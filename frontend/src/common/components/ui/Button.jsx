import React from "react";

export default function Button({ children, type = "button", onClick, disabled, className }) {
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={className}>
      {children}
    </button>
  );
}
