from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =========================================================
# Version
# =========================================================
SCRIPT_VERSION = "3.0-lexical-vector-categoryfilter-jamo"
INDEX_META_VERSION = "chroma+lexical"

# =========================================================
# 1) Normalization (영어/숫자 제거 + 한글/공백 중심 + 공백옵션)
# =========================================================
_re_eng = re.compile(r"[A-Za-z]")
_re_num = re.compile(r"\d")
_re_keep_kor_space = re.compile(r"[^가-힣\s]")
_re_multi_space = re.compile(r"\s+")


def normalize_menu_text(text: str, remove_space: bool = True) -> str:
    if not text:
        return ""
    t = str(text).strip()
    t = _re_eng.sub("", t)
    t = _re_num.sub("", t)
    t = _re_keep_kor_space.sub(" ", t)
    t = _re_multi_space.sub(" ", t).strip()
    if remove_space:
        t = t.replace(" ", "")
    return t


# (추가) raw_text에서 한글 구간을 분리해 보존 (숫자/가격 섞임 대응)
_re_kor_phrase = re.compile(r"[가-힣]+(?:\s+[가-힣]+)*")


def extract_korean_phrases(raw_text: str) -> List[str]:
    """
    OCR 원문(raw_text)에서 '한글 구간'을 숫자/기호 기준으로 분리하여 반환합니다.
    예) '백 주 4,000복분재0,000' -> ['백 주', '복분재']
    """
    if not raw_text:
        return []
    s = str(raw_text)
    out: List[str] = []
    for mm in _re_kor_phrase.finditer(s):
        ph = _re_multi_space.sub(" ", mm.group(0)).strip()
        if ph:
            out.append(ph)
    return out


def is_menu_candidate(norm_text: str) -> bool:
    if len(norm_text.replace(" ", "")) < 2:
        return False
    return any("가" <= ch <= "힣" for ch in norm_text)


# =========================================================
# 1.5) Non-menu filter
# =========================================================
_NONMENU_PATTERNS = [
    r"주문서", r"직원", r"전달", r"착석", r"이용", r"안내", r"공지", r"주의", r"참고",
    r"원산지", r"알레르기", r"유발", r"표시", r"영양", r"칼로리",
    r"Self\s*-?\s*Bar", r"셀프\s*-?\s*바", r"셀프바",
    r"인원수", r"인분", r"선택", r"순한맛", r"중간맛", r"매운맛",
    r"사리메뉴", r"단품", r"식사\s*후", r"주문해\s*주세요",
    r"맛있습니다",
]


def is_nonmenu_text(raw_text: str) -> bool:
    if not raw_text:
        return True
    s = str(raw_text).strip()
    if len(s) >= 22:
        return True
    if s.startswith(("※", "*", "★", "■", "▶", "•")):
        return True
    for p in _NONMENU_PATTERNS:
        if re.search(p, s, flags=re.IGNORECASE):
            return True
    return False


