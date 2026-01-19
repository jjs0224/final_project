import React from "react";
import './CommunityPostDetailModal.css'

export default function CommunityPostDetailModal({ post, onClose, onChanged }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000 }}>
      <div style={{ background: "#fff", padding: 20, borderRadius: 8, width: 400 }}>
        <h3>Post Details (Mock)</h3>
        <p>Title: {post?.title}</p>
        <p>Content: {post?.content}</p>
        <button onClick={() => { onChanged?.(); onClose?.(); }}>Update</button>
        <button onClick={onClose}>Close</button>
      </div>
    </div>
  );
}
