import pytest

from lightrag.utils import compute_mdhash_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_entities_and_relationships_vdb_meta_fields(lightrag_instance):
    rag = lightrag_instance

    custom_kg = {
        "chunks": [
            {"content": "EntityA is great", "source_id": "s1", "file_path": "f1.txt"}
        ],
        "entities": [
            {
                "entity_name": "EntityA",
                "entity_type": "organization",
                "description": "An org",
                "source_id": "s1",
                "file_path": "f1.txt",
            }
        ],
        "relationships": [
            {
                "src_id": "EntityA",
                "tgt_id": "EntityA",
                "description": "self",
                "keywords": "self",
                "weight": 1.0,
                "source_id": "s1",
                "file_path": "f1.txt",
            }
        ],
    }

    await rag.ainsert_custom_kg(custom_kg)

    # Entity vector payload shape
    ent_id = compute_mdhash_id("EntityA", prefix="ent-")
    ent = await rag.entities_vdb.get_by_id(ent_id)
    assert ent is not None
    assert "content" in ent
    assert "entity_name" in ent
    assert "file_path" in ent
    assert "created_at" in ent

    # Relationship vector payload shape
    rel_id = compute_mdhash_id("EntityA" + "EntityA", prefix="rel-")
    rel = await rag.relationships_vdb.get_by_id(rel_id)
    assert rel is not None
    for k in ("src_id", "tgt_id", "content", "file_path", "created_at"):
        assert k in rel


