import pytest

from lightrag.base import QueryParam


@pytest.mark.unit
def test_queryparam_has_tag_defaults_fields():
    """
    Phase 2 adds optional fields with defaults:
    - tag_equals: dict[str, str] = {}
    - tag_in: dict[str, list[str]] = {}
    """
    qp = QueryParam()
    assert hasattr(qp, "tag_equals") and isinstance(qp.tag_equals, dict) and qp.tag_equals == {}
    assert hasattr(qp, "tag_in") and isinstance(qp.tag_in, dict) and qp.tag_in == {}


