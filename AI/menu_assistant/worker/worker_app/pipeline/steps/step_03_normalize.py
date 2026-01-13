from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional


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
    variants_norm = [v for v in variants_norm if v]  # 빈 값 제거

    # 대표 메뉴명: 첫 번째 variant
    menu_norm = variants_norm[0] if variants_norm else None

    detail_parts_raw: List[str] = []
    detail_parts_norm: List[str] = []

    if detail_raw:
        detail_parts_raw = split_detail(detail_raw)
        detail_parts_norm = [normalize_korean_only(p) for p in detail_parts_raw]
        detail_parts_norm = [p for p in detail_parts_norm if p]  # 빈 값 제거

    is_set = ("세트" in menu_raw) or (detail_raw is not None)

    return {
        "menu_name_raw": menu_raw,
        "menu_name_norm": menu_norm,
        "menu_name_variants_raw": variants_raw,
        "menu_name_variants_norm": variants_norm,

        "detail_raw": detail_raw,
        "detail_parts_raw": detail_parts_raw,
        "detail_parts_norm": detail_parts_norm,

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
        nonlocal current_text, current_bbox, current_members, current_detail_parts, current_variants
        if current_text:
            merged.append({
                "text": current_text,  # 대표 메뉴명(norm)
                "bbox": current_bbox,
                "members": current_members[:],
                "menu_variants_norm": dedup_keep_order(current_variants),
                "detail_parts_norm": dedup_keep_order(current_detail_parts),
            })
        current_text, current_bbox, current_members = "", None, []
        current_detail_parts, current_variants = [], []

    for it in line:
        raw = it.get("text", "")

        fields = build_structured_fields(raw)
        norm = fields.get("menu_name_norm") or ""
        variants_norm = fields.get("menu_name_variants_norm") or []
        detail_parts_norm = fields.get("detail_parts_norm") or []

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
            current_detail_parts.extend(detail_parts_norm)
        else:
            flush()
            current_text = norm
            current_bbox = bbox[:]
            current_members = [idx] if idx is not None else []
            current_variants = list(variants_norm)
            current_detail_parts = list(detail_parts_norm)

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

        rec = {
            "idx": i,
            "raw_text": raw_text,
            "score": score,
            "bbox": bbox,
            "poly": it.get("poly"),

            # ✅ 구조화 필드 저장(핵심)
            **fields,
        }

        # drop reason: 이제 normalized는 menu_name_norm 기준으로 판단
        if not menu_norm:
            rec["dropped_reason"] = "no_korean_in_menu_name_after_filter"
        elif len(menu_norm) < cfg.min_len:
            rec["dropped_reason"] = "menu_name_too_short_after_normalize"

        items_normalized.append(rec)

        # ✅ 병합/후속 Step_04 RAG 키는 menu_name_norm만 사용
        if bbox and menu_norm and len(menu_norm) >= cfg.min_len and score >= cfg.min_score:
            it2 = dict(it)
            it2["_idx"] = i
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
