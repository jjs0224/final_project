
import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../../common/components/ui/Header";
import ReviewList from "./ReviewList";
import { mockUser, mockReviews } from "../../assets/mock/mockData";

export default function ReviewPage() {
  const navigate = useNavigate();
  const nickname = useMemo(() => mockUser.nickname, []);

  const [q, setQ] = useState("");
  const [items, setItems] = useState(mockReviews);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;

    const fetchReviews = async () => {
      setLoading(true);
      try {
        // 서버 호출 예시
        // const res = await fetch(`/reviews?q=${q}`);
        // const data = await res.json();
        // if (alive) setItems(data);

        // 목업 필터링
        const filtered = mockReviews.filter(
          (r) => r.title.includes(q) || r.summary.includes(q)
        );
        if (alive) setItems(filtered);
      } finally {
        if (alive) setLoading(false);
      }
    };

    fetchReviews();

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
          placeholder="검색"
        />
        <button className="create_review_Btn" onClick={() => navigate("/review/new")}>
          리뷰 작성
        </button>
      </div>

      <div className="listBox">
        {loading ? <div className="muted">불러오는 중...</div> : <ReviewList items={items} />}
      </div>
    </div>
  );
}
