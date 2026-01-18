from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional


# ============================================================
# Non-menu filtering (do NOT change any paths; only filtering)
# ============================================================
# Goal: normalize.json should contain menu candidates ONLY.
# We keep existing output schema/paths intact and simply filter records
# before they are appended to items_normalized / items_merged.
# ============================================================
# Jaccard helpers (NEW)
# ============================================================

# 메뉴가 절대 될 수 없는 키워드
_NON_MENU_HARD_KEYWORDS = [
    "원산지", "국내산", "수입산",
    "인원", "인분",
    "포장", "배달",
    "셀프", "무한",
    "환불", "결제",
    "문의", "전화",
    "대로받습니다",
    "식자재", "유통",
]
# 2글자지만 실제 메뉴로 자주 등장하는 것들(필요시 추가)
_SHORT_MENU_ALLOW = {
    "만두", "냉면", "우동", "라면", "먹태", "전", "국", "탕"
}

# 섹션/카테고리성 단어(메뉴 아님)
_NON_MENU_CATEGORY_WORDS = {
    "안주", "사이드", "추가", "추가메뉴", "사리", "음료", "음료수", "주류", "메뉴"
}

def is_strict_menu_candidate(
    text_norm: str,
    detail_parts_norm: list[str] | None = None,
) -> bool:
    """
    Chroma 쿼리용 '진짜 메뉴' 판별 (보수적이되 과도하게 배제하지 않음)
    """
    if not text_norm:
        return False

    # 1) 너무 짧은 조각 텍스트 차단 (단, 예외 허용)
    if len(text_norm) < 2:
        return False
    if len(text_norm) == 2 and text_norm not in _SHORT_MENU_ALLOW:
        return False

    # 2) 하드 키워드 차단
    for kw in _NON_MENU_HARD_KEYWORDS:
        if kw in text_norm:
            return False

    # 3) 섹션/카테고리 단독 단어 차단
    if text_norm in _NON_MENU_CATEGORY_WORDS:
        return False

    # 4) 제목형 표현 차단
    if text_norm.endswith(("류", "메뉴", "안내")):
        return False

    # 5) detail_parts_norm(괄호) 유무는 더 이상 필수 조건이 아님
    #    (괄호 없는 메뉴가 훨씬 많음)

    return True


# Jaccard에 독이 되는 일반 메뉴 접미사
_JACCARD_DROP_SUFFIX = [
    "국", "탕", "찌개",
    "면", "밥", "죽",
    "볶음", "구이", "전", "튀김",
    "세트", "정식"
]
def normalize_for_jaccard(text: str) -> str:
    """
    Jaccard 계산 전용 문자열 생성
    - 한글만 유지
    - 공백 제거
    - 의미 없는 접미사 제거
    """
    s = normalize_korean_only(text)
    if not s:
        return ""

    for suf in _JACCARD_DROP_SUFFIX:
        if s.endswith(suf) and len(s) > len(suf) + 1:
            s = s[: -len(suf)]
            break

    return s


# Notice/guide/operation words that indicate non-menu sentences.
_NON_MENU_SUBSTRINGS = [
    "주문", "안내", "공지", "필수", "가능", "불가", "포장", "매장", "이용",
    "시간", "휴무", "전화", "문의", "원산지", "알레르기", "알러지", "주의",
]

# Common section titles (non-menu headers).
_NON_MENU_TITLES = {
    "추가메뉴", "사이드", "사리", "추가", "음료", "음료수", "주류", "메뉴",
}

def _looks_like_notice(raw_text: str, menu_norm: str) -> bool:
    t = (raw_text or "").strip()
    if not t:
        return True

    # Bullet/marker + notice content (e.g., "※ 1인 1메뉴 주문입니다")
    if t.startswith(("※", "*", "•", "-", "·")):
        for s in _NON_MENU_SUBSTRINGS:
            if s in t:
                return True

    # Normalized text still contains notice/operation words
    for s in _NON_MENU_SUBSTRINGS:
        if s in (menu_norm or ""):
            return True

    return False

def is_menu_candidate(raw_text: str, menu_norm: Optional[str], score: float, cfg: "NormalizeConfig") -> bool:
    """
    Returns True if the record should be kept as a menu candidate.
    This function MUST NOT affect any file paths; it only determines
    whether an OCR item is included in normalized outputs.
    """
    if not menu_norm:
        return False
    if len(menu_norm) < cfg.min_len:
        return False
    if score < cfg.min_score:
        return False

    if menu_norm in _NON_MENU_TITLES:
        return False

    if _looks_like_notice(raw_text, menu_norm):
        return False

    return True

