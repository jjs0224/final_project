import "./ReviewPage.css";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import ReviewList from "../components/ReviewList";
import Header from "../components/Header";

const SESSION_KEY = "final_project_session";

function getSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

// 임시 리뷰 목록
async function mockFetchReviews({ q = "" }) {
  await new Promise((r) => setTimeout(r, 150));

  const all = Array.from({ length: 20 }, (_, i) => ({
    id: `r-${i + 1}`,
    title: `리뷰 제목 ${i + 1}`,
    summary: `리뷰 요약 ${i + 1}`,
  }));

  return all.filter((x) => (q ? x.title.includes(q) || x.summary.includes(q) : true));
}

export default function ReviewPage() {
  const navigate = useNavigate();
  const session = getSession();
  const nickname = useMemo(() => session?.user?.nickname || "게스트", [session]);

  const [q, setQ] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      try {
        const res = await mockFetchReviews({ q });
        if (!alive) return;
        setItems(res);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [q]);

  return (
    <div className="pageWrap">
      <Header />
      <div className="reviewTop">

        <input
          className="searchInput"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="검색창"
        />

        <button
          className="create_review_Btn"
          onClick={() => navigate("/review/new")}
        >
            Create Review
        </button>
      </div>

      <div className="listBox">
        {loading ? <div className="muted">불러오는 중...</div> : <ReviewList items={items} />}
      </div>
    </div>
  );
}

