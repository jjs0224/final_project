import React from "react";
import { mockReviews } from "../../assets/mock/mockData";
import './ReviewList.css';

export default function ReviewList({ items = mockReviews }) {
  if (!items.length) return <div className="muted">No reviews yet.</div>;

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
