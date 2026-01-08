# AI/build_vector_index.py
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional



def embed_texts_sentence_transformers(texts: List[str], model_name: str) -> "Any":
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise RuntimeError(
            "sentence-transformers가 필요합니다. 설치: pip install sentence-transformers"
        ) from e

    model = SentenceTransformer(model_name)
    emb = model.encode(texts, normalize_embeddings=True, batch_size=128, show_progress_bar=True)
    return emb

def build_chroma(persist_dir: Path, collection_name: str, docs: List[Dict[str, Any]], model_name: str):
    try:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    except Exception as e:
        raise RuntimeError("chromadb가 필요합니다. 설치: pip install chromadb") from e

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))

    ef = SentenceTransformerEmbeddingFunction(model_name=model_name)

    # 컬렉션 생성/획득
    col = client.get_or_create_collection(
        name=collection_name,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    ids = [str(d["id"]) for d in docs]
    texts = [str(d["text_for_embed"]) for d in docs]
    metadatas = [{
        "menu": str(d.get("menu", "")),
        "category_lv1": str(d.get("category_lv1", "OTHER")),
        "category_conf": float(d.get("category_conf", 0.0)),
        "ALG_TAG": ",".join(d.get("ALG_TAG", []) or []),
    } for d in docs]

    # ✅ 권장: 대량 delete는 위험할 수 있음
    # 가장 안전: persist_dir/chroma 폴더를 삭제하고 다시 build
    # 그래도 코드로 하려면 "컬렉션 전체 삭제 후 재생성"이 안전
    # (아래는 선택)
    # try:
    #     client.delete_collection(name=collection_name)
    #     col = client.get_or_create_collection(
    #         name=collection_name,
    #         embedding_function=ef,
    #         metadata={"hnsw:space": "cosine"},
    #     )
    # except Exception:
    #     pass

    BATCH = 5000  # max 5461보다 작게

    for start in range(0, len(ids), BATCH):
        batch_ids = ids[start:start + BATCH]
        batch_texts = texts[start:start + BATCH]
        batch_metas = metadatas[start:start + BATCH]

        col.add(ids=batch_ids, documents=batch_texts, metadatas=batch_metas)
        print(f"[CHROMA] added {start}~{start + len(batch_ids) - 1} ({len(batch_ids)})")

    print(f"[OK] chroma built: {persist_dir} (collection={collection_name}, count={len(ids)})")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True, help="data/menu_catalog.jsonl")
    ap.add_argument("--mode", choices=["chroma", "npy"], required=True)
    ap.add_argument("--model", default="snunlp/KR-SBERT-V40K-klueNLI-augSTS", help="sentence-transformers model")
    ap.add_argument("--out_dir", required=True, help="index/vector")
    ap.add_argument("--collection", default="menu_catalog")
    args = ap.parse_args()

    catalog = Path(args.catalog)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    docs: List[Dict[str, Any]] = []
    with catalog.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                docs.append(json.loads(line))

    if args.mode == "chroma":
        persist_dir = out_dir / "chroma"
        build_chroma(persist_dir=persist_dir, collection_name=args.collection, docs=docs, model_name=args.model)
        return

    # mode == "npy": emb.npy + meta.jsonl
    texts = [d["text_for_embed"] for d in docs]
    emb = embed_texts_sentence_transformers(texts, model_name=args.model)

    import numpy as np
    emb_path = out_dir / "emb.npy"
    np.save(str(emb_path), emb)

    meta_path = out_dir / "meta.jsonl"
    with meta_path.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps({
                "id": d["id"],
                "menu": d["menu"],
                "category_lv1": d["category_lv1"],
                "category_conf": d["category_conf"],
                "ALG_TAG": d.get("ALG_TAG", []),
                "text_for_embed": d["text_for_embed"],
            }, ensure_ascii=False) + "\n")

    print(f"[OK] wrote: {emb_path}")
    print(f"[OK] wrote: {meta_path}")

if __name__ == "__main__":
    main()

'''
빌드:
python -m AI.build_vector_index ^
  --catalog AI/data/menu_catalog.jsonl ^
  --mode chroma ^
  --out_dir AI/index/vector ^
  --collection menu_catalog
'''