ALLERGEN_MAP = {
    "우유": "ALG_MILK",
    "치즈": "ALG_MILK",
    "버터": "ALG_MILK",
    "생크림": "ALG_MILK",

    "계란": "ALG_EGGS",

    "콩": "ALG_SOY",
    "두부": "ALG_SOY",

    "땅콩": "ALG_PEANUTS",

    "아몬드": "ALG_TREE_NUTS",
    "호두": "ALG_TREE_NUTS",
    "잣": "ALG_TREE_NUTS",
    "캐슈넛": "ALG_TREE_NUTS",

    "밀": "ALG_CEREALS_GLUTEN",
    "보리": "ALG_CEREALS_GLUTEN",
    "메밀": "ALG_CEREALS_GLUTEN",

    "고등어": "ALG_FISH",
    "갈치": "ALG_FISH",
    "삼치": "ALG_FISH",
    "생선": "ALG_FISH",
    "황태": "ALG_FISH",

    "새우": "ALG_CRUSTACEANS",
    "게": "ALG_CRUSTACEANS",

    "조개": "ALG_MOLLUSCS",
    "바지락": "ALG_MOLLUSCS",
    "굴": "ALG_MOLLUSCS",
    "홍합": "ALG_MOLLUSCS",
    "문어": "ALG_MOLLUSCS",
    "오징어": "ALG_MOLLUSCS",
    "전복": "ALG_MOLLUSCS",

    "참깨": "ALG_SESAME",
    "겨자": "ALG_MUSTARD",
    "샐러리": "ALG_CELERY"
}

def add_allergen_tags(data):
    for item in data:
        tags = set()
        for ing in item["ingredients_ko"]:
            if ing in ALLERGEN_MAP:
                tags.add(ALLERGEN_MAP[ing])
        item["ALG_TAG"] = sorted(tags)
    return data
import json

with open("menu_clean.json", "r", encoding="utf-8") as f:
    data = json.load(f)

data = add_allergen_tags(data)

with open("menu_final_with_allergen.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
