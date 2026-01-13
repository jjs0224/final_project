import json

def generate_food_journal(user_profile, review_data):
    # 1. Format the User Constraints
    constraints = f"""
    USER DIETARY PROFILE:
    - Allergies: {', '.join(user_profile['allergies'])}
    - Dislikes: {', '.join(user_profile['dislikes'])}
    """

    # 2. Format the Review Data
    reviews_str = json.dumps(review_data, ensure_ascii=False, indent=2)

    # 3. Construct the Final Prompt
    full_prompt = f"{constraints}\n\nRESTAURANT VISITS (JSON):\n{reviews_str}\n\n" \
                  f"Please write a 3-day food journal based on these visits. " \
                  f"Reflect on the flavors of the menu items and ensure you mention " \
                  f"if any items conflict with the user's allergies or dislikes."

    return full_prompt

# --- Example Data ---
user_data = {
    "allergies": ["egg (계란)"],
    "dislikes": ["cucumber (오이)"]
}

reviews = [
    {
        "store_name": "블루문",
        "address": "경기도 용인시 기흥구 죽전로43번길 19 1층 블루문 레스토랑",
        "menu_name": ["라지나", "쉬림프 알리오", "코카콜라"]
    }
    # ... other reviews
]

prompt = generate_food_journal(user_data, reviews)
print(prompt)