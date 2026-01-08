# AI/category_rules.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

# ---------------------------
# Normalization
# ---------------------------

_RE_PRICE = re.compile(r"\d{1,3}(?:,\d{3})*\s*원")
_RE_UNIT = re.compile(r"\d+(?:\.\d+)?\s*(?:ml|g|kg|l|L|인분|인|pcs|피스|개|접시|그릇|잔)")
_RE_BRACKETS = re.compile(r"[\(\[\{].*?[\)\]\}]")
_RE_SPACES = re.compile(r"\s+")
_RE_PUNCT = re.compile(r"[^\w가-힣]+")

# 표기 통합(필요 시 계속 추가)
_CANON_REPL = [
    (re.compile(r"(돈가스|돈까스|돈카츠|돈카츠|톤카츠|카츠)"), "돈까스"),
    (re.compile(r"(라멘|라면)"), "라면"),
    (re.compile(r"(우동면)"), "우동"),
    (re.compile(r"(아메리카노)"), "아메리카노"),
]

def normalize_menu(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    t = _RE_BRACKETS.sub(" ", t)
    t = _RE_PRICE.sub(" ", t)
    t = _RE_UNIT.sub(" ", t)
    for pat, rep in _CANON_REPL:
        t = pat.sub(rep, t)
    t = t.lower()
    t = _RE_PUNCT.sub(" ", t)
    t = _RE_SPACES.sub(" ", t).strip()
    return t

# ---------------------------
# Category rules
# ---------------------------

@dataclass(frozen=True)
class CatResult:
    category_lv1: str
    confidence: float
    matched: List[str]

# 대분류(초기 12개)
CATEGORIES = [
    "RICE",
    "NOODLE",
    "SOUP_STEW",
    "MEAT",
    "SEAFOOD",
    "SNACK_STREET",
    "FRIED_CUTLET",
    "DUMPLING",
    "VEG_SALAD",
    "DESSERT_BAKERY",
    "BEVERAGE",
    "OTHER",
]

# 강/약 키워드: 강키워드는 confidence를 크게 올림
STRONG: Dict[str, List[str]] = {
    "NOODLE": ["냉면", "막국수", "쫄면", "칼국수", "수제비", "우동", "국수", "소면", "라면", "짜장면", "짬뽕", "파스타", "스파게티"],
    "SOUP_STEW": ["순대국", "해장국", "곰탕", "설렁탕", "삼계탕", "감자탕", "전골", "찌개", "탕", "국", "샤브"],
    "RICE": ["비빔밥", "볶음밥", "덮밥", "김밥", "오므라이스", "카레", "주먹밥"],
    "FRIED_CUTLET": ["돈까스"],
    "SNACK_STREET": ["떡볶이", "순대", "어묵", "김말이", "핫도그", "튀김"],
    "DUMPLING": ["만두", "교자", "딤섬"],
    "MEAT": ["갈비", "삼겹", "목살", "불고기", "족발", "보쌈", "닭갈비", "치킨"],
    "SEAFOOD": ["회", "사시미", "전복", "조개", "굴", "새우", "게", "낙지", "문어", "오징어"],
    "DESSERT_BAKERY": ["빙수", "아이스크림", "케이크", "쿠키", "도넛", "마카롱", "떡", "빵"],
    "BEVERAGE": ["아메리카노", "라떼", "커피", "스무디", "에이드", "주스", "차", "티"],
    "VEG_SALAD": ["샐러드"],
}

WEAK: Dict[str, List[str]] = {
    "RICE": ["정식", "세트", "특선", "백반"],
    "MEAT": ["구이", "바베큐"],
    "SEAFOOD": ["해물", "해산물"],
    "DESSERT_BAKERY": ["디저트"],
    "BEVERAGE": ["음료"],
}

# 카테고리 우선순위(충돌 시)
PRIORITY = [
    "FRIED_CUTLET",
    "NOODLE",
    "SOUP_STEW",
    "SNACK_STREET",
    "RICE",
    "MEAT",
    "SEAFOOD",
    "DUMPLING",
    "VEG_SALAD",
    "DESSERT_BAKERY",
    "BEVERAGE",
]

def predict_category(menu_text: str) -> CatResult:
    norm = normalize_menu(menu_text)

    if not norm:
        return CatResult("OTHER", 0.0, [])

    scores: Dict[str, float] = {c: 0.0 for c in CATEGORIES}
    matched: Dict[str, List[str]] = {c: [] for c in CATEGORIES}

    # 강키워드
    for cat, kws in STRONG.items():
        for kw in kws:
            if kw in norm:
                scores[cat] += 3.0
                matched[cat].append(kw)

    # 약키워드
    for cat, kws in WEAK.items():
        for kw in kws:
            if kw in norm:
                scores[cat] += 1.0
                matched[cat].append(kw)

    # 아무것도 못 찾으면 OTHER
    best_cat = "OTHER"
    best_score = 0.0

    # 우선순위를 반영하여 best 선택
    for cat in PRIORITY:
        sc = scores.get(cat, 0.0)
        if sc > best_score:
            best_score = sc
            best_cat = cat

    if best_score <= 0.0:
        return CatResult("OTHER", 0.30, [])

    # confidence: 강키워드가 있을수록 높게
    # score 3.0(강키워드 1개)면 0.85 근처
    # score 1.0(약키워드 1개)면 0.60 근처
    # cap 0.97
    conf = 0.55 + (best_score * 0.10)
    conf = max(0.55, min(conf, 0.97))

    return CatResult(best_cat, conf, matched.get(best_cat, []))
