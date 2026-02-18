import asyncio
import json
import logging

from google import genai

logger = logging.getLogger("clockchain.judge")

JUDGE_PROMPT = """You are a content moderation system for a historical education platform.

Evaluate this query for a historical scene generation:
"{query}"

Classify as ONE of:
- "approve" — innocuous historical topic, safe to generate
- "sensitive" — involves violence, controversy, or mature themes but is historically significant and educational; approve with a disclaimer
- "reject" — harmful, hateful, exploitative, or not a genuine historical query

Return ONLY a JSON object: {{"verdict": "approve"|"sensitive"|"reject", "reason": "brief explanation"}}"""


class ContentJudge:
    def __init__(self, google_api_key: str):
        self.api_key = google_api_key

    async def screen(self, query: str) -> str:
        prompt = JUDGE_PROMPT.format(query=query)

        client = genai.Client(api_key=self.api_key)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt,
        )

        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        result = json.loads(text)
        verdict = result.get("verdict", "reject")
        logger.info("Judge verdict for %r: %s (%s)", query, verdict, result.get("reason", ""))

        if verdict in ("approve", "sensitive"):
            return verdict
        return "reject"
