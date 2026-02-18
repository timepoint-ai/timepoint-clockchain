import json
import os
import shutil
from unittest.mock import MagicMock, patch

import pytest

from app.core.graph import GraphManager
from app.workers.expander import GraphExpander


MOCK_GEMINI_RESPONSE = [
    {
        "name": "Roman Civil War",
        "year": -49,
        "month": "january",
        "day": 10,
        "time": "0800",
        "country": "italy",
        "region": "lazio",
        "city": "rome",
        "one_liner": "Caesar crosses the Rubicon, triggering civil war",
        "tags": ["politics", "ancient-rome", "civil-war"],
        "figures": ["Julius Caesar", "Pompey"],
        "edge_type": "causes",
    },
    {
        "name": "Death of Cleopatra",
        "year": -30,
        "month": "august",
        "day": 12,
        "time": "1400",
        "country": "egypt",
        "region": "alexandria",
        "city": "alexandria",
        "one_liner": "Cleopatra VII takes her own life after Octavian's conquest of Egypt",
        "tags": ["politics", "ancient-rome", "ancient-egypt"],
        "figures": ["Cleopatra VII", "Octavian"],
        "edge_type": "thematic",
    },
]


@pytest.fixture()
async def graph_manager(tmp_path):
    seeds_src = os.path.join(os.path.dirname(__file__), "..", "data", "seeds.json")
    shutil.copy(seeds_src, tmp_path / "seeds.json")
    gm = GraphManager(data_dir=str(tmp_path))
    await gm.load()
    return gm


@pytest.mark.asyncio
async def test_expander_generates_related_events(graph_manager):
    mock_response = MagicMock()
    mock_response.text = json.dumps(MOCK_GEMINI_RESPONSE)

    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response

    initial_count = graph_manager.graph.number_of_nodes()

    with patch("google.genai.Client") as MockClient:
        MockClient.return_value = mock_client_instance
        expander = GraphExpander(graph_manager, "fake-api-key")
        await expander._expand_once()

    new_count = graph_manager.graph.number_of_nodes()
    assert new_count > initial_count
    assert new_count == initial_count + 2


@pytest.mark.asyncio
async def test_expander_creates_edges(graph_manager):
    mock_response = MagicMock()
    mock_response.text = json.dumps(MOCK_GEMINI_RESPONSE)

    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response

    initial_edges = graph_manager.graph.number_of_edges()

    with patch("google.genai.Client") as MockClient:
        MockClient.return_value = mock_client_instance
        expander = GraphExpander(graph_manager, "fake-api-key")
        await expander._expand_once()

    assert graph_manager.graph.number_of_edges() > initial_edges


@pytest.mark.asyncio
async def test_expander_sets_correct_attributes(graph_manager):
    mock_response = MagicMock()
    mock_response.text = json.dumps(MOCK_GEMINI_RESPONSE)

    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response

    with patch("google.genai.Client") as MockClient:
        MockClient.return_value = mock_client_instance
        expander = GraphExpander(graph_manager, "fake-api-key")
        await expander._expand_once()

    # Find the "Roman Civil War" node
    found = None
    for node_id, attrs in graph_manager.graph.nodes(data=True):
        if "roman-civil-war" in node_id:
            found = attrs
            break

    assert found is not None
    assert found["visibility"] == "public"
    assert found["created_by"] == "system"
    assert found["layer"] == 1
