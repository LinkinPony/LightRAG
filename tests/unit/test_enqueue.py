import asyncio
from datetime import datetime

import pytest

from lightrag.base import DocStatus


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apipeline_enqueue_documents_stores_status_and_full_docs(lightrag_instance):
    rag = lightrag_instance

    content = "Hello World"
    track_id = await rag.apipeline_enqueue_documents([content])
    assert isinstance(track_id, str) and len(track_id) > 0

    # Verify full_docs saved content
    # Get the doc_id by scanning doc_status entries
    docs = await rag.doc_status.get_docs_by_status(DocStatus.PENDING)
    assert len(docs) == 1
    doc_id = next(iter(docs.keys()))

    full_doc = await rag.full_docs.get_by_id(doc_id)
    assert full_doc is not None
    assert full_doc["content"] == content

    # Verify status fields shape
    status = docs[doc_id]
    assert status.status == DocStatus.PENDING
    assert status.content_length == len(content)
    assert isinstance(status.created_at, str)
    assert isinstance(status.updated_at, str)
    # created_at and updated_at are ISO strings
    datetime.fromisoformat(status.created_at)
    datetime.fromisoformat(status.updated_at)


