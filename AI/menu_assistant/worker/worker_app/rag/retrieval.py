"""
menu_assistant.worker.worker_app.rag.retrieval

역할:
- Step3 normalize 결과(variants 등)를 입력으로 받아
- ChromaDB(menu_index)에서 표준 메뉴를 검색/매칭하여
- best match + 후보 리스트 + 상태(CONFIRMED/AMBIGUOUS/NOT_FOUND)를 반환한다.

주의:
- 여기서는 "검색"까지만 담당한다.
- 사용자 알러지 매칭(DANGER/CAUTION/SAFE), LLM 호출은 다른 모듈(risk.py 등)로 분리한다.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


# ==============================
# CONFIG
# ==============================
COLLECTION_NAME = "menu_index"
DEFAULT_TOP_K = 5
DEFAULT_SCORE_THRESHOLD = 0.85
DEFAULT_AMBIGUOUS_GAP = 0.03  # best - second가 이 값보다 작으면 애매(AMBIGUOUS)로 간주

# Chroma persist dir (프로젝트 상대경로)
BASE_DIR = Path(__file__).resolve().parents[3]  # menu_assistant/
DEFAULT_CHROMA_DIR = BASE_DIR / "data" / "chroma"

# Embedding model (index 빌드와 동일해야 함)
DEFAULT_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# 간단한 정규화(검색 품질 안정화용)
_WS_RE = re.compile(r"\s+")
_SLASH_SPLIT_RE = re.compile(r"\s*/\s*")


# ==============================
# DATA STRUCTURES
# ==============================
@dataclass
class Candidate:
    id: str
    score: float  # 내부적으로는 similarity로 통일 (1.0에 가까울수록 좋음)
    menu: str
    ingredients_ko: List[str]
    alg_tags: List[str]
    source: str = ""


@dataclass
class RetrievalResult:
    status: str  # CONFIRMED | AMBIGUOUS | NOT_FOUND
    best_match: Optional[Candidate]
    candidates: List[Candidate]
    used_query: Optional[str] = None  # best를 만든 query(variant)
    debug: Optional[Dict[str, Any]] = None


# ==============================
# UTILS
# ==============================
def _norm_text(s: str) -> str:
    s = (s or "").strip()
    s = _WS_RE.sub(" ", s)
    return s


def _split_csv(s: str) -> List[str]:
    """metadata에 문자열로 저장된 'a, b, c' 형태를 list로 복원."""
    if not s:
        return []
    parts = [p.strip() for p in s.split(",")]
    return [p for p in parts if p]


def _parse_metadata(md: Dict[str, Any]) -> Tuple[str, List[str], List[str], str]:
    """
    build_chroma_index.py에서 metadata를 문자열로 저장했으므로,
    여기서 list로 복원한다.
    """
    menu = _norm_text(str(md.get("menu", "")))
    ingredients = _split_csv(str(md.get("ingredients_ko", "")))
    alg_tags = _split_csv(str(md.get("alg_tags", "")))
    source = _norm_text(str(md.get("source", "")))
    return menu, ingredients, alg_tags, source


def _safe_get_first(lst: Any, default=None):
    if isinstance(lst, list) and lst:
        return lst[0]
    return default


def _to_similarity(distance: Optional[float]) -> float:
    """
    Chroma의 거리(distance)는 embedding function/버전/설정에 따라
    의미가 다를 수 있으나, 일반적으로 작은 값이 더 유사함.
    여기서는 일관된 비교를 위해 "유사도(similarity)"로 변환한다.

    - distance가 None이면 0으로 처리
    - cosine distance 가정 시 similarity ≈ 1 - distance
    """
    if distance is None:
        return 0.0
    try:
        d = float(distance)
    except Exception:
        return 0.0
    return 1.0 - d


def _expand_variants(variants: List[str]) -> List[str]:
    """
    Step3에서 variants를 주지만,
    슬래시 메뉴(물냉면/비빔냉면)처럼 한 문자열에 복수 메뉴가 있는 경우를 대비해 확장.
    """
    out: List[str] = []
    for v in variants or []:
        v = _norm_text(v)
        if not v:
            continue
        out.append(v)
        # "A/B" 형태면 분리도 추가
        if "/" in v:
            for part in _SLASH_SPLIT_RE.split(v):
                part = _norm_text(part)
                if part and part not in out:
                    out.append(part)
    # 중복 제거(순서 유지)
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    return uniq


# ==============================
# CHROMA CLIENT (LAZY SINGLETON)
# ==============================
class ChromaMenuRetriever:
    """
    런타임에서 ChromaDB(menu_index)를 로드해 검색하는 클래스.
    """

    def __init__(
        self,
        chroma_dir: Path = DEFAULT_CHROMA_DIR,
        collection_name: str = COLLECTION_NAME,
        embed_model: str = DEFAULT_EMBED_MODEL,
    ):
        self.chroma_dir = Path(chroma_dir)
        self.collection_name = collection_name
        self.embed_model = embed_model

        self._client = None
        self._collection = None

    def _init(self):
        if self._collection is not None:
            return

        self.chroma_dir.mkdir(parents=True, exist_ok=True)

        emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.embed_model
        )

        # Persist 로드: PersistentClient 우선
        if hasattr(chromadb, "PersistentClient"):
            self._client = chromadb.PersistentClient(path=str(self.chroma_dir))
        else:
            self._client = chromadb.Client(
                Settings(
                    persist_directory=str(self.chroma_dir),
                    anonymized_telemetry=False,
                )
            )

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=emb_fn,
        )

        # ✅ 여기서만 count 체크 (collection 생성 이후)
        print(f"[RAG] chroma_dir = {self.chroma_dir}")
        print(f"[RAG] collection = {self.collection_name}")

        try:
            cnt = self._collection.count()
        except Exception:
            got = self._collection.get(limit=1, include=["metadatas"])
            cnt = len(got.get("ids", []))

        print(f"[RAG] collection.count() = {cnt}")
        if cnt == 0:
            raise RuntimeError(
                f"[RAG] collection is empty. chroma_dir={self.chroma_dir} collection={self.collection_name}"
            )

    @property
    def collection(self):
        self._init()
        return self._collection


    def retrieve_menu(
        self,
        variants: List[str],
        top_k: int = DEFAULT_TOP_K,
        score_threshold: float = DEFAULT_SCORE_THRESHOLD,
        ambiguous_gap: float = DEFAULT_AMBIGUOUS_GAP,
        include_debug: bool = False,
    ) -> RetrievalResult:
        """
        variants(질의 후보들)를 순회하며 가장 높은 score의 결과를 선택한다.

        score는 내부적으로 similarity(1.0에 가까울수록 유사)로 통일한다.
        - CONFIRMED: best.score >= threshold AND (best - second) >= gap
        - AMBIGUOUS: best.score >= threshold BUT (best - second) < gap
        - NOT_FOUND: best.score < threshold or 후보 없음
        """
        variants = _expand_variants([_norm_text(v) for v in (variants or [])])
        variants = [v for v in variants if v]

        if not variants:
            return RetrievalResult(
                status="NOT_FOUND",
                best_match=None,
                candidates=[],
                used_query=None,
                debug={"reason": "empty_variants"} if include_debug else None,
            )

        best_overall: Optional[Candidate] = None
        best_query: Optional[str] = None
        best_candidates: List[Candidate] = []
        debug_info: Dict[str, Any] = {"per_query": []} if include_debug else {}

        for q in variants:
            res = self._query_once(q, top_k=top_k)
            cands = res["candidates"]
            if include_debug:
                debug_info["per_query"].append(
                    {
                        "query": q,
                        "top_scores": [c.score for c in cands[: min(5, len(cands))]],
                        "top_menus": [c.menu for c in cands[: min(5, len(cands))]],
                    }
                )

            if not cands:
                continue

            # query별 best
            if best_overall is None or cands[0].score > best_overall.score:
                best_overall = cands[0]
                best_query = q
                best_candidates = cands

        if best_overall is None:
            return RetrievalResult(
                status="NOT_FOUND",
                best_match=None,
                candidates=[],
                used_query=None,
                debug=debug_info if include_debug else None,
            )

        # 상태 결정
        if best_overall.score < score_threshold:
            status = "NOT_FOUND"
        else:
            second_score = best_candidates[1].score if len(best_candidates) >= 2 else 0.0
            gap = best_overall.score - second_score
            status = "CONFIRMED" if gap >= ambiguous_gap else "AMBIGUOUS"
            if include_debug:
                debug_info["gap"] = gap
                debug_info["second_score"] = second_score

        return RetrievalResult(
            status=status,
            best_match=best_overall if status != "NOT_FOUND" else None,
            candidates=best_candidates,
            used_query=best_query if status != "NOT_FOUND" else None,
            debug=debug_info if include_debug else None,
        )

    def _query_once(self, query: str, top_k: int) -> Dict[str, Any]:
        """
        ChromaDB에 단일 질의를 수행하고 Candidate 리스트로 반환.
        """
        query = _norm_text(query)
        if not query:
            return {"candidates": []}

        # include: metadatas, distances를 받아 score 계산
        raw = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["metadatas", "distances"],  # ✅ ids 제거
        )

        ids = _safe_get_first(raw.get("ids"), [])
        if not ids:
            # ids가 반환되지 않는 환경 대비: index 기반 가짜 id
            ids = [f"idx_{i}" for i in range(len(_safe_get_first(raw.get('metadatas'), [])))]
        metadatas = _safe_get_first(raw.get("metadatas"), [])
        distances = _safe_get_first(raw.get("distances"), [])

        candidates: List[Candidate] = []

        for _id, md, dist in zip(ids, metadatas, distances):
            menu, ing, tags, source = _parse_metadata(md or {})
            score = _to_similarity(dist)

            candidates.append(
                Candidate(
                    id=str(_id),
                    score=float(score),
                    menu=menu,
                    ingredients_ko=ing,
                    alg_tags=tags,
                    source=source,
                )
            )

        # score 내림차순 정렬(혹시 Chroma 반환 순서가 불안정한 경우 방어)
        candidates.sort(key=lambda x: x.score, reverse=True)

        return {"candidates": candidates}


# ==============================
# MODULE-LEVEL CONVENIENCE API
# ==============================
_DEFAULT_RETRIEVER: Optional[ChromaMenuRetriever] = None


def get_retriever() -> ChromaMenuRetriever:
    global _DEFAULT_RETRIEVER
    if _DEFAULT_RETRIEVER is None:
        _DEFAULT_RETRIEVER = ChromaMenuRetriever()
    return _DEFAULT_RETRIEVER


def retrieve_menu(
    variants: List[str],
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    ambiguous_gap: float = DEFAULT_AMBIGUOUS_GAP,
    include_debug: bool = False,
) -> Dict[str, Any]:
    """
    함수형 인터페이스.
    반환값은 dict(직렬화 용이) 형태로 제공한다.
    """
    r = get_retriever().retrieve_menu(
        variants=variants,
        top_k=top_k,
        score_threshold=score_threshold,
        ambiguous_gap=ambiguous_gap,
        include_debug=include_debug,
    )

    return {
        "status": r.status,
        "used_query": r.used_query,
        "best_match": asdict(r.best_match) if r.best_match else None,
        "candidates": [asdict(c) for c in r.candidates],
        "debug": r.debug,
    }
