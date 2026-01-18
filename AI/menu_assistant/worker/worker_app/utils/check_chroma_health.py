from pathlib import Path
import chromadb
from chromadb.config import Settings

BASE_DIR = Path(__file__).resolve().parents[3]  # menu_assistant/
CHROMA_DIR = BASE_DIR / "data" / "chroma"
COLLECTION = "menu_index"

def main():
    if hasattr(chromadb, "PersistentClient"):
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    else:
        client = chromadb.Client(Settings(persist_directory=str(CHROMA_DIR), anonymized_telemetry=False))

    col = client.get_or_create_collection(name=COLLECTION)

    # count는 버전에 따라 없을 수 있어 get으로 방어
    try:
        n = col.count()
    except Exception:
        # 일부 버전은 count 미지원 → 한 번 get 해보고 길이로 추정
        got = col.get(limit=5, include=["metadatas"])
        n = len(got.get("ids", []))

    print(f"[CHROMA_DIR] {CHROMA_DIR}")
    print(f"[COLLECTION] {COLLECTION}")
    print(f"[COUNT] {n}")

    # 샘플 몇 개 출력
    sample = col.get(limit=3, include=["metadatas"])
    print("[SAMPLE IDS]", sample.get("ids"))
    print("[SAMPLE MENUS]", [m.get("menu") for m in (sample.get("metadatas") or [])])

if __name__ == "__main__":
    main()

'''
python menu_assistant/worker/worker_app/utils/check_chroma_health.py

'''