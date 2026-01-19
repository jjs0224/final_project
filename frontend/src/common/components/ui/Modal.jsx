import React from "react";

export default function Modal({ isOpen, onClose, onConfirm, message }) {
  if (!isOpen) return null;
  const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", justifyContent: "center", alignItems: "center" };
  const modalStyle = { background: "#fff", padding: 20, borderRadius: 8, minWidth: 300 };
  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <p>{message}</p>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 20 }}>
          <button onClick={onClose}>Cancel</button>
          <button onClick={onConfirm}>Confirm</button>
        </div>
      </div>
    </div>
  );
}
