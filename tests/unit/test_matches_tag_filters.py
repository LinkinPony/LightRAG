import pytest


@pytest.mark.unit
@pytest.mark.xfail(reason="matches_tag_filters not implemented yet", strict=False)
def test_matches_tag_filters_semantics():
    """
    Phase 2 utility to be implemented:
    matches_tag_filters(tags, tag_equals, tag_in) -> bool

    Semantics:
    - AND across keys within each dict
    - Both groups apply with AND
    - If a key appears in both, both constraints must hold
    - Missing keys => no match
    Supported types: str or list[str] values inside tags
    """
    from lightrag.utils import matches_tag_filters  # type: ignore

    tags = {"project": "alpha", "region": ["us", "eu"], "team": "ml"}
    assert matches_tag_filters(tags, {"project": "alpha"}, {}) is True
    assert matches_tag_filters(tags, {"project": "beta"}, {}) is False
    assert matches_tag_filters(tags, {}, {"region": ["us"]}) is True
    assert matches_tag_filters(tags, {}, {"region": ["apac"]}) is False
    # Both groups AND
    assert matches_tag_filters(tags, {"project": "alpha"}, {"region": ["eu"]}) is True
    # Key in both: equals must also be in 'in'
    assert matches_tag_filters(tags, {"region": "us"}, {"region": ["us", "eu"]}) is True
    assert matches_tag_filters(tags, {"region": "us"}, {"region": ["eu"]}) is False
    # Missing key => no match
    assert matches_tag_filters(tags, {"missing": "x"}, {}) is False


