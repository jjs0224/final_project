import re
import pandas as pd
from pathlib import Path

###############################################################################
# 0) 입력/출력 경로
###############################################################################
INPUT_CSV  = r"food_data_allergy.csv"   # 당신 파일명으로 변경
OUTPUT_CSV = r"food_data_with_halal_labels.csv"

###############################################################################
# 1) 키워드 룰셋 (ko 중심, 필요하면 en도 추가 가능)
###############################################################################

# (A) 즉시 HARAM: 돼지/알코올/피(선지)/명시적 하람
HARAM_RULES = [
    ("PORK", [
        "돼지", "돈육", "삼겹", "오겹", "목살", "앞다리", "뒷다리", "베이컨", "햄", "소시지",
        "순대",  # 지역/레시피에 따라 돼지 케이스 많아 보수적으로 HARAM 처리(원하면 CAUTION로 변경 가능)
        "라드", "lard"
    ], "돼지고기(또는 돼지 유래) 포함 가능"),
    ("ALCOHOL", [
        "술", "소주", "맥주", "와인", "청주", "사케", "럼", "보드카", "위스키",
        "미림", "맛술", "와인소스", "beer", "wine"
    ], "알코올(또는 알코올 조리재) 포함"),
    ("BLOOD", [
        "선지", "피", "혈액"
    ], "혈액/선지(피) 유래 식품"),
    ("EXPLICIT_HARAM", [
        "하람", "non-halal", "비할랄"
    ], "명시적으로 비할랄/하람 표기"),
]

# (B) 원료/공정에 따라 달라지는 CAUTION: 젤라틴/렌넷/유화제 등
CAUTION_RULES = [
    ("GELATIN", ["젤라틴", "gelatin"], "젤라틴 원료가 돼지/비할랄일 수 있음"),
    ("RENNET", ["렌넷", "rennet"], "치즈 응고 효소(원료 확인 필요)"),
    ("EMULSIFIER", ["유화제", "mono", "diglyceride", "글리세리드"], "유화제(동물성 유래 가능)"),
    ("ENZYME_EXTRACT", ["효소", "추출물", "향료", "flavor", "extract"], "추출/향료 원료 및 용매 확인 필요"),
]

# (C) “고기류” 감지: 할랄 인증 여부 없으면 CAUTION
MEAT_KEYWORDS = [
    "소고기", "우육", "불고기", "갈비", "차돌", "양지",
    "닭", "치킨", "닭고기",
    "오리", "양고기", "염소고기",
]
HALAL_CERT_KEYWORDS = [
    "할랄", "halal", "halal-certified", "인증"
]

###############################################################################
# 2) 텍스트 정규화
###############################################################################
def norm(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def contains_any(text: str, keywords: list[str]) -> bool:
    t = norm(text)
    for k in keywords:
        if norm(k) in t:
            return True
    return False

###############################################################################
# 3) 판정 함수
###############################################################################
def halal_classify(menu_name: str, ingredients_ko: str = "") -> dict:
    text = f"{menu_name} | {ingredients_ko}"
    triggers = []

    # 1) HARAM 우선
    for rule_id, kws, reason in HARAM_RULES:
        if contains_any(text, kws):
            triggers.append((rule_id, reason))
    if triggers:
        return {
            "halal_decision": "HARAM",
            "haram_reason": " / ".join(sorted(set(r for _, r in triggers))),
            "haram_triggers": "; ".join(sorted(set(k for k, _ in triggers))),
            "needs_halal_cert": False,
        }

    # 2) CAUTION (첨가물/원료 불명)
    caution_triggers = []
    for rule_id, kws, reason in CAUTION_RULES:
        if contains_any(text, kws):
            caution_triggers.append((rule_id, reason))

    # 3) 고기류인데 할랄 인증 표기 없으면 CAUTION
    has_meat = contains_any(text, MEAT_KEYWORDS)
    has_halal_cert = contains_any(text, HALAL_CERT_KEYWORDS)

    if has_meat and not has_halal_cert:
        caution_triggers.append(("MEAT_NEEDS_CERT", "육류 포함 가능: 할랄 도축/인증 확인 필요"))

    if caution_triggers:
        return {
            "halal_decision": "CAUTION",
            "haram_reason": " / ".join(sorted(set(r for _, r in caution_triggers))),
            "haram_triggers": "; ".join(sorted(set(k for k, _ in caution_triggers))),
            "needs_halal_cert": bool(has_meat and not has_halal_cert),
        }

    # 4) 위에 걸리지 않으면 HALAL (보수적 기준)
    return {
        "halal_decision": "HALAL",
        "haram_reason": "",
        "haram_triggers": "",
        "needs_halal_cert": False,
    }

###############################################################################
# 4) 실행: CSV 로드 → 라벨링 → 저장
###############################################################################
df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")

# 컬럼명은 프로젝트에 따라 다를 수 있어요.
# 보통 당신 파일은 menu_core, ingredients_ko 등이 있음.
MENU_COL = "menu_core" if "menu_core" in df.columns else "ko_clean_primary"
ING_COL  = "ingredients_ko" if "ingredients_ko" in df.columns else ""

labels = df.apply(
    lambda r: halal_classify(
        menu_name=str(r.get(MENU_COL, "")),
        ingredients_ko=str(r.get(ING_COL, "")) if ING_COL else ""
    ),
    axis=1
)

# dict Series -> columns
label_df = pd.DataFrame(labels.tolist())
out = pd.concat([df, label_df], axis=1)

out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
print("Saved:", OUTPUT_CSV)
print(out["halal_decision"].value_counts())
