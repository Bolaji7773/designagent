# agent/planner.py
# Takes the user's prompt and breaks it into a structured design plan
# Every driver reads this plan — keeps drivers clean and consistent

import json
from agent.llm import ask_async

PLANNER_SYSTEM = """
You are an expert graphic designer AI.
Your job is to turn a user's design request into a structured JSON plan.

Return ONLY valid JSON. No explanation. No markdown. No backticks.

JSON structure:
{
  "design_type": "flyer | banner | logo | social_post | poster | mockup",
  "title": "main headline text",
  "subtitle": "secondary text if any",
  "body_text": "any extra text like date, venue, price etc",
  "color_palette": {
    "background": "#hex",
    "primary": "#hex",
    "secondary": "#hex",
    "text": "#hex",
    "accent": "#hex"
  },
  "style": "dark | light | minimal | bold | elegant | playful",
  "font_style": "modern | classic | handwritten | bold | thin",
  "dimensions": {
    "width_mm": 210,
    "height_mm": 297,
    "preset": "A4 | A5 | square | story | banner"
  },
  "elements": [
    {
      "type": "text | shape | image | line | logo",
      "content": "text content if type is text",
      "position": "top | center | bottom | top-left | top-right | bottom-left | bottom-right",
      "size": "large | medium | small",
      "style": "bold | italic | normal"
    }
  ],
  "reference_image_used": true,
  "notes": "any extra design notes"
}

Rules:
- Colors must match the vibe the user described
- Dark events (parties, clubs) = dark backgrounds, neon accents
- Corporate = clean, light or navy, professional fonts
- Always include all key info from the prompt in the elements
- dimensions default to A4 (210x297mm) if not specified
"""


async def plan_design(prompt: str, has_image: bool = False) -> dict:
    """
    Takes a user prompt and returns a structured design plan as a dict.

    Args:
        prompt:    The user's design request
        has_image: Whether the user uploaded a reference image

    Returns:
        dict with full design spec, or empty dict if parsing fails
    """
    full_prompt = prompt
    if has_image:
        full_prompt += "\n\nNote: The user has uploaded a reference image."

    raw = await ask_async(
        prompt=full_prompt,
        system=PLANNER_SYSTEM,
        temperature=0.7,
        max_tokens=1500,
    )

    # Strip any accidental markdown
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    try:
        plan = json.loads(clean)
        return plan
    except json.JSONDecodeError as e:
        print(f"[Planner] Failed to parse plan JSON: {e}")
        print(f"[Planner] Raw response was: {raw}")
        return {}