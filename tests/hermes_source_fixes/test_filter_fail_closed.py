"""Real Qdrant models must not lose constraints during narrow translation."""
from types import SimpleNamespace as NS

import pytest
from qdrant_client.models import (
    FieldCondition,
    Filter,
    GeoBoundingBox,
    GeoLineString,
    GeoPoint,
    GeoPolygon,
    GeoRadius,
    MatchValue,
    MinShould,
    Range,
    ValuesCount,
)

from src.db_adapters import _vector_filter
from src.db_adapters.vector_lancedb import _LanceDBClient

def condition(key='agent_id', value='wanted-space'):
    return FieldCondition(key=key, match=MatchValue(value=value))


@pytest.fixture
def client(tmp_path):
    adapter = _LanceDBClient(str(tmp_path / 'lance'))
    adapter.create_collection('memory', NS(size=2, distance='Cosine'))
    adapter.upsert('memory', [
        NS(id='wanted', vector=[0.8, 0.2], payload={'kind': 'memory', 'agent_id': 'wanted-space'}),
        NS(id='other', vector=[1.0, 0.0], payload={'kind': 'memory', 'agent_id': 'other-space'}),
    ])
    yield adapter
    adapter.close()


def rows(client):
    return sorted(client._connect().open_table('memory').to_arrow().to_pylist(), key=lambda row: row['id'])


@pytest.mark.parametrize('clause', ['must', 'should', 'must_not'])
def test_scalar_clause_rejects_before_search(client, clause):
    filt = Filter(**{clause: condition()})
    before = rows(client)
    with pytest.raises(NotImplementedError, match=clause):
        client.search('memory', [1.0, 0.0], limit=1, query_filter=filt)
    assert rows(client) == before


@pytest.mark.parametrize('shape', ['direct', 'single-must-list'])
def test_supported_equality_search_is_not_vacuously_rejected(client, shape):
    filt = condition() if shape == 'direct' else Filter(must=[condition()])
    assert [hit.id for hit in client.search('memory', [1.0, 0.0], limit=1, query_filter=filt)] == ['wanted']


def test_supported_single_must_delete_only_removes_wanted_namespace(client):
    client.delete('memory', NS(filter=Filter(must=[condition()])))
    assert {row['id'] for row in rows(client)} == {'other'}


@pytest.mark.parametrize('filt', [None, Filter(), Filter(must=[], should=[], must_not=[])])
def test_empty_real_filter_stays_match_all(client, filt):
    assert _vector_filter.normalise(filt).must == ()
    assert {hit.id for hit in client.search('memory', [1.0, 0.0], query_filter=filt)} == {'wanted', 'other'}


@pytest.mark.parametrize('with_must', [False, True])
def test_min_should_search_rejects_and_preserves_rows(client, with_must):
    filt = Filter(must=[condition('kind', 'memory')] if with_must else None,
                  min_should=MinShould(conditions=[condition()], min_count=1))
    before = rows(client)
    with pytest.raises(NotImplementedError, match='min_should'):
        client.search('memory', [1.0, 0.0], query_filter=filt)
    assert rows(client) == before


def test_min_should_delete_rejects_and_preserves_both_namespaces(client):
    filt = Filter(must=[condition('kind', 'memory')],
                  min_should=MinShould(conditions=[condition()], min_count=1))
    before = rows(client)
    with pytest.raises(NotImplementedError, match='min_should'):
        client.delete('memory', NS(filter=filt))
    assert rows(client) == before


CO_CONSTRAINTS = [
    ('range', Range(gte=2)),
    ('geo_bounding_box', GeoBoundingBox(top_left=GeoPoint(lon=0, lat=1), bottom_right=GeoPoint(lon=1, lat=0))),
    ('geo_radius', GeoRadius(center=GeoPoint(lon=0, lat=0), radius=1)),
    ('geo_polygon', GeoPolygon(exterior=GeoLineString(points=[
        GeoPoint(lon=0, lat=0), GeoPoint(lon=1, lat=0),
        GeoPoint(lon=0, lat=1), GeoPoint(lon=0, lat=0),
    ]))),
    ('values_count', ValuesCount(gte=2)),
    ('is_empty', True), ('is_empty', False),
    ('is_null', True), ('is_null', False),
]


