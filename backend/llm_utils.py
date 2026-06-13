"""Moderation for ExpireMate item listings."""
import os
import json
import logging
import uuid
import asyncio
import openai

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a strict content moderator for ExpireMate, a community platform where people give away soon-to-expire food, sealed medicines, pet supplies, and cleaning items.

ALLOW: Sealed unexpired food, sealed unopened over-the-counter medicine (Tylenol, Advil, etc.), pet food, sealed cleaning supplies, household items.

BLOCK if the item mentions ANY of:
- Opened/used medicine (especially anything opened)
- Prescription medications (antibiotics, painkillers like Oxycodone, ADHD meds, etc.)
- Alcohol (beer, wine, liquor)
- Recreational drugs (weed, marijuana, cannabis, edibles, vapes)
- Weapons (guns, knives meant as weapons, ammunition)
- Raw meat, dairy, or perishables clearly already spoiled
- Anything illegal in the US
- Sexual / adult products
- Anything implying tampering

Respond ONLY with valid JSON in this exact format:
{"allowed": true, "reason": "Sealed item, safe to share"} or
{"allowed": false, "reason": "<short reason e.g. 'Prescription medication'>"}

No other text."""


async def moderate_item(title: str, description: str, category: str) -> dict:
    """Return {'allowed': bool, 'reason': str}. On failure -> allow with warning."""
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"allowed": True, "reason": "Moderation skipped (no key)"}
    try:
        openai.api_key = api_key
        prompt = f"Category: {category}\nTitle: {title}\nDescription: {description}"

        def create_chat():
            return openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=150,
            )

        response = await asyncio.to_thread(create_chat)
        text = response.choices[0].message["content"].strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            data = json.loads(text[start : end + 1])
            return {
                "allowed": bool(data.get("allowed", True)),
                "reason": str(data.get("reason", "")),
            }
        return {"allowed": True, "reason": "Moderation parse fallback"}
    except Exception as e:
        logger.error(f"Moderation failed: {e}")
        return {"allowed": True, "reason": "Moderation error — allowed by default"}
