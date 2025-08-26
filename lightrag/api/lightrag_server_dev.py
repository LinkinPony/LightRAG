import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from . import lightrag_server as server
from fastapi import FastAPI
from starlette.responses import HTMLResponse


def _print(msg: str) -> None:
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def _find_webui_dir() -> Path:
    # lightrag/api/ -> repo root -> lightrag_webui
    return Path(__file__).resolve().parents[2] / "lightrag_webui"


def _ensure_env() -> None:
    # Reuse the same environment checks as normal server
    if not server.check_env_file():
        sys.exit(1)

    server.check_and_install_dependencies()
    server.configure_logging()
    server.update_uvicorn_mode_config()
    server.display_splash_screen(server.global_args)
    server.setup_signal_handlers()


def _start_frontend_dev(backend_host: str, backend_port: int) -> subprocess.Popen:
    webui_dir = _find_webui_dir()
    if not webui_dir.exists():
        raise RuntimeError(f"Cannot find webui directory: {webui_dir}")

    use_bun = shutil.which("bun") is not None
    if use_bun:
        cmd = ["bun", "run", "dev"]
    else:
        # Fallback to Node - use the no-bun script defined in package.json
        if shutil.which("npm") is None and shutil.which("pnpm") is None and shutil.which("yarn") is None:
            raise RuntimeError("Neither bun nor npm/pnpm/yarn found. Please install one of them to run the WebUI dev server.")
        cmd = ["npm", "run", "dev-no-bun"]

    # Prepare environment for Vite proxy
    env = os.environ.copy()
    backend_host_for_proxy = (
        "localhost" if backend_host in ("0.0.0.0", "::", "") else backend_host
    )
    backend_url = f"http://{backend_host_for_proxy}:{backend_port}"
    # Always overwrite to ensure consistency across restarts
    env["VITE_BACKEND_URL"] = backend_url
    env["VITE_API_PROXY"] = "true"
    # Include all endpoints used by the WebUI so auth/login and others are proxied in dev
    env["VITE_API_ENDPOINTS"] = "/api,/docs,/openapi.json,/auth-status,/login,/health,/documents,/graph"

    # Start the dev server
    _print(f"Starting WebUI dev server in {webui_dir} using: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd=str(webui_dir), env=env)
    return proc


def _override_webui_mount(app: FastAPI, vite_url: str) -> None:
    """Replace the default static /webui mount with a small HTML that embeds Vite dev UI.

    This keeps the browser address at backend port while enabling full Vite HMR inside.
    """
    # Remove existing /webui mount if present
    app.router.routes = [r for r in app.router.routes if getattr(r, 'path', None) not in ('/webui', '/webui/')]

    async def dev_webui_index():
        html = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>LightRAG Dev UI</title>
    <style>html,body,iframe{{margin:0;padding:0;height:100%;width:100%;border:0;}}</style>
  </head>
  <body>
    <iframe src=\"{vite_url}/webui\" allow=\"clipboard-write; clipboard-read\"></iframe>
  </body>
</html>
"""
        return HTMLResponse(html)

    # Register both /webui and /webui/
    app.add_api_route('/webui', dev_webui_index, include_in_schema=False)
    app.add_api_route('/webui/', dev_webui_index, include_in_schema=False)


def get_dev_application() -> FastAPI:
    """Uvicorn factory target used in reload mode.

    Reads DEV_VITE_URL from env (default http://localhost:5173) and overrides /webui.
    """
    vite_url = os.getenv("DEV_VITE_URL", "http://localhost:5173")
    app = server.create_app(server.global_args)
    _override_webui_mount(app, vite_url)
    return app


def _start_backend_dev() -> None:
    import uvicorn

    # Use import string + factory to allow reload
    uvicorn.run(
        "lightrag.api.lightrag_server_dev:get_dev_application",
        host=server.global_args.host,
        port=server.global_args.port,
        reload=True,
        factory=True,
        log_config=None,
    )


def main() -> None:
    _ensure_env()

    backend_host = server.global_args.host
    backend_port = server.global_args.port

    # Start frontend dev server
    fe_proc = _start_frontend_dev(backend_host, backend_port)

    # Make sure we terminate the FE dev server when backend exits
    def _terminate_child(*_args):
        try:
            if fe_proc.poll() is None:
                _print("Stopping WebUI dev server ...")
                # Send SIGINT first for graceful shutdown
                fe_proc.send_signal(signal.SIGINT)
                # Wait a bit, then force kill if still alive
                for _ in range(20):  # ~2s
                    if fe_proc.poll() is not None:
                        break
                    time.sleep(0.1)
                if fe_proc.poll() is None:
                    fe_proc.kill()
        except Exception:
            pass

    # Register handlers to stop child on termination
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_args: (_terminate_child(), sys.exit(0)))

    _print("")
    _print("============================================================")
    _print("LightRAG Dev Mode")
    _print("- Backend API   : http://%s:%s" % (backend_host, backend_port))
    _print("- Dev WebUI     : http://%s:%s/webui (proxied to Vite dev)" % (backend_host, backend_port))
    _print("  Note: /webui embeds Vite dev UI; HMR still connects to the Vite port internally.")
    _print("============================================================\n")

    try:
        _start_backend_dev()
    finally:
        _terminate_child()


if __name__ == "__main__":
    main()