# =========================================================
# 2) Hangul Jamo utilities
# =========================================================
CHOSUNG = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
JUNGSUNG = ["ㅏ","ㅐ","ㅑ","ㅒ","ㅓ","ㅔ","ㅕ","ㅖ","ㅗ","ㅘ","ㅙ","ㅚ","ㅛ","ㅜ","ㅝ","ㅞ","ㅟ","ㅠ","ㅡ","ㅢ","ㅣ"]
JONGSUNG = ["","ㄱ","ㄲ","ㄳ","ㄴ","ㄵ","ㄶ","ㄷ","ㄹ","ㄺ","ㄻ","ㄼ","ㄽ","ㄾ","ㄿ","ㅀ","ㅁ","ㅂ","ㅄ","ㅅ","ㅆ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]


def to_jamo(text: str) -> str:
    t = (text or "").replace(" ", "")
    out: List[str] = []
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
            out.append(ch)
    return "".join(out)


def ngrams(s: str, n: int = 2) -> List[str]:
    if len(s) < n:
        return [s] if s else []
    return [s[i:i + n] for i in range(len(s) - n + 1)]


def jamo_ngram_jaccard(a: str, b: str, n: int = 2) -> float:
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
# 3) Category (대분류)
# =========================================================
CATEGORIES = [
    "RICE","NOODLE","SOUP_STEW","MEAT","SEAFOOD","SNACK_STREET",
    "FRIED_CUTLET","DUMPLING","VEG_SALAD","DESSERT_BAKERY","BEVERAGE","OTHER"
]

_CAT_STRONG: Dict[str, List[str]] = {
    "NOODLE": ["냉면","막국수","쫄면","칼국수","수제비","우동","국수","소면","라면","짜장면","짬뽕","파스타","스파게티"],
    "SOUP_STEW": ["순대국","해장국","곰탕","설렁탕","삼계탕","감자탕","전골","찌개","탕","국","샤브"],
    "RICE": ["비빔밥","볶음밥","덮밥","김밥","오므라이스","카레","주먹밥"],
    "FRIED_CUTLET": ["돈까스","돈가스","카츠","가스"],
    "SNACK_STREET": ["떡볶이","순대","어묵","김말이","핫도그","튀김"],
    "DUMPLING": ["만두","교자","딤섬"],
    "MEAT": ["갈비","삼겹","목살","불고기","족발","보쌈","닭갈비","치킨"],
    "SEAFOOD": ["회","사시미","전복","조개","굴","새우","게","낙지","문어","오징어"],
    "DESSERT_BAKERY": ["빙수","아이스크림","케이크","쿠키","도넛","마카롱","떡","빵"],
    "BEVERAGE": ["아메리카노","라떼","커피","스무디","에이드","주스","차","티"],
    "VEG_SALAD": ["샐러드"],
}
_CAT_WEAK: Dict[str, List[str]] = {
    "RICE": ["정식","세트","특선","백반"],
    "SEAFOOD": ["해물","해산물"],
    "DESSERT_BAKERY": ["디저트"],
    "BEVERAGE": ["음료"],
}
_CAT_PRIORITY = [
    "FRIED_CUTLET","NOODLE","SOUP_STEW","SNACK_STREET",
    "RICE","MEAT","SEAFOOD","DUMPLING","VEG_SALAD","DESSERT_BAKERY","BEVERAGE"
]


@dataclass(frozen=True)
class CatResult:
    category_lv1: str
    confidence: float
    matched: List[str]


def predict_category(menu_text: str) -> CatResult:
    norm = normalize_menu_text(menu_text, remove_space=False)
    if not norm:
        return CatResult("OTHER", 0.0, [])

    scores: Dict[str, float] = {c: 0.0 for c in CATEGORIES}
    matched: Dict[str, List[str]] = {c: [] for c in CATEGORIES}

    for cat, kws in _CAT_STRONG.items():
        for kw in kws:
            if kw in norm:
                scores[cat] += 3.0
                matched[cat].append(kw)

    for cat, kws in _CAT_WEAK.items():
        for kw in kws:
            if kw in norm:
                scores[cat] += 1.0
                matched[cat].append(kw)

    best_cat = "OTHER"
    best_score = 0.0
    for cat in _CAT_PRIORITY:
        sc = scores.get(cat, 0.0)
        if sc > best_score:
            best_score = sc
            best_cat = cat

    if best_score <= 0.0:
        return CatResult("OTHER", 0.30, [])

    conf = 0.55 + (best_score * 0.10)
    conf = max(0.55, min(conf, 0.97))
    return CatResult(best_cat, conf, matched.get(best_cat, []))


# =========================================================
# 4) Lexical (rapidfuzz 우선)
# =========================================================
def lexical_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    try:
        from rapidfuzz import fuzz  # type: ignore
        return float(fuzz.ratio(a, b)) / 100.0
    except Exception:
        import difflib
        return difflib.SequenceMatcher(None, a, b).ratio()


def lexical_topn(query: str, choices: List[str], top_n: int) -> List[Tuple[int, float]]:
    if not query or not choices:
        return []
    try:
        from rapidfuzz import process, fuzz  # type: ignore
        res = process.extract(query, choices, scorer=fuzz.ratio, limit=top_n, score_cutoff=40)
        out = [(int(idx), float(score) / 100.0) for _, score, idx in res]
        out.sort(key=lambda x: x[1], reverse=True)
        return out
    except Exception:
        scored = [(i, lexical_ratio(query, c)) for i, c in enumerate(choices)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_n]


# =========================================================
# 5) Data structures
# =========================================================
@dataclass
class MenuEntry:
    id: str
    menu: str
    norm_menu: str
    ingredients_ko: Optional[List[str]]
    alg_tag: Optional[List[str]]
    category_lv1: str = "OTHER"
    category_conf: float = 0.0


# =========================================================
# 6) Chroma backend (Vector stage)
# =========================================================
import numpy as np
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
emb_model_name='snunlp/KR-SBERT-V40K-klueNLI-augSTS'
class ChromaVector:
    def __init__(self, persist_dir: Path, collection: str, model_name: str):
        import chromadb  # type: ignore
        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.col = self.client.get_or_create_collection(name=collection)

        # run 단계에서도 query embedding을 만들기 위해 동일 EF 구성
        self.ef = SentenceTransformerEmbeddingFunction(model_name=model_name)

    def query_within_ids(self, query_text: str, ids: List[str], top_k: int) -> Dict[str, float]:
        if not ids:
            return {}

        got = self.col.get(ids=ids, include=["embeddings"])
        got_ids = got.get("ids", None)
        embs = got.get("embeddings", None)

        if got_ids is None or embs is None:
            return {}

        # ids / embeddings 길이 체크 (numpy/list 모두 안전)
        try:
            n_ids = len(got_ids)
            n_emb = len(embs)
        except Exception:
            return {}

        if n_ids == 0 or n_emb == 0:
            return {}

        # --- 형태 정규화 ---
        # got_ids: list[str]
        got_ids_list = list(got_ids)

        # embs: (N, D) float32 ndarray 로 강제
        # 1) list-of-list or list-of-ndarray -> ndarray
        embs_arr = np.asarray(embs, dtype=np.float32)

        # 2) 만약 (D,) 단일 벡터가 들어오면 (1, D)로
        if embs_arr.ndim == 1:
            embs_arr = embs_arr.reshape(1, -1)

        # 3) ids와 embeddings 개수 mismatch 방지
        n = min(len(got_ids_list), embs_arr.shape[0])
        got_ids_list = got_ids_list[:n]
        embs_arr = embs_arr[:n]

        # query embedding
        q = np.asarray(self.ef([query_text])[0], dtype=np.float32)
        qn = float(np.linalg.norm(q) + 1e-9)

        sims: Dict[str, float] = {}
        # cosine sim
        for _id, v in zip(got_ids_list, embs_arr):
            vn = float(np.linalg.norm(v) + 1e-9)
            sims[str(_id)] = float(np.dot(q, v) / (qn * vn))

        return dict(sorted(sims.items(), key=lambda x: x[1], reverse=True)[:top_k])


# =========================================================
# 7) Matcher (3-stage: lexical → vector → category filter) + jamo gate
# =========================================================
@dataclass
class MatchConfig:
    lex_top_n: int = 200
    vec_top_n: int = 50

    cat_filter_min_conf: float = 0.85
    cat_filter_min_keep: int = 2

    w_vec: float = 0.65
    w_lex: float = 0.25
    w_jamo: float = 0.10

    jamo_filter_min: float = 0.22

    threshold: float = 0.90
    min_cos: float = 0.62
    min_jacc: float = 0.55
    min_margin: float = 0.08


class MenuRAGMatcher:
    def __init__(self, cfg: Optional[MatchConfig] = None):
        self.cfg = cfg or MatchConfig()
        self.entries: List[MenuEntry] = []
        self.id_to_entry: Dict[str, MenuEntry] = {}
        self.norm_to_id: Dict[str, str] = {}
        self._choices_norm: List[str] = []
        self._ids: List[str] = []

    def build_from_catalog_jsonl(self, catalog_jsonl: Path):
        self.entries = []
        self.id_to_entry = {}
        self.norm_to_id = {}
        self._choices_norm = []
        self._ids = []

        with catalog_jsonl.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                _id = str(obj.get("id") or "")
                menu = str(obj.get("menu") or "").strip()
                if not _id or not menu:
                    continue

                norm = str(obj.get("menu_norm") or normalize_menu_text(menu, remove_space=True))
                if not norm:
                    continue

                entry = MenuEntry(
                    id=_id,
                    menu=menu,
                    norm_menu=norm,
                    ingredients_ko=obj.get("ingredients_ko"),
                    alg_tag=obj.get("ALG_TAG"),
                    category_lv1=str(obj.get("category_lv1") or "OTHER"),
                    category_conf=float(obj.get("category_conf") or 0.0),
                )

                if norm not in self.norm_to_id:
                    self.entries.append(entry)
                    self.id_to_entry[_id] = entry
                    self.norm_to_id[norm] = _id
                    self._choices_norm.append(norm)
                    self._ids.append(_id)

    def save_lexical_index(self, out_dir: Path):
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": SCRIPT_VERSION,
            "meta_version": INDEX_META_VERSION,
            "count": len(self.entries),
            "ids": self._ids,
            "menus_norm": self._choices_norm,
            "entries": [
                {
                    "id": e.id,
                    "menu": e.menu,
                    "norm_menu": e.norm_menu,
                    "ingredients_ko": e.ingredients_ko,
                    "ALG_TAG": e.alg_tag,
                    "category_lv1": e.category_lv1,
                    "category_conf": e.category_conf,
                }
                for e in self.entries
            ],
        }
        (out_dir / "lexical_meta.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_lexical_index(self, index_dir: Path):
        payload = json.loads((index_dir / "lexical_meta.json").read_text(encoding="utf-8"))
        self.entries = []
        self.id_to_entry = {}
        self.norm_to_id = {}
        self._choices_norm = payload.get("menus_norm", [])
        self._ids = payload.get("ids", [])

        for obj in payload.get("entries", []):
            e = MenuEntry(
                id=obj["id"],
                menu=obj["menu"],
                norm_menu=obj["norm_menu"],
                ingredients_ko=obj.get("ingredients_ko"),
                alg_tag=obj.get("ALG_TAG"),
                category_lv1=obj.get("category_lv1", "OTHER"),
                category_conf=float(obj.get("category_conf", 0.0)),
            )
            self.entries.append(e)
            self.id_to_entry[e.id] = e
            if e.norm_menu not in self.norm_to_id:
                self.norm_to_id[e.norm_menu] = e.id

        if len(self._ids) != len(self._choices_norm):
            raise ValueError("lexical index corrupted: ids and menus_norm length mismatch")

    @staticmethod
    def adaptive_threshold(norm_query: str, base: float) -> float:
        n = len(norm_query.replace(" ", ""))
        if n <= 2:
            return max(base, 0.985)
        if n == 3:
            return max(base, 0.96)
        return base

    @staticmethod
    def margin_gate(best: float, second: Optional[float], min_margin: float) -> bool:
        if second is None:
            return True
        return (best - second) >= min_margin

    def match(self, norm_query: str, chroma: ChromaVector, top_k: int) -> Dict[str, Any]:
        if len(norm_query.replace(" ", "")) < 3:
            return {"final_text": None, "ingredient": None, "ALG_TAG": None, "match_score": 0.0, "match_type": "too_short", "matched_norm": None}

        if norm_query in self.norm_to_id:
            _id = self.norm_to_id[norm_query]
            e = self.id_to_entry.get(_id)
            if e:
                return {"final_text": e.menu, "ingredient": e.ingredients_ko, "ALG_TAG": e.alg_tag, "match_score": 1.0, "match_type": "exact", "matched_norm": e.norm_menu}

        qcat = predict_category(norm_query)

        # Stage 1) lexical
        lex_hits = lexical_topn(norm_query, self._choices_norm, top_n=self.cfg.lex_top_n)
        if not lex_hits:
            return {"final_text": None, "ingredient": None, "ALG_TAG": None, "match_score": 0.0, "match_type": "none", "matched_norm": None}

        cand_ids = [self._ids[idx] for idx, _ in lex_hits]
        lex_map = {self._ids[idx]: float(sc) for idx, sc in lex_hits}

        # Stage 2) vector rerank within ids
        vec_map = chroma.query_within_ids(norm_query, cand_ids, top_k=self.cfg.vec_top_n)
        if not vec_map:
            best_id = cand_ids[0]
            e = self.id_to_entry.get(best_id)
            return {
                "final_text": None, "ingredient": None, "ALG_TAG": None,
                "match_score": float(lex_map.get(best_id, 0.0)),
                "match_type": "vector_failed",
                "matched_norm": (e.norm_menu if e else None),
                "debug": {"pred_category": qcat.category_lv1, "pred_category_conf": qcat.confidence},
            }

        vec_sorted = sorted(vec_map.items(), key=lambda x: x[1], reverse=True)

        # DEBUG: id_to_entry 매핑 확인
        sample_ids = [vid for vid, _ in vec_sorted[:5]]
        missing = [vid for vid in sample_ids if vid not in self.id_to_entry]
        print("[DEBUG] vec_sorted_top_ids:", sample_ids)
        print("[DEBUG] missing_in_id_to_entry:", missing)
        print("[DEBUG] id_to_entry_size:", len(self.id_to_entry))
        print("[DEBUG] norm_to_id_size:", len(self.norm_to_id))
        print("[DEBUG] choices_norm_size:", len(self._choices_norm))
        print("[DEBUG] ids_size:", len(self._ids))

        # Stage 3) category filter (고확신일 때만 강제, 부족하면 fallback)
        filtered_ids: List[str] = [vid for vid, _ in vec_sorted]
        cat_filter_applied = False
        if qcat.confidence >= self.cfg.cat_filter_min_conf:
            same_cat = []
            for vid, _ in vec_sorted:
                e = self.id_to_entry.get(vid)
                if e and e.category_lv1 == qcat.category_lv1:
                    same_cat.append(vid)
            if len(same_cat) >= self.cfg.cat_filter_min_keep:
                filtered_ids = same_cat
                cat_filter_applied = True

        # Final scoring + jamo gate
        qj = to_jamo(norm_query)
        rescored: List[Tuple[str, float, float, float, float]] = []
        for vid in filtered_ids[: max(top_k * 5, top_k)]:
            e = self.id_to_entry.get(vid)
            if not e:
                continue
            vec_sc = float(vec_map.get(vid, 0.0))
            lex_sc = float(lex_map.get(vid, 0.0))
            jacc = float(jamo_ngram_jaccard(qj, to_jamo(e.norm_menu), n=2))
            if jacc < self.cfg.jamo_filter_min:
                continue
            final = self.cfg.w_vec * vec_sc + self.cfg.w_lex * lex_sc + self.cfg.w_jamo * jacc
            rescored.append((vid, float(final), vec_sc, lex_sc, jacc))

        rescored.sort(key=lambda x: x[1], reverse=True)
        if not rescored:
            return {
                "final_text": None, "ingredient": None, "ALG_TAG": None,
                "match_score": float(vec_sorted[0][1]),
                "match_type": "no_candidate_after_scoring",
                "matched_norm": None,
                "debug": {"cat_filter_applied": cat_filter_applied, "pred_category": qcat.category_lv1, "pred_category_conf": qcat.confidence},
            }

        best = rescored[0]
        second = rescored[1] if len(rescored) > 1 else None

        best_id, best_final, best_vec, best_lex, best_jacc = best
        th = self.adaptive_threshold(norm_query, self.cfg.threshold)
        margin = (best_final - second[1]) if second else 1.0
        margin_ok = self.margin_gate(best_final, second[1] if second else None, self.cfg.min_margin)

        pass_gate = (
            (best_final >= th)
            and margin_ok
            and (best_vec >= self.cfg.min_cos)
            and (best_jacc >= self.cfg.min_jacc)
            and (margin >= self.cfg.min_margin)
        )

        e = self.id_to_entry.get(best_id)
        if pass_gate and e:
            return {
                "final_text": e.menu,
                "ingredient": e.ingredients_ko,
                "ALG_TAG": e.alg_tag,
                "match_score": float(best_final),
                "match_type": "lex_vec_catfilter_jamo",
                "matched_norm": e.norm_menu,
                "debug": {
                    "vec": float(best_vec), "lex": float(best_lex), "jamo_jaccard": float(best_jacc),
                    "margin": float(margin), "th": float(th),
                    "cat_filter_applied": bool(cat_filter_applied),
                    "pred_category": qcat.category_lv1, "pred_category_conf": float(qcat.confidence),
                    "matched_category": e.category_lv1,
                },
            }

        return {
            "final_text": None, "ingredient": None, "ALG_TAG": None,
            "match_score": float(best_final),
            "match_type": "rejected_by_gate",
            "matched_norm": (e.norm_menu if e else None),
            "debug": {
                "vec": float(best_vec), "lex": float(best_lex), "jamo_jaccard": float(best_jacc),
                "margin": float(margin), "th": float(th),
                "cat_filter_applied": bool(cat_filter_applied),
                "pred_category": qcat.category_lv1, "pred_category_conf": float(qcat.confidence),
                "matched_category": (e.category_lv1 if e else None),
            },
        }


# =========================================================
# 8) OCR meta loader
# =========================================================
def load_meta(meta_path: Path) -> Dict[str, Any]:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if "json_path" not in meta:
        raise ValueError("meta json must include 'json_path'.")
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["build", "run"], required=True)

    # build
    ap.add_argument("--catalog", help="menu_catalog.jsonl path (build mode)")

    # shared
    ap.add_argument("--index_dir", required=True, help="lexical index dir (will create lexical_meta.json)")

    # chroma (run)
    ap.add_argument("--chroma_dir", default="", help="Chroma persist dir (e.g., AI/index/vector/chroma)")
    ap.add_argument("--collection", default="menu_catalog", help="Chroma collection name")

    # run io
    ap.add_argument("--meta", help="*_run_meta.json path (run mode)")
    ap.add_argument("--out", help="output json path (run mode)")

    # match config
    ap.add_argument("--top_k", type=int, default=10)
    ap.add_argument("--lex_top_n", type=int, default=200)
    ap.add_argument("--vec_top_n", type=int, default=50)
    ap.add_argument("--cat_filter_min_conf", type=float, default=0.85)
    ap.add_argument("--cat_filter_min_keep", type=int, default=2)

    ap.add_argument("--w_vec", type=float, default=0.65)
    ap.add_argument("--w_lex", type=float, default=0.25)
    ap.add_argument("--w_jamo", type=float, default=0.05)

    ap.add_argument("--jamo_filter_min", type=float, default=0.05)

    ap.add_argument("--threshold", type=float, default=0.90)
    ap.add_argument("--min_cos", type=float, default=0.57)
    ap.add_argument("--min_jacc", type=float, default=0.25)
    ap.add_argument("--min_margin", type=float, default=0.08)

    # run filters
    ap.add_argument("--drop_nonmenu", action="store_true")
    ap.add_argument("--drop_nonmenu_regex", default="")
    ap.add_argument("--drop_unmatched", action="store_true")
    ap.add_argument("--min_len", type=int, default=2)

    args = ap.parse_args()

    cfg = MatchConfig(
        lex_top_n=int(args.lex_top_n),
        vec_top_n=int(args.vec_top_n),
        cat_filter_min_conf=float(args.cat_filter_min_conf),
        cat_filter_min_keep=int(args.cat_filter_min_keep),
        w_vec=float(args.w_vec),
        w_lex=float(args.w_lex),
        w_jamo=float(args.w_jamo),
        jamo_filter_min=float(args.jamo_filter_min),
        threshold=float(args.threshold),
        min_cos=float(args.min_cos),
        min_jacc=float(args.min_jacc),
        min_margin=float(args.min_margin),
    )

    index_dir = Path(args.index_dir)

    if args.mode == "build":
        if not args.catalog:
            raise ValueError("--catalog is required for build mode (menu_catalog.jsonl)")
        matcher = MenuRAGMatcher(cfg=cfg)
        matcher.build_from_catalog_jsonl(Path(args.catalog))
        matcher.save_lexical_index(index_dir)
        print(f"[OK] built lexical index: {index_dir} (count={len(matcher.entries)})")
        return

    # run
    if not args.meta or not args.out:
        raise ValueError("--meta and --out are required for run mode")
    if not args.chroma_dir:
        raise ValueError("--chroma_dir is required for run mode (e.g., AI/index/vector/chroma)")

    matcher = MenuRAGMatcher(cfg=cfg)
    matcher.load_lexical_index(index_dir)
    chroma = ChromaVector(persist_dir=Path(args.chroma_dir), collection=args.collection,model_name=emb_model_name)

    meta = load_meta(Path(args.meta))
    ocr_json_path = Path(meta["json_path"])
    ocr = json.loads(ocr_json_path.read_text(encoding="utf-8"))
    rec_texts = ocr.get("rec_texts", [])
    rec_boxes = ocr.get("rec_boxes")

    items_out: List[Dict[str, Any]] = []
    extra_re = re.compile(args.drop_nonmenu_regex) if args.drop_nonmenu_regex else None

    for i, raw in enumerate(rec_texts):
        if args.drop_nonmenu:
            if is_nonmenu_text(raw) or (extra_re and extra_re.search(str(raw))):
                if not args.drop_unmatched:
                    norm_tmp = normalize_menu_text(raw, remove_space=True)
                    items_out.append({
                        "idx": i, "raw_text": raw, "normalized_text": norm_tmp,
                        "raw_kor_phrases": extract_korean_phrases(raw),
                        "raw_kor_phrases_compact": [normalize_menu_text(p, remove_space=True) for p in extract_korean_phrases(raw)],
                        "final_text": None, "final_text_compact": None,
                        "ingredient": None, "ALG_TAG": None,
                        "match_score": 0.0, "match_type": "dropped_nonmenu",
                        "matched_norm": None, "debug": None,
                        "box": (rec_boxes[i] if isinstance(rec_boxes, list) and i < len(rec_boxes) else None),
                    })
                continue

        # --- phrase split (Korean-only) ---
        raw_kor_phrases = extract_korean_phrases(raw)
        raw_kor_phrases_compact = [normalize_menu_text(p, remove_space=True) for p in raw_kor_phrases]

        # ✅ If multiple phrases exist in one raw line, evaluate each phrase independently via RAG
        if isinstance(raw_kor_phrases_compact, list) and len(raw_kor_phrases_compact) >= 2:
            for sub_idx, norm in enumerate(raw_kor_phrases_compact):
                if not norm or len(norm) < args.min_len:
                    continue
                if not is_menu_candidate(norm):
                    continue

                m = matcher.match(norm_query=norm, chroma=chroma, top_k=int(args.top_k))
                final_text = m.get("final_text")
                final_text_compact = normalize_menu_text(final_text, remove_space=True) if isinstance(final_text, str) else None

                if args.drop_unmatched and final_text is None:
                    continue

                items_out.append({
                    "idx": i,
                    "sub_idx": sub_idx,            # ✅ per-phrase result index within the same raw line
                    "raw_text": raw,
                    "raw_part": (raw_kor_phrases[sub_idx] if sub_idx < len(raw_kor_phrases) else None),
                    "normalized_text": norm,       # ✅ evaluate each phrase (NOT concatenated text)
                    "raw_kor_phrases": raw_kor_phrases,
                    "raw_kor_phrases_compact": raw_kor_phrases_compact,
                    "final_text": final_text,
                    "final_text_compact": final_text_compact,
                    "ingredient": m.get("ingredient"),
                    "ALG_TAG": m.get("ALG_TAG"),
                    "match_score": m.get("match_score", 0.0),
                    "match_type": m.get("match_type"),
                    "matched_norm": m.get("matched_norm"),
                    "debug": m.get("debug"),
                    "box": (rec_boxes[i] if isinstance(rec_boxes, list) and i < len(rec_boxes) else None),
                })
            continue  # ✅ already evaluated per-phrase, skip concatenated evaluation

        # fallback: single-string evaluation (previous behavior)
        norm = normalize_menu_text(raw, remove_space=True)
        if len(norm) < args.min_len:
            continue
        if not is_menu_candidate(norm):
            continue

        m = matcher.match(norm_query=norm, chroma=chroma, top_k=int(args.top_k))
        final_text = m.get("final_text")
        final_text_compact = normalize_menu_text(final_text, remove_space=True) if isinstance(final_text, str) else None

        if args.drop_unmatched and final_text is None:
            continue

        items_out.append({
            "idx": i,
            "raw_text": raw,
            "normalized_text": norm,
            "raw_kor_phrases": raw_kor_phrases,
            "raw_kor_phrases_compact": raw_kor_phrases_compact,
            "final_text": final_text,
            "final_text_compact": final_text_compact,
            "ingredient": m.get("ingredient"),
            "ALG_TAG": m.get("ALG_TAG"),
            "match_score": m.get("match_score", 0.0),
            "match_type": m.get("match_type"),
            "matched_norm": m.get("matched_norm"),
            "debug": m.get("debug"),
            "box": (rec_boxes[i] if isinstance(rec_boxes, list) and i < len(rec_boxes) else None),
        })

    payload = {
        "meta": meta,
        "ocr_json_path": str(ocr_json_path),
        "index_dir": str(index_dir),
        "chroma_dir": str(Path(args.chroma_dir)),
        "collection": args.collection,
        "script_version": SCRIPT_VERSION,
        "match_config": cfg.__dict__,
        "items": items_out,
        "drop_nonmenu": bool(args.drop_nonmenu),
        "drop_unmatched": bool(args.drop_unmatched),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] saved: {out_path} (items={len(items_out)})")


