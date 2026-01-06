from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer


# =========================================================
# 1) Normalization (요구사항 유지: 영어/숫자 먼저 제거 + 기존 정규화)
# =========================================================
_re_eng = re.compile(r"[A-Za-z]")
_re_num = re.compile(r"\d")
_re_keep_kor_space = re.compile(r"[^가-힣\s]")
_re_multi_space = re.compile(r"\s+")

def normalize_menu_text(text: str, remove_space: bool = True) -> str:
    """
    1) 영어 제거
    2) 숫자 제거
    3) 한글/공백 중심 유지 + 공백 정리
    4) (옵션) 띄어쓰기 제거
    """
    if not text:
        return ""
    t = text.strip()
    t = _re_eng.sub("", t)
    t = _re_num.sub("", t)
    t = _re_keep_kor_space.sub(" ", t)
    t = _re_multi_space.sub(" ", t).strip()
    if remove_space:
        t = t.replace(" ", "")
    return t

def is_menu_candidate(norm_text: str) -> bool:
    if len(norm_text.replace(" ", "")) < 2:
        return False
    return any("가" <= ch <= "힣" for ch in norm_text)


# =========================================================
# 2) Hangul Jamo utilities (자모 기반 비교 핵심)
# =========================================================
CHOSUNG = [
    "ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"
]
JUNGSUNG = [
    "ㅏ","ㅐ","ㅑ","ㅒ","ㅓ","ㅔ","ㅕ","ㅖ","ㅗ","ㅘ","ㅙ","ㅚ","ㅛ","ㅜ","ㅝ","ㅞ","ㅟ","ㅠ","ㅡ","ㅢ","ㅣ"
]
JONGSUNG = [
    "", "ㄱ","ㄲ","ㄳ","ㄴ","ㄵ","ㄶ","ㄷ","ㄹ","ㄺ","ㄻ","ㄼ","ㄽ","ㄾ","ㄿ","ㅀ","ㅁ","ㅂ","ㅄ","ㅅ","ㅆ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"
]

def to_jamo(text: str) -> str:
    """
    한글 문자열을 자모 시퀀스로 변환.
    - 공백 제거 후 비교하는 것이 매칭 안정성에 유리
    """
    t = text.replace(" ", "")
    out = []
    for ch in t:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            base = code - 0xAC00
            cho = base // 588
            jung = (base % 588) // 28
            jong = base % 28
            out.append(CHOSUNG[cho])
            out.append(JUNGSUNG[jung])
            if JONGSUNG[jong]:
                out.append(JONGSUNG[jong])
        else:
            # 한글 외 문자는 그대로 포함(여기서는 정규화에서 대부분 제거됨)
            out.append(ch)
    return "".join(out)

def ngrams(s: str, n: int = 2) -> List[str]:
    if len(s) < n:
        return [s] if s else []
    return [s[i:i+n] for i in range(len(s) - n + 1)]

def jamo_ngram_jaccard(a: str, b: str, n: int = 2) -> float:
    """
    자모 문자열을 n-gram으로 만들고 Jaccard 유사도 계산
    - OCR 오타(꼬/코, 되/돼 등)에 상당히 강함
    """
    if not a or not b:
        return 0.0
    A = set(ngrams(a, n))
    B = set(ngrams(b, n))
    if not A or not B:
        return 0.0
    inter = len(A & B)
    union = len(A | B)
    return inter / union if union else 0.0


# =========================================================
# 3) RAG Retriever (임베딩 검색) + 자모 리랭킹
# =========================================================
@dataclass
class MenuEntry:
    menu: str
    norm_menu: str
    ingredients_ko: Optional[List[str]]

