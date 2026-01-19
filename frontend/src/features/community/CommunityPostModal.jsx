import React from "react";
import './CommunityPostModal.css';

export default function CommunityPostModal({ memberId, onClose, onCreated }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000 }}>
      <div style={{ background: "#fff", padding: 20, borderRadius: 8, width: 400 }}>
        <h3>Create Post (Mock)</h3>
        <p>Member ID: {memberId}</p>
        <button onClick={() => { onCreated?.(); onClose?.(); }}>Create</button>
        <button onClick={onClose}>Close</button>
      </div>
    </div>
  );
}