@pytest.mark.parametrize('name,value', CO_CONSTRAINTS)
@pytest.mark.parametrize('shape', ['direct', 'single-must-list'])
def test_field_condition_co_constraints_are_not_dropped(client, name, value, shape):
    cond = FieldCondition(key='agent_id', match=MatchValue(value='wanted-space'), **{name: value})
    filt = cond if shape == 'direct' else Filter(must=[cond])
    before = rows(client)
    with pytest.raises(NotImplementedError, match=name):
        client.search('memory', [1.0, 0.0], query_filter=filt)
    assert rows(client) == before
    if shape == 'single-must-list':
        with pytest.raises(NotImplementedError, match=name):
            client.delete('memory', NS(filter=filt))
        assert rows(client) == before


@pytest.mark.parametrize('clause', ['must', 'should', 'must_not'])
def test_scalar_clause_delete_preserves_both_namespaces(client, clause):
    filt = Filter(**{clause: condition()})
    before = rows(client)
    with pytest.raises(NotImplementedError):
        client.delete('memory', NS(filter=filt))
    assert rows(client) == before


@pytest.mark.parametrize('clause', ['must', 'should', 'must_not'])
def test_malformed_tuple_clause_is_rejected(clause):
    value = (condition(),) if clause == 'must' else ()
    filt = Filter.model_construct(**{clause: value})
    with pytest.raises(NotImplementedError, match=clause):
        _vector_filter.normalise(filt)


@pytest.mark.parametrize('value', [[], {}, 1.5, None])
def test_malformed_match_value_rejects_before_search_or_delete(client, value):
    cond = FieldCondition.model_construct(key='agent_id', match=MatchValue.model_construct(value=value))
    filt = Filter(must=[cond])
    before = rows(client)
    with pytest.raises(NotImplementedError, match='MatchValue'):
        client.search('memory', [1.0, 0.0], query_filter=filt)
    with pytest.raises(NotImplementedError, match='MatchValue'):
        client.delete('memory', NS(filter=filt))
    assert rows(client) == before


@pytest.mark.parametrize('node', ['filter', 'match'])
def test_unrecognised_real_model_constraints_are_not_dropped(node):
    # Pydantic model_copy bypasses validation. A malformed extra constraint
    # must still fail closed, including falsey values, not become equality-only.
    if node == 'filter':
        filt = Filter(must=[condition()]).model_copy(update={'extra_constraint': False})
    else:
        match = MatchValue(value='wanted-space').model_copy(update={'extra_constraint': []})
        filt = FieldCondition.model_construct(key='agent_id', match=match)
    with pytest.raises(NotImplementedError, match='extra_constraint'):
        _vector_filter.normalise(filt)


@pytest.mark.parametrize('value', [True, False, 0, 1, '', 'wanted-space'])
def test_real_match_value_scalar_positive_controls(value):
    normalised = _vector_filter.normalise(condition(value=value))
    assert type(normalised.must[0].value) is type(value)
    assert normalised.must[0].value == value


@pytest.mark.parametrize('shape', ['multiple-must', 'nested', 'should-list', 'must-not-list'])
def test_real_compounds_reject_search_and_delete_without_changes(client, shape):
    target = condition()
    if shape == 'multiple-must':
        filt = Filter(must=[target, condition('kind', 'memory')])
    elif shape == 'nested':
        filt = Filter(must=[Filter(must=[target])])
    else:
        name = 'should' if shape == 'should-list' else 'must_not'
        filt = Filter(must=[condition('kind', 'memory')], **{name: [target]})
    before = rows(client)
    with pytest.raises(NotImplementedError):
        client.search('memory', [1.0, 0.0], query_filter=filt)
    with pytest.raises(NotImplementedError):
        client.delete('memory', NS(filter=filt))
    assert rows(client) == before


def test_real_model_field_coverage_is_explicit():
    assert set(Filter.model_fields) == {'must', 'should', 'must_not', 'min_should'}
    assert set(FieldCondition.model_fields) - {'key', 'match'} == {name for name, _ in CO_CONSTRAINTS}
    assert set(MatchValue.model_fields) == {'value'}