class MenuRAGMatcher:
    def __init__(self, model_name: str, use_faiss: bool = True):
        self.model = SentenceTransformer(model_name)
        self.use_faiss = use_faiss

        self.entries: List[MenuEntry] = []
        self.norm_to_idx: Dict[str, int] = {}

        self.emb: Optional[np.ndarray] = None  # (N, D), normalized
        self.faiss_index = None

    def build_from_json(self, dict_path: Path):
        rows = json.loads(dict_path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError("menuName_ingredients.json must be a JSON list.")

        self.entries = []
        self.norm_to_idx = {}

        for row in rows:
            menu = str(row.get("menu", "")).strip()
            if not menu:
                continue
            # ✅ 사전 쪽도 동일 정책: 공백 제거된 정규화로 인덱싱
            norm = normalize_menu_text(menu, remove_space=True)
            if not norm:
                continue

            entry = MenuEntry(menu=menu, norm_menu=norm, ingredients_ko=row.get("ingredients_ko"))

            # 같은 norm 충돌 시 첫 항목 유지(정책 변경 가능)
            if norm not in self.norm_to_idx:
                self.norm_to_idx[norm] = len(self.entries)
                self.entries.append(entry)

        texts = [e.norm_menu for e in self.entries]
        emb = self.model.encode(
            texts,
            batch_size=64,
            show_progress_bar=True,
            normalize_embeddings=True
        )
        self.emb = np.array(emb, dtype=np.float32)

        if self.use_faiss:
            try:
                import faiss  # type: ignore
                d = self.emb.shape[1]
                index = faiss.IndexFlatIP(d)  # cosine == IP (normalized)
                index.add(self.emb)
                self.faiss_index = index
            except Exception:
                self.use_faiss = False
                self.faiss_index = None

    def save(self, out_dir: Path):
        out_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "count": len(self.entries),
            "use_faiss": self.use_faiss,
        }
        (out_dir / "index_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        entries_payload = [
            {"menu": e.menu, "norm_menu": e.norm_menu, "ingredients_ko": e.ingredients_ko}
            for e in self.entries
        ]
        (out_dir / "entries.json").write_text(json.dumps(entries_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        np.save(out_dir / "emb.npy", self.emb)

        if self.use_faiss and self.faiss_index is not None:
            import faiss  # type: ignore
            faiss.write_index(self.faiss_index, str(out_dir / "faiss.index"))

    def load(self, index_dir: Path, model_name: str):
        self.model = SentenceTransformer(model_name)

        entries_payload = json.loads((index_dir / "entries.json").read_text(encoding="utf-8"))
        self.entries = [
            MenuEntry(menu=e["menu"], norm_menu=e["norm_menu"], ingredients_ko=e.get("ingredients_ko"))
            for e in entries_payload
        ]
        self.norm_to_idx = {e.norm_menu: i for i, e in enumerate(self.entries)}
        self.emb = np.load(index_dir / "emb.npy").astype(np.float32)

        meta = json.loads((index_dir / "index_meta.json").read_text(encoding="utf-8"))
        self.use_faiss = bool(meta.get("use_faiss", False))

        if self.use_faiss:
            try:
                import faiss  # type: ignore
                self.faiss_index = faiss.read_index(str(index_dir / "faiss.index"))
            except Exception:
                self.use_faiss = False
                self.faiss_index = None

    def retrieve(self, norm_query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        if self.emb is None or len(self.entries) == 0:
            return []

        q_emb = self.model.encode([norm_query], normalize_embeddings=True)
        q = np.array(q_emb, dtype=np.float32)

        if self.use_faiss and self.faiss_index is not None:
            scores, idxs = self.faiss_index.search(q, top_k)
            res = []
            for i, s in zip(idxs[0], scores[0]):
                if i < 0:
                    continue
                res.append((int(i), float(s)))
            return res

        scores = (self.emb @ q[0]).astype(np.float32)
        top = np.argsort(-scores)[:top_k]
        return [(int(i), float(scores[i])) for i in top]

    # --------------------------
    # 매칭 결정 로직(자모 기반)
    # --------------------------
    @staticmethod
    def adaptive_threshold(norm_query: str, base: float) -> float:
        n = len(norm_query.replace(" ", ""))
        if n <= 2:
            return max(base, 0.985)
        if n == 3:
            return max(base, 0.96)
        return base

    @staticmethod
    def margin_gate(best: float, second: Optional[float], min_margin: float = 0.05) -> bool:
        if second is None:
            return True
        return (best - second) >= min_margin

    def rerank_with_jamo(self, norm_query: str, hits: List[Tuple[int, float]], top_k: int = 10):
        """
        hits: [(idx, cosine), ...]
        리랭크 점수:
          final = 0.65*cosine + 0.35*jamo_jaccard
        + 자모 overlap 필터로 엉뚱한 후보 제거
        """
        qj = to_jamo(norm_query)

        rescored = []
        for idx, cos in hits[:top_k]:
            cand_norm = self.entries[idx].norm_menu
            cj = to_jamo(cand_norm)

            jacc = jamo_ngram_jaccard(qj, cj, n=2)

            # 너무 동떨어진 표기는 제거 (터무니없는 매칭 방지에 매우 효과적)
            if jacc < 0.22:
                continue

            final = 0.65 * cos + 0.35 * jacc
            rescored.append((idx, final, cos, jacc))

        rescored.sort(key=lambda x: x[1], reverse=True)
        return rescored

    def match(self, norm_query: str, threshold: float = 0.90, top_k: int = 10) -> Dict[str, Any]:
        # 0) 너무 짧은 텍스트는 매칭 금지(엉뚱한 결과를 거의 확실히 유발)
        if len(norm_query.replace(" ", "")) < 3:
            return {
                "final_text": norm_query,
                "ingredient": None,
                "match_score": 0.0,
                "match_type": "too_short",
                "matched_norm": None,
            }

        # 1) Exact match
        if norm_query in self.norm_to_idx:
            idx = self.norm_to_idx[norm_query]
            e = self.entries[idx]
            return {
                "final_text": e.menu,
                "ingredient": e.ingredients_ko,
                "match_score": 1.0,
                "match_type": "exact",
                "matched_norm": e.norm_menu,
            }

        # 2) Retriever
        hits = self.retrieve(norm_query, top_k=top_k)
        if not hits:
            return {
                "final_text": norm_query,
                "ingredient": None,
                "match_score": 0.0,
                "match_type": "none",
                "matched_norm": None,
            }

        # 3) Jamo re-rank
        rescored = self.rerank_with_jamo(norm_query, hits, top_k=top_k)
        if not rescored:
            # 리랭크 필터에서 다 탈락: 매칭하지 않는 것이 안전
            return {
                "final_text": norm_query,
                "ingredient": None,
                "match_score": float(hits[0][1]),
                "match_type": "filtered_out_by_jamo",
                "matched_norm": None,
            }

        best = rescored[0]
        second = rescored[1] if len(rescored) > 1 else None

        best_idx, best_final, best_cos, best_jacc = best
        th = self.adaptive_threshold(norm_query, threshold)
        margin_ok = self.margin_gate(best_final, second[1] if second else None, min_margin=0.05)

        if best_final >= th and margin_ok:
            e = self.entries[best_idx]
            return {
                "final_text": e.menu,
                "ingredient": e.ingredients_ko,
                "match_score": float(best_final),
                "match_type": "rag_jamo_reranked",
                "matched_norm": e.norm_menu,
                "debug": {"cos": float(best_cos), "jamo_jaccard": float(best_jacc)},
            }

        # 미채택(확신 부족): 원본 정규화 텍스트 유지
        return {
            "final_text": norm_query,
            "ingredient": None,
            "match_score": float(best_final),
            "match_type": "below_threshold_or_low_margin",
            "matched_norm": self.entries[best_idx].norm_menu,
            "debug": {"cos": float(best_cos), "jamo_jaccard": float(best_jacc)},
        }


# =========================================================
# 4) OCR meta -> rec_texts 처리
# =========================================================
def load_meta(meta_path: Path) -> Dict[str, Any]:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if "json_path" not in meta:
        raise ValueError("meta json must include 'json_path'.")
    return meta

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["build", "run"], required=True)
    ap.add_argument("--dict", help="menuName_ingredients.json path (build mode)")
    ap.add_argument("--index_dir", required=True, help="index directory path")
    ap.add_argument("--model", default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
    ap.add_argument("--meta", help="*_run_meta.json path (run mode)")
    ap.add_argument("--out", help="output json path (run mode)")
    ap.add_argument("--threshold", type=float, default=0.90)
    ap.add_argument("--top_k", type=int, default=10)
    ap.add_argument("--min_len", type=int, default=2)
    args = ap.parse_args()

    index_dir = Path(args.index_dir)

    if args.mode == "build":
        if not args.dict:
            raise ValueError("--dict is required for build mode")

        matcher = MenuRAGMatcher(model_name=args.model, use_faiss=True)
        matcher.build_from_json(Path(args.dict))
        matcher.save(index_dir)
        print(f"[OK] built index: {index_dir} (count={len(matcher.entries)})")
        return

    # run mode
    if not args.meta or not args.out:
        raise ValueError("--meta and --out are required for run mode")

    matcher = MenuRAGMatcher(model_name=args.model, use_faiss=True)
    matcher.load(index_dir, model_name=args.model)

    meta = load_meta(Path(args.meta))
    ocr_json_path = Path(meta["json_path"])
    ocr = json.loads(ocr_json_path.read_text(encoding="utf-8"))
    rec_texts = ocr.get("rec_texts", [])
    rec_boxes = ocr.get("rec_boxes")  # 있으면 사용

    items_out: List[Dict[str, Any]] = []
    for i, raw in enumerate(rec_texts):
        # ✅ OCR 전처리도 동일 정책: 공백 제거된 정규화 텍스트를 사용/저장
        norm = normalize_menu_text(raw, remove_space=True)
        if len(norm) < args.min_len:
            continue
        if not is_menu_candidate(norm):
            continue

        m = matcher.match(norm, threshold=args.threshold, top_k=args.top_k)
        final_text = m["final_text"]
        # ✅ 매칭 이후 결과값도 공백 제거 버전 제공 (저장/키로 사용하기 좋음)
        final_text_compact = normalize_menu_text(final_text, remove_space=True) if final_text else ""
        items_out.append({
            "idx": i,
            "raw_text": raw,
            "normalized_text": norm,
            "final_text": m["final_text"],     # ✅ 최종 메뉴명
            "final_text_compact": final_text_compact,  # ✅ 공백 제거 버전
            "ingredient": m["ingredient"],     # ✅ 재료 리스트
            "match_score": m["match_score"],
            "match_type": m["match_type"],
            "matched_norm": m.get("matched_norm"),
            "debug": m.get("debug"),
            "box": (rec_boxes[i] if isinstance(rec_boxes, list) and i < len(rec_boxes) else None),
        })

    payload = {
        "meta": meta,
        "ocr_json_path": str(ocr_json_path),
        "index_dir": str(index_dir),
        "model": args.model,
        "threshold": args.threshold,
        "top_k": args.top_k,
        "items": items_out,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] saved: {out_path} (items={len(items_out)})")

if __name__ == "__main__":
    main()


'''
초기 빌딩 코드

python menu_rag_match.py ^
  --mode build ^
  --dict menuName_ingredients.json ^
  --index_dir rag_index ^
  --model sentence-transformers/paraphrase-multilingual-mpnet-base-v2
  
실행 코드 
python menu_rag_match.py ^
  --mode run ^
  --meta ocr_output/image_1_run_meta.json ^
  --index_dir rag_index ^
  --out ocr_output/image_1_menu_rag.json ^
  --threshold 0.90 ^
  --top_k 10
'''