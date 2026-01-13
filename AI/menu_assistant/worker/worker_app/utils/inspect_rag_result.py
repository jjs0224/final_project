import json
from pathlib import Path
from collections import Counter


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    # 🔧 여기 경로만 필요에 따라 수정
    RAG_RESULT_PATH = Path(
        r"C:\Users\201\Desktop\PGHfolder\Final_project\AI\menu_assistant\data\runs\20260113_121958\rag\rag_match.json"
    )

    data = load_json(RAG_RESULT_PATH)

    status_counter = Counter()

    print("=" * 80)
    print("RAG MATCH SUMMARY (핵심 결과)")
    print("=" * 80)

    for item in data:
        idx = item.get("idx")
        raw_text = item.get("raw_text")

        rag = item.get("rag_match", {})
        status = rag.get("status", "UNKNOWN")
        status_counter[status] += 1

        best = rag.get("best_match")

        if status == "CONFIRMED" and best:
            print(
                f"[CONFIRMED] idx={idx} | "
                f"'{raw_text}' → {best['menu']} "
                f"(score={best['score']:.3f})"
            )

        elif status == "AMBIGUOUS" and best:
            print(
                f"[AMBIGUOUS] idx={idx} | "
                f"'{raw_text}' → {best['menu']} "
                f"(score={best['score']:.3f})"
            )

        else:
            print(
                f"[NOT_FOUND] idx={idx} | '{raw_text}'"
            )

    print("\n" + "-" * 80)
    print("STATUS COUNT")
    for k, v in status_counter.items():
        print(f"{k:12s}: {v}")
    print("-" * 80)

    confirmed = status_counter.get("CONFIRMED", 0)
    ambiguous = status_counter.get("AMBIGUOUS", 0)

    print(
        f"→ Step5(RISK) 대상 후보 수: {confirmed + ambiguous} "
        f"(CONFIRMED + AMBIGUOUS)"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()


#python menu_assistant\worker\worker_app\utils\inspect_rag_result.py
