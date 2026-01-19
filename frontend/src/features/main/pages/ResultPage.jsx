import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import MenuOverlay from "../components/MenuOverlay";
import FoodDetailModal from "../components/FoodDetailModal";
import { analyzeResponseMock } from "../../../assets/mock/analyzeResponse.mock";
import { convertPolyToScreen } from "../../../common/utils/convertPolyToScreen";
import "./ResultPage.css";
import Header from "../../../common/components/ui/Header";

export default function ResultPage() {
  const navigate = useNavigate();
  const { state } = useLocation();

  /** mock 분석 결과 사용 */
  const { image, menus } = analyzeResponseMock;

  const imgRef = useRef(null);
  const [renderedSize, setRenderedSize] = useState(null);
  const [selectedMenuId, setSelectedMenuId] = useState(null);

  /** 화면 렌더링 크기 측정 */
  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;
    const updateSize = () => setRenderedSize({ width: img.clientWidth, height: img.clientHeight });
    if (img.complete) updateSize();
    else img.onload = updateSize;
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  return (
    <main className="page result-page container">
      <header className="text-center" style={{ width: '100%', marginBottom: '8px' }}>
        <h2 className="font-4 font-bold">Analysis Results</h2>
        <p className="font-9" style={{ color: 'var(--gray-700)' }}>
          Tap highlighted items to see ingredient details.
        </p>
      </header>

      <section className="result-image-section">
        <img ref={imgRef} src={image.url} alt="Analyzed menu" className="result-image" />
        {renderedSize && menus.map(menu => (
          <MenuOverlay
            key={menu.menuId}
            poly={convertPolyToScreen(menu.poly, image, renderedSize)}
            summary={menu.summary}
            onClick={() => setSelectedMenuId(menu.menuId)}
            className={`menu-overlay ${menu.riskStatus}`}
          />
        ))}
      </section>

      <section className="result-bottom-bar">
        <button className="button medium color-ghost" onClick={() => navigate("/")}>Return Home</button>
        <button className="button medium color-secondary" onClick={() => navigate(-1)}>Scan Again</button>
      </section>

      {selectedMenuId && (
        <FoodDetailModal
          menuId={selectedMenuId}
          onClose={() => setSelectedMenuId(null)}
        />
      )}
    </main>
  );
}
