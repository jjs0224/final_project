from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------
# OCR 이후 얻어낸 json 파일을 토대로 메뉴명 영어,숫자 제거후 메뉴만 남도록 정규화
# --------------------------------------------------------------------



# ---------------------------
# 1) 텍스트 정규화/판별 유틸
# ---------------------------

HANGUL_RE = re.compile(r"[가-힣]")
PRICE_RE = re.compile(r"^\s*\d{1,3}(?:,\d{3})+\s*$")  # 17,000
TIME_RE = re.compile(r"\d{1,2}:\d{2}")               # 17:00
RANGE_TIME_RE = re.compile(r"\d{1,2}:\d{2}\s*~\s*\d{1,2}:\d{2}")
ONLY_SYMBOL_RE = re.compile(r"^[\W_]+$")             # 기호만
MOSTLY_NUMBER_RE = re.compile(r"^[\d\s,.\-~:/()]+$")  # 숫자/기호 위주

# 메뉴가 아닌 안내/구분 텍스트에 자주 등장하는 키워드(필요시 계속 추가)
STOPWORDS = {
    "영업시간", "라스트오더", "이용시간", "제한", "구성", "변경", "당일",
    "국내산", "중국산", "덴마크", "브라질", "원산지",
    "디저트", "별미", "튀김",  # 카테고리 제목을 제외하고 싶으면 유지
}

# OCR 노이즈에 자주 등장하는 단발 토큰류
JUNK_TOKENS = {"", " ", "ㅁ", "Xㅁ", "X", "$", "N", "i1]", "LE71", "그ㅁ\""}


def normalize_text(s: str) -> str:
    if s is None:
        return ""

    # 1️⃣ Unicode 정규화
    s = unicodedata.normalize("NFKC", s)

    # 2️⃣ 영어 제거 (대소문자)
    s = re.sub(r"[A-Za-z]", "", s)

    # 3️⃣ 숫자 제거
    s = re.sub(r"\d", "", s)

    # 4️⃣ 불필요한 기호 제거
    s = re.sub(r"[•·]", "", s)

    # 5️⃣ 괄호만 남은 경우 제거
    s = re.sub(r"[()\[\]{}]", "", s)

    # 6️⃣ 공백 정리
    s = re.sub(r"\s+", " ", s).strip()

    # 7️⃣ 따옴표 정리
    s = s.strip(" \"'")

    return s



def hangul_ratio(s: str) -> float:
    if not s:
        return 0.0
    hangul = len(HANGUL_RE.findall(s))
    return hangul / max(len(s), 1)


def is_price_like(s: str) -> bool:
    s2 = s.replace(" ", "")
    return bool(PRICE_RE.match(s2)) or ("원" in s2 and any(ch.isdigit() for ch in s2))


def is_time_like(s: str) -> bool:
    return bool(RANGE_TIME_RE.search(s) or TIME_RE.search(s))


def looks_like_menu_name(s: str) -> bool:
    """규칙 기반 메뉴명 후보 판별."""
    if not s:
        return False

    if s in JUNK_TOKENS:
        return False

    if ONLY_SYMBOL_RE.match(s):
        return False

    # 숫자/기호 비중이 과도하면 제외
    if MOSTLY_NUMBER_RE.match(s):
        return False

    # 시간/가격 제거
    if is_time_like(s) or is_price_like(s):
        return False

    # 한글 비율이 너무 낮으면 제외(영문/코드/잡텍스트 방지)
    if hangul_ratio(s) < 0.35:
        return False

    # 너무 짧은 토큰 제외 (단, "참돔" 같은 2글자 메뉴가 있어서 2는 허용)
    if len(s) < 2:
        return False

    # 안내/구분 키워드 단독 등장 제외
    if s in STOPWORDS:
        return False

    # "2인54,000" 같이 인원+가격 붙은 형태 제외
    if re.search(r"\d+인", s) and any(ch.isdigit() for ch in s):
        return False

    return True


