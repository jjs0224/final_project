# ai/review/review_llm.py

from typing import Dict, List

def build_review_prompt(data: Dict) -> str:
    review_text = data["review_text"]
    menu_items = ", ".join(data.get("menu_items", []))
    allergies = ", ".join(data["dietary_requirements"].get("allergies", [])) or "None"
    preferences = ", ".join(data["dietary_requirements"].get("preferences", [])) or "None"
    store = data.get("store_name", "the restaurant")

    return f"""
You are an AI assistant that evaluates the quality of a food review.

Restaurant: {store}
Menu eaten: {menu_items}
Dietary requirements:
- Allergies: {allergies}
- Preferences: {preferences}

Evaluate the review using the following rubric.
Each category is scored between 0.0 and 0.1.

Rubric:
1. Length
2. Specificity (mentions menu, taste, texture)
3. Dining experience (service, atmosphere, wait time)
4. Sentiment clarity
5. Effort and coherence

Return JSON ONLY in this exact format:
{{
  "length": number,
  "specificity": number,
  "experience": number,
  "sentiment": number,
  "coherence": number,
  "total": number
}}

Review:
\"\"\"
{review_text}
\"\"\"
""".strip()
