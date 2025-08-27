import json
import pytest

from lightrag.base import QueryParam
from lightrag.prompt import PROMPTS
from lightrag.utils import compute_mdhash_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_entity_relation_tag_aggregation_and_storage_to_vdb_and_graph(lightrag_instance, monkeypatch):
    rag = lightrag_instance

    # Prepare pipeline shared storage
    from lightrag.kg.shared_storage import initialize_share_data, initialize_pipeline_status
    initialize_share_data(1)
    await initialize_pipeline_status()

    # Stub LLM to emit one entity pair and one relationship using expected delimiters
    td = PROMPTS["DEFAULT_TUPLE_DELIMITER"]
    rd = PROMPTS["DEFAULT_RECORD_DELIMITER"]
    cd = PROMPTS["DEFAULT_COMPLETION_DELIMITER"]

    extraction_output = rd.join(
        [
            f"(\"entity\"{td}\"Alice\"{td}\"person\"{td}\"Alice desc\")",
            f"(\"entity\"{td}\"Bob\"{td}\"person\"{td}\"Bob desc\")",
            f"(\"relationship\"{td}\"Alice\"{td}\"Bob\"{td}\"friends\"{td}\"friendship\"{td}8)",
        ]
    )
    extraction_output += cd

    async def fake_llm(prompt: str, *args, **kwargs):
        # Return extraction records for entity/relation merges
        return extraction_output

    monkeypatch.setattr(rag, "llm_model_func", fake_llm)

    # Insert document with tags so chunk-level tags exist for aggregation
    tags = {"project": "alpha", "region": ["us", "eu"]}
    track_id = await rag.apipeline_enqueue_documents(["Alice and Bob are friends."], file_paths=["a.txt"], tags=tags)
    assert isinstance(track_id, str)

    await rag.apipeline_process_enqueue_documents()

    # Ensure persistence
    await rag._insert_done()

    # Verify tags aggregated onto entities_vdb payload (order-insensitive for lists)
    alice_ent_id = compute_mdhash_id("Alice", prefix="ent-")
    alice_vec = await rag.entities_vdb.get_by_id(alice_ent_id)
    assert alice_vec is not None
    alice_tags = alice_vec.get("tags")
    assert alice_tags is not None and alice_tags.get("project") == tags["project"]
    assert set(alice_tags.get("region", [])) == set(tags["region"])  # ignore order

    bob_ent_id = compute_mdhash_id("Bob", prefix="ent-")
    bob_vec = await rag.entities_vdb.get_by_id(bob_ent_id)
    assert bob_vec is not None
    bob_tags = bob_vec.get("tags")
    assert bob_tags is not None and bob_tags.get("project") == tags["project"]
    assert set(bob_tags.get("region", [])) == set(tags["region"])  # ignore order

    # Verify tags aggregated onto relationships_vdb payload (Alice-Bob sorted key)
    rel_id = compute_mdhash_id("Alice" + "Bob", prefix="rel-")
    rel_vec = await rag.relationships_vdb.get_by_id(rel_id)
    assert rel_vec is not None
    rel_tags = rel_vec.get("tags")
    assert rel_tags is not None and rel_tags.get("project") == tags["project"]
    assert set(rel_tags.get("region", [])) == set(tags["region"])  # ignore order

    # Verify tags_json written to graph nodes and edges
    alice_node = await rag.chunk_entity_relation_graph.get_node("Alice")
    assert alice_node is not None and "tags_json" in alice_node
    node_tags = alice_node["tags_json"]
    if isinstance(node_tags, str):
        node_tags = json.loads(node_tags)
    assert node_tags.get("project") == tags["project"]
    assert set(node_tags.get("region", [])) == set(tags["region"])  # ignore order

    edge = await rag.chunk_entity_relation_graph.get_edge("Alice", "Bob")
    assert edge is not None and "tags_json" in edge
    edge_tags = edge["tags_json"]
    if isinstance(edge_tags, str):
        edge_tags = json.loads(edge_tags)
    assert edge_tags.get("project") == tags["project"]
    assert set(edge_tags.get("region", [])) == set(tags["region"])  # ignore order


