import "./ReviewList.css";

export default function ReviewList({ items = [] }) {
  if (!items.length) return <div className="muted">리뷰가 없습니다.</div>;

  return (
    <ul className="reviewList">
      {items.map((r) => (
        <li key={r.id} className="reviewRow">
          <div className="reviewTitle">{r.title}</div>
          <div className="reviewSummary">{r.summary}</div>
        </li>
      ))}
    </ul>
  );
}