# ---------------------------
# 2) OCR JSON 로드/결과 구조
# ---------------------------

@dataclass
class OcrItem:
    text_raw: str
    text: str
    score: float
    box: List[int]  # [x1, y1, x2, y2]
    idx: int

    @property
    def cx(self) -> float:
        return (self.box[0] + self.box[2]) / 2.0

    @property
    def cy(self) -> float:
        return (self.box[1] + self.box[3]) / 2.0

    @property
    def area(self) -> int:
        w = max(0, self.box[2] - self.box[0])
        h = max(0, self.box[3] - self.box[1])
        return w * h


def load_ocr_json(ocr_json_path: Path) -> List[OcrItem]:
    data = json.loads(ocr_json_path.read_text(encoding="utf-8"))

    texts = data.get("rec_texts", [])
    scores = data.get("rec_scores", [])
    boxes = data.get("rec_boxes", [])

    n = min(len(texts), len(scores), len(boxes))
    items: List[OcrItem] = []
    for i in range(n):
        raw = texts[i] if texts[i] is not None else ""
        norm = normalize_text(raw)
        items.append(
            OcrItem(
                text_raw=raw,
                text=norm,
                score=float(scores[i]),
                box=list(map(int, boxes[i])),
                idx=i,
            )
        )
    return items


def score_menu_candidate(item: OcrItem) -> float:
    """메뉴 후보 우선순위 점수(정렬용)."""
    hr = hangul_ratio(item.text)
    base = item.score

    # 패널티: 너무 작거나(한 글자급) 면적이 극단적으로 작은 경우
    penalty = 1.0
    if item.area < 200:   # 상황에 따라 조정
        penalty *= 0.3

    # 패널티: STOPWORDS 포함(단독이 아니더라도 안내 문구 가능성)
    if any(sw in item.text for sw in STOPWORDS):
        penalty *= 0.6

    return base * (0.6 + 0.4 * hr) * penalty


def extract_menu_candidates(
    items: List[OcrItem],
    min_ocr_score: float = 0.70,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    for it in items:
        if it.score < min_ocr_score:
            continue

        if not looks_like_menu_name(it.text):
            continue

        out.append(
            {
                "text": it.text,
                "text_raw": it.text_raw,
                "ocr_score": it.score,
                "hangul_ratio": round(hangul_ratio(it.text), 4),
                "box": it.box,         # [x1,y1,x2,y2]
                "center": [round(it.cx, 2), round(it.cy, 2)],
                "idx": it.idx,
                "menu_score": round(score_menu_candidate(it), 6),
            }
        )

    # menu_score로 정렬 (높은 게 더 메뉴 같음)
    out.sort(key=lambda d: d["menu_score"], reverse=True)
    return out


# ---------------------------
# 3) CLI: meta -> json_path -> candidates 저장
# ---------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", required=True, help="*_run_meta.json 경로")
    ap.add_argument("--min_ocr_score", type=float, default=0.70)
    ap.add_argument("--out", default=None, help="결과 저장 경로 (기본: meta와 같은 폴더/menu_candidates.json)")
    args = ap.parse_args()

    meta_path = Path(args.meta).resolve()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    ocr_json_path = Path(meta["json_path"]).resolve()
    out_path = Path(args.out).resolve() if args.out else (meta_path.parent / "menu_candidates.json")

    items = load_ocr_json(ocr_json_path)
    candidates = extract_menu_candidates(items, min_ocr_score=args.min_ocr_score)

    payload = {
        "input_image": meta.get("input_image"),
        "ocr_json_path": str(ocr_json_path),
        "count_all_items": len(items),
        "count_menu_candidates": len(candidates),
        "min_ocr_score": args.min_ocr_score,
        "menu_candidates": candidates,
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] saved: {out_path}")
    print(f" - menu candidates: {len(candidates)} / all: {len(items)}")


if __name__ == "__main__":
    main()