# ============================================================
# 1) Normalization: keep Hangul only + join spaces
# ============================================================
_KEEP_KO_AND_SPACE = re.compile(r"[^가-힣\s]+", re.UNICODE)
_MULTI_SPACE = re.compile(r"\s+", re.UNICODE)

def normalize_korean_only(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    s = _KEEP_KO_AND_SPACE.sub("", s)      # keep Hangul + space only
    s = _MULTI_SPACE.sub(" ", s).strip()   # normalize spaces
    s = s.replace(" ", "")                 # join spaces: "삼 겹살" -> "삼겹살"
    return s


# ============================================================
# 2) Parentheses split + detail split (BEFORE stripping symbols)
# ============================================================
# "만두샤브세트(만두3개+소고기+갈국수)" -> ("만두샤브세트", "만두3개+소고기+갈국수")
_PAREN_RE = re.compile(r"^\s*(.*?)\s*\(\s*(.*?)\s*\)\s*$")
# details split tokens: + , / · ㆍ & |  (원하면 더 추가)
_DETAIL_SPLIT_RE = re.compile(r"[+,/·ㆍ&\|]|,", re.UNICODE)

def split_parentheses(raw_text: str) -> Tuple[str, Optional[str]]:
    t = (raw_text or "").strip()
    m = _PAREN_RE.match(t)
    if not m:
        return t, None
    return m.group(1).strip(), m.group(2).strip()

def split_detail(detail_raw: str) -> List[str]:
    parts = [p.strip() for p in _DETAIL_SPLIT_RE.split(detail_raw) if p and p.strip()]
    return parts
# 메뉴명 내 variant 분리: "물냉면/비빔냉면" -> ["물냉면", "비빔냉면"]
_MENU_SPLIT_RE = re.compile(r"\s*/\s*", re.UNICODE)

def split_menu_variants(menu_raw: str) -> List[str]:
    parts = [p.strip() for p in _MENU_SPLIT_RE.split(menu_raw or "") if p and p.strip()]
    return parts if parts else [(menu_raw or "").strip()]



def build_structured_fields(raw_text: str) -> Dict[str, Any]:
    """
    Step_03 핵심:
    - 괄호 바깥(메뉴명) / 괄호 안(detail) 분리
    - 메뉴명은 "/" 기준으로 variants 분할 저장
    - RAG 키(대표)는 menu_name_norm = 첫 번째 variant의 norm
    """
    menu_raw, detail_raw = split_parentheses(raw_text)

    # ✅ 메뉴명 "/" variants split (정규화 이전에 수행)
    variants_raw = split_menu_variants(menu_raw)
    variants_norm = [normalize_korean_only(v) for v in variants_raw]
    variants_norm = [v for v in variants_norm if v]

    # ✅ Jaccard 전용 variants
    variants_jaccard = [normalize_for_jaccard(v) for v in variants_norm]
    variants_jaccard = [v for v in variants_jaccard if v]

    menu_norm = variants_norm[0] if variants_norm else None
    menu_jaccard = variants_jaccard[0] if variants_jaccard else None

    detail_parts_raw: List[str] = []
    detail_parts_norm: List[str] = []

    if detail_raw:
        detail_parts_raw = split_detail(detail_raw)
        detail_parts_norm = [normalize_korean_only(p) for p in detail_parts_raw]
        detail_parts_norm = [p for p in detail_parts_norm if p]  # 빈 값 제거

    is_set = ("세트" in menu_raw) or (detail_raw is not None)
    menu_candidate = is_strict_menu_candidate(
        menu_norm,
        detail_parts_norm,
    )

    return {
        "menu_name_raw": menu_raw,
        "menu_name_norm": menu_norm,
        "menu_name_variants_raw": variants_raw,
        "menu_name_variants_norm": variants_norm,

        "menu_name_jaccard": menu_jaccard,
        "menu_name_variants_jaccard": variants_jaccard,

        "detail_raw": detail_raw,
        "detail_parts_raw": detail_parts_raw,
        "detail_parts_norm": detail_parts_norm,

        "menu_candidate": menu_candidate,  # ✅ NEW

        "has_parentheses": detail_raw is not None,
        "is_set": is_set,
    }


# ============================================================
# 3) bbox utils + line grouping + merging
# ============================================================
def bbox_center(bbox: List[int]) -> Tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0

def bbox_height(bbox: List[int]) -> int:
    return int(bbox[3] - bbox[1])

def horizontal_gap(prev_bbox: List[int], cur_bbox: List[int]) -> int:
    return int(cur_bbox[0] - prev_bbox[2])


@dataclass
class NormalizeConfig:
    min_len: int = 2
    line_y_tol: int = 20
    merge_gap_px: int = 25       # base gap (dynamic gap uses max(base, h*ratio))
    min_score: float = 0.0


def group_items_by_line(items: List[Dict[str, Any]], y_tol: int) -> List[List[Dict[str, Any]]]:
    valid = []
    for it in items:
        bbox = it.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        cx, cy = bbox_center(bbox)
        it["_cy"] = cy
        it["_cx"] = cx
        valid.append(it)

    valid.sort(key=lambda x: (x["_cy"], x["_cx"]))

    lines: List[List[Dict[str, Any]]] = []
    for it in valid:
        if not lines:
            lines.append([it])
            continue
        last_line = lines[-1]
        if abs(it["_cy"] - last_line[-1]["_cy"]) <= y_tol:
            last_line.append(it)
        else:
            lines.append([it])

    for line in lines:
        line.sort(key=lambda x: x["_cx"])
    return lines


def merge_line_tokens(line: List[Dict[str, Any]], merge_gap_px: int = 25) -> List[Dict[str, Any]]:
    """
    같은 라인에서 인접 박스 병합.
    - 병합 "대표 텍스트": menu_name_norm (첫 variant)
    - variants: menu_name_variants_norm를 aggregate + dedup
    - detail_parts_norm도 aggregate + dedup
    """
    merged: List[Dict[str, Any]] = []
    current_jaccard_variants: List[str] = []
    current_menu_candidate = False

    def union_bbox(a, b):
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]

    current_text = ""
    current_bbox: Optional[List[int]] = None
    current_members: List[int] = []

    current_detail_parts: List[str] = []
    current_variants: List[str] = []

    def dedup_keep_order(seq: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in seq:
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out

    def flush():
        nonlocal current_text, current_bbox, current_members
        nonlocal current_detail_parts, current_variants, current_jaccard_variants, current_menu_candidate

        j_variants = dedup_keep_order(current_jaccard_variants)
        if current_text:
            merged.append({
                "text": current_text,
                "bbox": current_bbox,
                "members": current_members[:],
                "menu_variants_norm": dedup_keep_order(current_variants),
                "menu_variants_jaccard": j_variants,
                "menu_jaccard": j_variants[0] if j_variants else None,
                "menu_candidate": current_menu_candidate,
                "detail_parts_norm": dedup_keep_order(current_detail_parts),
            })

        current_text, current_bbox, current_members = "", None, []
        current_detail_parts, current_variants = [], []
        current_jaccard_variants = []
        current_menu_candidate = False



    for it in line:
        raw = it.get("text", "")

        fields = it.get("_fields") or build_structured_fields(raw)
        norm = fields.get("menu_name_norm") or ""
        variants_norm = fields.get("menu_name_variants_norm") or []
        detail_parts_norm = fields.get("detail_parts_norm") or []
        variants_jaccard = fields.get("menu_name_variants_jaccard") or []

        if not norm:
            continue

        bbox = it["bbox"]
        idx = it.get("_idx")

        if current_bbox is None:
            current_text = norm
            current_bbox = bbox[:]
            current_members = [idx] if idx is not None else []
            current_variants = list(variants_norm)
            current_detail_parts = list(detail_parts_norm)
            current_jaccard_variants = list(variants_jaccard)
            current_menu_candidate = bool(fields.get("menu_candidate", False))

            continue

        gap = horizontal_gap(current_bbox, bbox)

        # ---- dynamic gap: handle far split like "만" + "두" ----
        prev_h = bbox_height(current_bbox)
        cur_h = bbox_height(bbox)
        h = (prev_h + cur_h) / 2.0
        adaptive_gap = max(merge_gap_px, int(h * 1.8))

        # ---- anti-over-merge: only allow wide-gap merge for short tokens ----
        prev_len = len(current_text)
        cur_len = len(norm)
        short_token_merge = (prev_len <= 2 and cur_len <= 2 and (prev_len + cur_len) <= 4)

        if gap <= adaptive_gap and short_token_merge:
            current_text += norm
            current_bbox = union_bbox(current_bbox, bbox)
            if idx is not None:
                current_members.append(idx)

            # aggregate
            current_variants.extend(variants_norm)
            current_jaccard_variants.extend(variants_jaccard)
            current_detail_parts.extend(detail_parts_norm)
            current_menu_candidate = (
                    current_menu_candidate or fields.get("menu_candidate", False)
            )


        else:
            flush()
            current_text = norm
            current_bbox = bbox[:]
            current_members = [idx] if idx is not None else []
            current_variants = list(variants_norm)
            current_detail_parts = list(detail_parts_norm)
            current_jaccard_variants = list(variants_jaccard)
            current_menu_candidate = bool(fields.get("menu_candidate", False))


    flush()

    return merged



# ============================================================
# 4) Step_03 runner
# ============================================================
def run_step_03_normalize(ocr_json_path: Path, out_json_path: Path, cfg: NormalizeConfig) -> Path:
    with ocr_json_path.open("r", encoding="utf-8") as f:
        ocr = json.load(f)

    items = ocr.get("items", [])

    items_normalized: List[Dict[str, Any]] = []
    filtered_for_merge: List[Dict[str, Any]] = []

    for i, it in enumerate(items):
        raw_text = it.get("text", "")
        score = float(it.get("score", 0.0))
        bbox = it.get("bbox")

        fields = build_structured_fields(raw_text)
        menu_norm = fields.get("menu_name_norm")

        # ✅ Keep menus only: do not append non-menu records to outputs
        if not is_menu_candidate(raw_text=raw_text, menu_norm=menu_norm, score=score, cfg=cfg):
            continue

        rec = {
            "idx": i,
            "raw_text": raw_text,
            "score": score,
            "bbox": bbox,
            "poly": it.get("poly"),

            # ✅ 구조화 필드 저장(메뉴/variants/detail)
            **fields,
        }

        items_normalized.append(rec)

        # ✅ 병합/후속 Step_04 RAG 대상도 '메뉴만'
        if bbox:
            it2 = dict(it)
            it2["_idx"] = i
            it2["_fields"] = fields  # ✅ 구조화 결과 재사용
            filtered_for_merge.append(it2)

    lines = group_items_by_line(filtered_for_merge, y_tol=cfg.line_y_tol)
    merged_all: List[Dict[str, Any]] = []
    for line in lines:
        merged_all.extend(merge_line_tokens(line, merge_gap_px=cfg.merge_gap_px))

    out = {
        "image": ocr.get("image"),
        "image_shape": ocr.get("image_shape"),
        "engine": ocr.get("engine"),
        "elapsed_ms": ocr.get("elapsed_ms"),
        "paddleocr_config": ocr.get("paddleocr_config"),
        "normalize_config": {
            "min_len": cfg.min_len,
            "line_y_tol": cfg.line_y_tol,
            "merge_gap_px": cfg.merge_gap_px,
            "min_score": cfg.min_score,
            "rule": {
                "menu_key": "menu_name_norm (outside parentheses only)",
                "detail": "split parentheses detail into detail_parts_*",
                "merge": "merge short adjacent tokens in same line; dynamic gap by height",
            },
        },
        "items_normalized": items_normalized,
        "items_merged": merged_all,
    }

    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    with out_json_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    return out_json_path


# ============================================================
# 5) CLI (input fixed: run_dir/ocr/ocr.json)
# ============================================================
def _find_latest_run_dir(runs_root: Path) -> Path:
    run_dirs = [p for p in runs_root.iterdir() if p.is_dir()]
    if not run_dirs:
        raise FileNotFoundError(f"No run directories under: {runs_root}")
    run_dirs.sort(key=lambda p: p.name)
    return run_dirs[-1]


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Step 03: normalize + split set details + merge short tokens.")
    p.add_argument("--runs-root", default="menu_assistant/data/runs", help="Runs root directory")
    p.add_argument("--run-id", default=None, help="Run id (e.g., 20260112_193336). If omitted, use latest.")
    p.add_argument("--out-json", default=None, help="Override output json path")

    p.add_argument("--min-len", type=int, default=2)
    p.add_argument("--line-y-tol", type=int, default=20)
    p.add_argument("--merge-gap-px", type=int, default=25)
    p.add_argument("--min-score", type=float, default=0.0)

    args = p.parse_args()

    runs_root = Path(args.runs_root)
    run_dir = (runs_root / args.run_id) if args.run_id else _find_latest_run_dir(runs_root)

    in_json = run_dir / "ocr" / "ocr.json"
    if not in_json.exists():
        raise FileNotFoundError(f"Expected input not found: {in_json}")

    out_json = Path(args.out_json) if args.out_json else (run_dir / "normalize" / "normalize.json")

    cfg = NormalizeConfig(
        min_len=args.min_len,
        line_y_tol=args.line_y_tol,
        merge_gap_px=args.merge_gap_px,
        min_score=args.min_score,
    )

    result = run_step_03_normalize(in_json, out_json, cfg)

    print("=== step_03_normalize DONE ===")
    print(f"run_dir: {run_dir}")
    print(f"input : {in_json}")
    print(f"output: {result}")
    print(f"config: {cfg}")
