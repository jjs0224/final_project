import "./MenuOverlay.css";

export default function MenuOverlay({ poly, summary, onClick }) {
  const points = poly.map(([x, y]) => `${x},${y}`).join(" ");

  const level =
    summary.danger > 0
      ? "danger"
      : summary.warning > 0
      ? "warning"
      : "safe";

  return (
    <svg className="menu-overlay">
      <polygon
        points={points}
        className={`menu-poly ${level}`}
        onClick={onClick}
      />
    </svg>
  );
}

