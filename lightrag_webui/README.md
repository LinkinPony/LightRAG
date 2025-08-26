# LightRAG WebUI

LightRAG WebUI is a React-based web interface for interacting with the LightRAG system. It provides a user-friendly interface for querying, managing, and exploring LightRAG's functionalities.

## Installation

1.  **Install Bun:**

    If you haven't already installed Bun, follow the official documentation: [https://bun.sh/docs/installation](https://bun.sh/docs/installation)

2.  **Install Dependencies:**

    In the `lightrag_webui` directory, run the following command to install project dependencies:

    ```bash
    bun install --frozen-lockfile
    ```

3.  **Build the Project:**

    Run the following command to build the project:

    ```bash
    bun run build --emptyOutDir
    ```

    This command will bundle the project and output the built files to the `lightrag/api/webui` directory.

## Development

- **Full-stack Dev (backend reload + Vite dev server):**

  After installing the package (editable install recommended), you can launch the backend with reload and the Vite dev server together:

  ```bash
  lightrag-server-dev
  ```

  - Backend: uvicorn reload using `lightrag.api.lightrag_server:get_application`
  - Frontend: Vite dev server (bun if available, otherwise npm) with API proxy to the backend
  - Open `http://localhost:5173/webui` during development

- **Start the Development Server (WebUI only):**

  ```bash
  bun run dev
  ```

## Script Commands

The following are some commonly used script commands defined in `package.json`:

- `bun install`: Installs project dependencies.
- `bun run dev`: Starts the development server.
- `bun run build`: Builds the project.
- `bun run lint`: Runs the linter.
