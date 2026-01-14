import json
from pathlib import Path
from collections import Counter


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fmt(v):
    return f"{v:.3f}" if isinstance(v, (int, float)) else "N/A"


def main():
    # 🔧 여기에 rag_match.json 경로만 수정
    RAG_RESULT_PATH = Path(
        r"C:\Users\201\Desktop\PGHfolder\Final_project\AI\menu_assistant\data\runs\20260114_182745\rag_match\rag_match.json"
    )

    # -----------------------------
    # 출력 옵션 (필요시만 수정)
    # -----------------------------
    SHOW_MAIN_LIST = True           # 전체 결과 리스트 출력
    SHOW_FILTERED_SECTION = True    # filtered_non_menu_candidate 별도 섹션 출력
    FILTERED_ONLY = False           # True면 "필터된 것만" 출력(메인 리스트 생략)
    MAX_FILTERED_PRINT = 80         # 필터 섹션에서 최대 출력 개수

    data = load_json(RAG_RESULT_PATH)

    items = data.get("items", [])
    stats = Counter()

    filtered = []  # menu_candidate=False 또는 reason=filtered_non_menu_candidate

    print("=" * 120)
    print("RAG MATCH RESULT SUMMARY (Step04: menu_candidate gate + Jaccard + Rerank + Fusion)")
    print("=" * 120)

    for i, item in enumerate(items):
        text = item.get("text") or item.get("raw_text") or ""
        rag = item.get("rag_match", {}) or {}

        status = rag.get("status", "UNKNOWN")
        reason = rag.get("reason")
        stats[status] += 1

        # menu_candidate gate로 걸린 항목 모으기
        if item.get("menu_candidate") is False or reason == "filtered_non_menu_candidate":
            filtered.append((i, text, item.get("menu_candidate"), reason, rag))
            # FILTERED_ONLY 모드면 여기서만 출력
            if FILTERED_ONLY:
                print(f"[FILTERED ] idx={i:04d} cand={item.get('menu_candidate')} reason={reason} | {text}")
            continue

        if FILTERED_ONLY:
            # 필터만 출력하는 모드면, 필터 아닌 항목은 출력하지 않음
            continue

        if not SHOW_MAIN_LIST:
            continue

        best = rag.get("best_match")
        if best:
            menu = (
                best.get("menu")
                or best.get("menu_ko")
                or best.get("menu_name")
                or "UNKNOWN"
            )

            embed = best.get("embed_score") or best.get("score")
            rerank = best.get("rerank_score")
            jacc = best.get("_jaccard")
            final_score = best.get("final_score")

            print(
                f"[{status:10s}] idx={i:04d} "
                f"{text:<24s} → {menu:<18s} | "
                f"embed={_fmt(embed)} rerank={_fmt(rerank)} jaccard={_fmt(jacc)} final={_fmt(final_score)}"
            )
        else:
            # best_match 없음
            used_q = rag.get("used_query")
            print(f"[{status:10s}] idx={i:04d} {text:<24s} → NO MATCH | used_query={used_q}")

    # -----------------------------
    # Summary
    # -----------------------------
    print("\n" + "-" * 120)
    print("STATUS COUNT")
    for k, v in stats.items():
        print(f"{k:14s}: {v}")
    print("-" * 120)

    confirmed = stats.get("CONFIRMED", 0)
    ambiguous = stats.get("AMBIGUOUS", 0)
    not_found = stats.get("NOT_FOUND", 0)

    print(f"→ Step05(RISK) 대상 수: {confirmed + ambiguous} (CONFIRMED + AMBIGUOUS)")
    print(f"→ NOT_FOUND: {not_found}")
    print(f"→ FILTERED(non-menu): {len(filtered)}")
    print("=" * 120)

    # -----------------------------
    # Filtered section
    # -----------------------------
    if SHOW_FILTERED_SECTION and filtered and not FILTERED_ONLY:
        print("\n" + "=" * 120)
        print("FILTERED ITEMS (menu_candidate=False OR reason=filtered_non_menu_candidate)")
        print("=" * 120)

        for n, (idx, text, cand, reason, rag) in enumerate(filtered[:MAX_FILTERED_PRINT], start=1):
            used_q = rag.get("used_query")
            print(f"[FILTERED ] #{n:03d} idx={idx:04d} cand={cand} reason={reason} | {text} | used_query={used_q}")

        if len(filtered) > MAX_FILTERED_PRINT:
            print(f"... truncated: showing {MAX_FILTERED_PRINT}/{len(filtered)}")

        print("=" * 120)


if __name__ == "__main__":
    main()
