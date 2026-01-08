# AI/menu_matcher.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from AI.data.category_rules import normalize_menu, predict_category

# ---------------------------
# Lexical scorer (rapidfuzz preferred)
# ---------------------------

def _lex_score(a: str, b: str) -> float:
    """
    returns 0.0~1.0
    """
    if not a or not b:
        return 0.0
    try:
        from rapidfuzz import fuzz
        return float(fuzz.ratio(a, b)) / 100.0
    except Exception:
        # fallback: difflib
        import difflib
        return difflib.SequenceMatcher(None, a, b).ratio()

# ---------------------------
# Vector backends
# ---------------------------

class VectorBackend:
    def rerank(self, query_text: str, candidate_ids: List[str], top_k: int) -> Dict[str, float]:
        """
        return dict[id] = vector_score (0~1)
        """
        raise NotImplementedError

class ChromaBackend(VectorBackend):
    def __init__(self, persist_dir: Path, collection: str, model_name: Optional[str] = None):
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        self.client = chromadb.PersistentClient(path=str(persist_dir))
        ef = None
        if model_name:
            ef = SentenceTransformerEmbeddingFunction(model_name=model_name)
        self.col = self.client.get_or_create_collection(name=collection, embedding_function=ef)

    def rerank(self, query_text: str, candidate_ids: List[str], top_k: int) -> Dict[str, float]:
        # Chroma는 where/ids 필터가 가능하므로 candidates만 대상으로 검색
        res = self.col.query(
            query_texts=[query_text],
            n_results=min(top_k, max(1, len(candidate_ids))),
            where=None,
            include=["distances", "ids"],
            # ids 제한
            ids=candidate_ids,
        )
        ids = res["ids"][0]
        dists = res["distances"][0]  # cosine distance (0 is best) in many setups
        out: Dict[str, float] = {}
        for _id, dist in zip(ids, dists):
            # distance -> similarity(0~1 근사)
            sim = max(0.0, 1.0 - float(dist))
            out[_id] = sim
        return out

class NpyEmbeddingBackend(VectorBackend):
    """
    emb.npy + meta.jsonl 기반. candidates에 대해서만 cosine 계산.
    """
    def __init__(self, emb_path: Path, meta_path: Path, st_model: str):
        import numpy as np
        self.emb = np.load(str(emb_path))
        self.id_to_idx: Dict[str, int] = {}
        self.st_model = st_model

        with meta_path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                obj = json.loads(line)
                self.id_to_idx[obj["id"]] = i

        try:
            from sentence_transformers import SentenceTransformer
        except Exception as e:
            raise RuntimeError("npy backend는 sentence-transformers가 필요합니다.") from e
        self.model = SentenceTransformer(st_model)

    def rerank(self, query_text: str, candidate_ids: List[str], top_k: int) -> Dict[str, float]:
        import numpy as np

        q = self.model.encode([query_text], normalize_embeddings=True)[0]  # (d,)
        q = q.astype("float32")

        sims: List[Tuple[str, float]] = []
        for _id in candidate_ids:
            idx = self.id_to_idx.get(_id)
            if idx is None:
                continue
            v = self.emb[idx].astype("float32")
            sim = float(np.dot(q, v))
            sims.append((_id, sim))

        sims.sort(key=lambda x: x[1], reverse=True)
        sims = sims[:top_k]
        return {i: max(0.0, min(1.0, s)) for i, s in sims}

# ---------------------------
# Matcher
# ---------------------------

@dataclass
class MatchConfig:
    lexical_top_n: int = 200
    rerank_top_k: int = 20
    # final score = w_vec*vec + w_lex*lex + w_cat*cat_boost
    w_vec: float = 0.55
    w_lex: float = 0.40
    w_cat: float = 0.05
    # category boost applies only when predicted category confidence >= cat_min_conf_for_boost
    cat_min_conf_for_boost: float = 0.75

class MenuMatcher:
    def __init__(
        self,
        lexical_index_path: Path,
        catalog_path: Path,
        vector_backend: Optional[VectorBackend] = None,
        config: Optional[MatchConfig] = None,
    ):
        self.cfg = config or MatchConfig()
        self.vector = vector_backend

        # load lexical index
        lex = json.loads(lexical_index_path.read_text(encoding="utf-8"))
        self.ids: List[str] = lex["ids"]
        self.menus_norm: List[str] = lex["menus_norm"]
        self.menus_raw: List[str] = lex["menus_raw"]
        self.cats: List[str] = lex["category_lv1"]
        self.count = int(lex["count"])

        # load catalog for final payload
        self.catalog: Dict[str, Dict[str, Any]] = {}
        with catalog_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    self.catalog[obj["id"]] = obj

    def _lex_candidates(self, query_norm: str) -> List[Tuple[str, float]]:
        scored: List[Tuple[str, float]] = []
        for _id, mn in zip(self.ids, self.menus_norm):
            s = _lex_score(query_norm, mn)
            if s > 0:
                scored.append((_id, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[: self.cfg.lexical_top_n]

    def match(self, query_menu: str) -> Dict[str, Any]:
        q_norm = normalize_menu(query_menu)
        q_cat = predict_category(query_menu)

        # 1) lexical 후보
        cands = self._lex_candidates(q_norm)
        cand_ids = [cid for cid, _ in cands]
        lex_map = {cid: sc for cid, sc in cands}

        # 2) vector rerank (optional)
        vec_map: Dict[str, float] = {}
        if self.vector and cand_ids:
            vec_map = self.vector.rerank(query_text=query_menu, candidate_ids=cand_ids, top_k=self.cfg.rerank_top_k)

        # 3) final score
        results: List[Dict[str, Any]] = []
        for cid in cand_ids:
            lex_sc = lex_map.get(cid, 0.0)
            vec_sc = vec_map.get(cid, 0.0) if vec_map else 0.0

            cat_boost = 0.0
            if q_cat.confidence >= self.cfg.cat_min_conf_for_boost:
                # 같은 카테고리면 +1, 아니면 0
                doc = self.catalog.get(cid, {})
                if doc.get("category_lv1") == q_cat.category_lv1:
                    cat_boost = 1.0

            final = (self.cfg.w_vec * vec_sc) + (self.cfg.w_lex * lex_sc) + (self.cfg.w_cat * cat_boost)

            doc = self.catalog.get(cid)
            if not doc:
                continue

            results.append({
                "id": cid,
                "final_score": round(float(final), 6),
                "lex_score": round(float(lex_sc), 6),
                "vec_score": round(float(vec_sc), 6),
                "category_boost": cat_boost,
                "menu": doc["menu"],
                "category_lv1": doc.get("category_lv1", "OTHER"),
                "ingredients_ko": doc.get("ingredients_ko", []),
                "ALG_TAG": doc.get("ALG_TAG", []),
            })

        results.sort(key=lambda x: x["final_score"], reverse=True)

        return {
            "query": {
                "raw": query_menu,
                "norm": q_norm,
                "pred_category_lv1": q_cat.category_lv1,
                "pred_category_conf": round(float(q_cat.confidence), 4),
                "pred_category_matched": q_cat.matched,
            },
            "config": self.cfg.__dict__,
            "results": results[: self.cfg.rerank_top_k],
        }
