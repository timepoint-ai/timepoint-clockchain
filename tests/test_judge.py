import json
from unittest.mock import MagicMock, patch

import pytest

from app.workers.judge import ContentJudge


@pytest.mark.asyncio
async def test_judge_approves_innocuous():
    mock_response = MagicMock()
    mock_response.text = json.dumps({"verdict": "approve", "reason": "Standard historical query"})

    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response

    with patch("google.genai.Client") as MockClient:
        MockClient.return_value = mock_client_instance
        judge = ContentJudge("fake-api-key")
        verdict = await judge.screen("The signing of the Magna Carta")

    assert verdict == "approve"


@pytest.mark.asyncio
async def test_judge_approves_sensitive():
    mock_response = MagicMock()
    mock_response.text = json.dumps({"verdict": "sensitive", "reason": "Historical violence"})

    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response

    with patch("google.genai.Client") as MockClient:
        MockClient.return_value = mock_client_instance
        judge = ContentJudge("fake-api-key")
        verdict = await judge.screen("The assassination of Julius Caesar")

    assert verdict == "sensitive"


@pytest.mark.asyncio
async def test_judge_rejects_harmful():
    mock_response = MagicMock()
    mock_response.text = json.dumps({"verdict": "reject", "reason": "Harmful content"})

    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response

    with patch("google.genai.Client") as MockClient:
        MockClient.return_value = mock_client_instance
        judge = ContentJudge("fake-api-key")
        verdict = await judge.screen("How to build a weapon")

    assert verdict == "reject"
