import pytest

from lightrag.base import DocStatus


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apipeline_enqueue_error_documents_records_failed_status(lightrag_instance):
    rag = lightrag_instance

    error_files = [
        {
            "file_path": "bad.pdf",
            "error_description": "Document enqueue error",
            "original_error": "Failed to parse PDF",
            "file_size": 123,
        }
    ]

    await rag.apipeline_enqueue_error_documents(error_files, track_id="t1")

    failed_docs = await rag.doc_status.get_docs_by_status(DocStatus.FAILED)
    assert len(failed_docs) == 1
    doc_id, status = next(iter(failed_docs.items()))
    assert status.status == DocStatus.FAILED
    assert status.file_path == "bad.pdf"
    assert status.content_length == 123
    assert status.metadata.get("error_type") == "file_extraction_error"


