import json
import os
import tempfile

import pytest

from app.core.graph import GraphManager


@pytest.fixture()
async def graph_manager(tmp_path):
    seeds_src = os.path.join(os.path.dirname(__file__), "..", "data", "seeds.json")
    seeds_dst = tmp_path / "seeds.json"
    with open(seeds_src) as f:
        data = f.read()
    seeds_dst.write_text(data)

    gm = GraphManager(data_dir=str(tmp_path))
    await gm.load()
    return gm


@pytest.mark.asyncio
async def test_load_seeds(graph_manager):
    assert graph_manager.graph.number_of_nodes() == 5
    assert graph_manager.graph.number_of_edges() == 3


@pytest.mark.asyncio
async def test_get_node(graph_manager):
    node = graph_manager.get_node(
        "/-44/march/15/1030/italy/lazio/rome/assassination-of-julius-caesar"
    )
    assert node is not None
    assert node["name"] == "Assassination of Julius Caesar"
    assert node["year"] == -44


@pytest.mark.asyncio
async def test_get_node_not_found(graph_manager):
    assert graph_manager.get_node("/nonexistent/path") is None


@pytest.mark.asyncio
async def test_browse_root(graph_manager):
    items = graph_manager.browse("")
    segments = [i["segment"] for i in items]
    assert "-44" in segments
    assert "1945" in segments
    assert "1969" in segments
    assert "2016" in segments


@pytest.mark.asyncio
async def test_browse_year(graph_manager):
    items = graph_manager.browse("1969")
    segments = [i["segment"] for i in items]
    assert "july" in segments
    assert "november" in segments


@pytest.mark.asyncio
async def test_today_in_history(graph_manager):
    # March 15 should return Caesar
    events = graph_manager.today_in_history(3, 15)
    assert len(events) >= 1
    assert any("Caesar" in e.get("name", "") for e in events)


@pytest.mark.asyncio
async def test_search_caesar(graph_manager):
    results = graph_manager.search("caesar")
    assert len(results) >= 1
    assert results[0]["name"] == "Assassination of Julius Caesar"


@pytest.mark.asyncio
async def test_search_apollo(graph_manager):
    results = graph_manager.search("apollo")
    assert len(results) >= 2


@pytest.mark.asyncio
async def test_random_public(graph_manager):
    node = graph_manager.random_public()
    assert node is not None
    assert node["visibility"] == "public"


@pytest.mark.asyncio
async def test_stats(graph_manager):
    s = graph_manager.stats()
    assert s["total_nodes"] == 5
    assert s["total_edges"] == 3
    assert "layer_counts" in s
    assert "edge_type_counts" in s


@pytest.mark.asyncio
async def test_save_load_round_trip(graph_manager, tmp_path):
    await graph_manager.save()
    assert (tmp_path / "graph.json").exists()

    gm2 = GraphManager(data_dir=str(tmp_path))
    await gm2.load()
    assert gm2.graph.number_of_nodes() == 5


@pytest.mark.asyncio
async def test_get_neighbors(graph_manager):
    neighbors = graph_manager.get_neighbors(
        "/1969/july/20/2056/united-states/florida/cape-canaveral/apollo-11-moon-landing"
    )
    assert len(neighbors) >= 1
    types = [n["edge_type"] for n in neighbors]
    assert "contemporaneous" in types or "causes" in types


@pytest.mark.asyncio
async def test_get_frontier_nodes(graph_manager):
    frontier = graph_manager.get_frontier_nodes(threshold=5)
    assert len(frontier) > 0
