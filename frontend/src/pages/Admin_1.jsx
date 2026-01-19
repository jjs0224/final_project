import React, { useState } from "react";

export default function AdminRestrictionsBatchPage() {
  // ✅ 너 백엔드 주소에 맞게 수정
//   const API_URL = "http://127.0.0.1:8004/admin/restrictions/batch";
  const API_URL = "http://127.0.0.1:8004/admin/restrictions/batch";

  const emptyItem = () => ({ item_label_ko: "", item_label_en: "" });
  const emptyCategory = () => ({
    category_label_ko: "",
    category_label_en: "",
    items: [emptyItem()],
  });

  const [accessToken, setAccessToken] = useState("");
  const [categories, setCategories] = useState([emptyCategory()]);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [result, setResult] = useState(null);

  // ----------------- state helpers -----------------
  const addCategory = () => {
    setCategories((prev) => [...prev, emptyCategory()]);
  };

  const removeCategory = (catIdx) => {
    setCategories((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== catIdx)));
  };

  const updateCategoryField = (catIdx, field, value) => {
    setCategories((prev) =>
      prev.map((c, i) => (i === catIdx ? { ...c, [field]: value } : c))
    );
  };

  const addItem = (catIdx) => {
    setCategories((prev) =>
      prev.map((c, i) => (i === catIdx ? { ...c, items: [...c.items, emptyItem()] } : c))
    );
  };

  const removeItem = (catIdx, itemIdx) => {
    setCategories((prev) =>
      prev.map((c, i) => {
        if (i !== catIdx) return c;
        if (c.items.length <= 1) return c;
        return { ...c, items: c.items.filter((_, j) => j !== itemIdx) };
      })
    );
  };

  const updateItemField = (catIdx, itemIdx, field, value) => {
    setCategories((prev) =>
      prev.map((c, i) => {
        if (i !== catIdx) return c;
        const newItems = c.items.map((it, j) => (j === itemIdx ? { ...it, [field]: value } : it));
        return { ...c, items: newItems };
      })
    );
  };

  const reset = () => {
    setCategories([emptyCategory()]);
    setMsg("");
    setResult(null);
  };

  // ----------------- submit -----------------
  const buildPayload = () => {
    // ✅ trim + 빈 줄 제거(원하면 제거 로직 빼도 됨)
    const normalized = categories
      .map((c) => {
        const items = (c.items || [])
          .map((it) => ({
            item_label_ko: it.item_label_ko.trim(),
            item_label_en: it.item_label_en.trim(),
          }))
          .filter((it) => it.item_label_ko || it.item_label_en);

        return {
          category_label_ko: c.category_label_ko.trim(),
          category_label_en: c.category_label_en.trim(),
          items,
        };
      })
      .filter((c) => c.category_label_ko || c.category_label_en);

    return { categories: normalized };
  };

    const saveAll = async () => {
      setMsg("");
      setResult(null);

      const payload = buildPayload();
      if (!payload.categories.length) {
        setMsg("⚠️ 최소 1개의 카테고리를 입력해줘.");
        return;
      }

      // 간단 검증
      for (let i = 0; i < payload.categories.length; i++) {
        const c = payload.categories[i];
        if (!c.category_label_ko || !c.category_label_en) {
          setMsg(`⚠️ 카테고리 ${i + 1}: ko/en 둘 다 입력해줘.`);
          return;
        }
        for (let j = 0; j < c.items.length; j++) {
          const it = c.items[j];
          if (!it.item_label_ko || !it.item_label_en) {
            setMsg(`⚠️ 카테고리 ${i + 1} - 아이템 ${j + 1}: ko/en 둘 다 입력해줘.`);
            return;
          }
        }
      }

      console.log("payload :: ", payload);

      setSaving(true);
      try {
        const res = await fetch(API_URL, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          },
          body: JSON.stringify(payload),
        });

        // ✅ body는 한 번만 읽기
        const raw = await res.text();
        let data = null;
        try {
          data = raw ? JSON.parse(raw) : null;
        } catch {
          data = null;
        }

        console.log("status:", res.status);
        console.log("raw:", raw);
        console.log("parsed:", data);

        if (!res.ok) {
          const detail = data?.detail ?? data ?? raw ?? `저장 실패 (status ${res.status})`;
          throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail, null, 2));
        }

        setResult(data);
        setMsg("✅ 저장 성공!");
      } catch (e) {
        setMsg(`❌ ${e?.message || "알 수 없는 오류"}`);
      } finally {
        setSaving(false);
      }
    };

  // ----------------- UI -----------------
  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h2 style={styles.title}>Admin: Category / Item 일괄 등록</h2>
        <p style={styles.desc}>
          “카테고리 추가”로 입력 폼을 아래로 늘리고, 각 카테고리마다 “아이템 추가”로 하위 입력줄을
          늘린 뒤 “저장”을 누르면 한 번에 저장합니다.
        </p>
      </div>

      <div style={styles.card}>
        <div style={styles.rowBetween}>
          <div>
            <div style={styles.label}>Access Token (Admin)</div>
            <div style={styles.hint}>Bearer 빼고 토큰만 넣어도 되고, 백엔드가 쿠키면 비워도 됨</div>
          </div>
          <button type="button" style={styles.btnGhost} onClick={reset}>
            초기화
          </button>
        </div>

        <input
          style={styles.input}
          value={accessToken}
          onChange={(e) => setAccessToken(e.target.value)}
          placeholder="access token 입력 (선택)"
        />
      </div>

      <div style={styles.rowBetween}>
        <h3 style={styles.sectionTitle}>입력 폼</h3>
        <button type="button" style={styles.btn} onClick={addCategory}>
          + 카테고리 추가
        </button>
      </div>

      {categories.map((cat, catIdx) => (
        <div key={catIdx} style={styles.card}>
          <div style={styles.rowBetween}>
            <div style={styles.cardTitle}>카테고리 {catIdx + 1}</div>
            <button
              type="button"
              style={{
                ...styles.btnTextDanger,
                opacity: categories.length <= 1 ? 0.4 : 1,
                cursor: categories.length <= 1 ? "not-allowed" : "pointer",
              }}
              onClick={() => removeCategory(catIdx)}
              disabled={categories.length <= 1}
            >
              삭제
            </button>
          </div>

          <div style={styles.grid2}>
            <div>
              <div style={styles.label}>category_label_ko</div>
              <input
                style={styles.input}
                value={cat.category_label_ko}
                onChange={(e) => updateCategoryField(catIdx, "category_label_ko", e.target.value)}
                placeholder="예: 알레르기"
              />
            </div>

            <div>
              <div style={styles.label}>category_label_en</div>
              <input
                style={styles.input}
                value={cat.category_label_en}
                onChange={(e) => updateCategoryField(catIdx, "category_label_en", e.target.value)}
                placeholder="예: allergy"
              />
            </div>
          </div>

          <div style={styles.subBox}>
            <div style={styles.rowBetween}>
              <div style={styles.cardSubTitle}>Items</div>
              <button type="button" style={styles.btnGhost} onClick={() => addItem(catIdx)}>
                + 아이템 추가
              </button>
            </div>

            {cat.items.map((it, itemIdx) => (
              <div key={itemIdx} style={styles.itemRow}>
                <div style={{ ...styles.rowBetween, marginBottom: 8 }}>
                  <div style={styles.itemTitle}>아이템 {itemIdx + 1}</div>
                  <button
                    type="button"
                    style={{
                      ...styles.btnTextDanger,
                      opacity: cat.items.length <= 1 ? 0.4 : 1,
                      cursor: cat.items.length <= 1 ? "not-allowed" : "pointer",
                    }}
                    onClick={() => removeItem(catIdx, itemIdx)}
                    disabled={cat.items.length <= 1}
                  >
                    삭제
                  </button>
                </div>

                <div style={styles.grid2}>
                  <div>
                    <div style={styles.label}>item_label_ko</div>
                    <input
                      style={styles.input}
                      value={it.item_label_ko}
                      onChange={(e) => updateItemField(catIdx, itemIdx, "item_label_ko", e.target.value)}
                      placeholder="예: 우유"
                    />
                  </div>

                  <div>
                    <div style={styles.label}>item_label_en</div>
                    <input
                      style={styles.input}
                      value={it.item_label_en}
                      onChange={(e) => updateItemField(catIdx, itemIdx, "item_label_en", e.target.value)}
                      placeholder="예: milk"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      <div style={styles.actions}>
        <button type="button" style={styles.btnPrimary} onClick={saveAll} disabled={saving}>
          {saving ? "저장 중..." : "저장"}
        </button>
        <div style={styles.msg}>{msg}</div>
      </div>

      {result && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>서버 응답</div>
          <pre style={styles.pre}>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

// ----------------- simple CSS-in-JS -----------------
const styles = {
  page: {
    maxWidth: 980,
    margin: "0 auto",
    padding: "24px 16px 40px",
    fontFamily:
      'system-ui, -apple-system, Segoe UI, Roboto, "Noto Sans KR", "Apple SD Gothic Neo", sans-serif',
    color: "#111",
  },
  header: { marginBottom: 14 },
  title: { margin: 0, fontSize: 22, fontWeight: 700 },
  desc: { margin: "8px 0 0", fontSize: 13, color: "#555", lineHeight: 1.4 },
  sectionTitle: { margin: "12px 0", fontSize: 16, fontWeight: 700 },

  card: {
    border: "1px solid #e5e5e5",
    borderRadius: 12,
    padding: 14,
    background: "#fff",
    marginBottom: 12,
  },
  subBox: {
    marginTop: 12,
    background: "#f6f6f6",
    border: "1px solid #eee",
    borderRadius: 12,
    padding: 12,
  },

  rowBetween: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 },
  grid2: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 10,
    marginTop: 10,
  },

  label: { fontSize: 12, fontWeight: 700, marginBottom: 6 },
  hint: { fontSize: 12, color: "#666", marginTop: 2 },

  input: {
    width: "100%",
    padding: "10px 10px",
    borderRadius: 10,
    border: "1px solid #ddd",
    fontSize: 13,
    outline: "none",
  },

  btn: {
    padding: "10px 12px",
    borderRadius: 10,
    border: "1px solid #ddd",
    background: "#fff",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 700,
  },
  btnGhost: {
    padding: "8px 10px",
    borderRadius: 10,
    border: "1px solid #ddd",
    background: "#fff",
    cursor: "pointer",
    fontSize: 13,
  },
  btnPrimary: {
    padding: "10px 14px",
    borderRadius: 10,
    border: "1px solid #000",
    background: "#000",
    color: "#fff",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 700,
  },
  btnTextDanger: {
    border: "none",
    background: "transparent",
    color: "#c62828",
    fontSize: 13,
    cursor: "pointer",
  },

  cardTitle: { fontSize: 14, fontWeight: 800 },
  cardSubTitle: { fontSize: 13, fontWeight: 800 },
  itemRow: {
    background: "#fff",
    border: "1px solid #eaeaea",
    borderRadius: 12,
    padding: 12,
    marginTop: 10,
  },
  itemTitle: { fontSize: 13, fontWeight: 800 },

  actions: {
    marginTop: 16,
    display: "flex",
    alignItems: "center",
    gap: 12,
    flexWrap: "wrap",
  },
  msg: { fontSize: 13, color: "#333", whiteSpace: "pre-wrap" },

  pre: {
    marginTop: 10,
    padding: 12,
    borderRadius: 10,
    background: "#f6f6f6",
    border: "1px solid #eee",
    fontSize: 12,
    overflow: "auto",
  },
};