if __name__ == "__main__":
    main()


'''
빌드:
python AI/menu_rag_match_advanced.py ^
  --mode build ^
  --catalog AI/data/menu_catalog.jsonl ^
  --index_dir AI/index/lexical
실행:
python AI/menu_rag_match_advanced_split_rag_each.py --mode run ^
  --meta AI/ocr_output/image1/image1_run_meta.json ^
  --index_dir AI/index/lexical ^
  --chroma_dir AI/index/vector/chroma ^
  --collection menu_catalog ^
  --out AI/ocr_output/image1/image1_menu_rag.json ^
  --top_k 10 --lex_top_n 700 --vec_top_n 200 ^
  --cat_filter_min_conf 0.90 --cat_filter_min_keep 2 ^
  --threshold 0.74 --min_cos 0.52 --min_jacc 0.48 --min_margin 0.03 ^
  --w_vec 0.68 --w_lex 0.22 --w_jamo 0.10 ^
  --jamo_filter_min 0.22 ^
  --drop_nonmenu

사용법:
jamo_filter_min 0.22: 완전 동떨어진 후보 컷(엉뚱매칭 방지)

min_jacc 0.48: 자모 유사도가 너무 낮으면 최종 합격 불가(오타 보정용)

threshold 0.74: 지금보다 살짝 올려 “아무거나 매칭”을 줄임

빠른 튜닝 규칙(운영하면서 바로 조절)

오매칭이 많다 → threshold↑, min_margin↑, jamo_filter_min↑, min_jacc↑

매칭이 너무 안 된다 → threshold↓, min_cos↓, min_jacc↓, lex_top_n↑, vec_top_n↑

짧은 메뉴(2~3글자)에서 오매칭 → min_margin을 0.04~0.06으로 올리는 게 효과 큼
'''