import json
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# ==============================
# CONFIG
# ==============================
COLLECTION_NAME = "menu_index"
BATCH_SIZE = 2000  # max batch size 이하로 안전하게
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# ==============================
# PATHS (✅ menu_assistant 기준 고정)
# ==============================
BASE_DIR = Path(__file__).resolve().parents[2]  # menu_assistant/
DATA_PATH = BASE_DIR / "data" /"datasets"/"raw"/ "menu_representative_korean_400.json"
CHROMA_DIR = BASE_DIR / "data" / "chroma"


def safe_str_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(v).strip() for v in x if str(v).strip()]
    s = str(x).strip()
    return [s] if s else []


def chunked(n: int, size: int):
    for i in range(0, n, size):
        yield i, min(i + size, n)


def main():
    print(f"[INFO] DATA_PATH: {DATA_PATH}")
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("menu_final_with_allergen.json must be a list")

    print(f"[INFO] Loaded records: {len(data)}")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] CHROMA_DIR: {CHROMA_DIR}")

    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )

    # Persist 보장: PersistentClient 우선
    if hasattr(chromadb, "PersistentClient"):
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    else:
        client = chromadb.Client(Settings(persist_directory=str(CHROMA_DIR), anonymized_telemetry=False))

    # 재빌드: 컬렉션 삭제 후 생성
    try:
        client.delete_collection(COLLECTION_NAME)
        print("[INFO] Existing collection deleted.")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=emb_fn,
    )

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    # ✅ 문서는 메뉴명 중심으로 단순화 (매칭 품질 ↑)
    for idx, item in enumerate(data):
        menu = str(item.get("menu", "")).strip()
        if not menu:
            continue

        ingredients = safe_str_list(item.get("ingredients_ko"))
        alg_tags = safe_str_list(item.get("alg_tags") or item.get("ALG_TAG"))  # ✅ 호환
        variants = safe_str_list(item.get("variants"))  # ✅ 400 데이터셋 기준

        ids.append(str(item.get("id") or f"menu_{idx}"))  # ✅ id가 있으면 사용
        documents.append(" ".join([menu] + variants))  # ✅ menu+variants 임베딩

        metadatas.append(
            {
                "menu": menu,
                "variants": ", ".join(variants),
                "ingredients_ko": ", ".join(ingredients),
                "alg_tags": ", ".join(alg_tags),
                "source": "representative_korean_menu_400",
            }
        )

    total = len(ids)
    print(f"[INFO] Prepared insert records: {total}")
    if total == 0:
        raise ValueError("No insertable records. Check dataset field 'menu'.")

    print(f"[INFO] Inserting in batches (BATCH_SIZE={BATCH_SIZE})...")
    for s, e in chunked(total, BATCH_SIZE):
        collection.add(
            ids=ids[s:e],
            documents=documents[s:e],
            metadatas=metadatas[s:e],
        )
        print(f"[INFO] Inserted {e}/{total}")

    # ✅ 삽입 검증
    try:
        cnt = collection.count()
    except Exception:
        got = collection.get(limit=5, include=["metadatas"])
        cnt = len(got.get("ids", []))

    print(f"[VERIFY] collection.count() = {cnt}")
    if cnt == 0:
        raise RuntimeError("Build finished but collection is empty. Check persist directory / permissions.")

    # 샘플 출력
    sample = collection.get(limit=3, include=["metadatas"])
    metas = sample.get("metadatas") or []
    print("[SAMPLE] ids:", sample.get("ids"))
    print("[SAMPLE] menus:", [m.get("menu") for m in metas])

    print("[SUCCESS] Chroma index build complete.")
    print(f"[MODEL] {EMBED_MODEL}")
    print(f"[COLLECTION] {COLLECTION_NAME}")
    print(f"[CHROMA_DIR] {CHROMA_DIR}")


if __name__ == "__main__":
    main()
