import React, { useEffect, useState } from "react";
import { menuDetailMock } from "../../../assets/mock/menuDetail.mock";
import "./FoodDetailModal.css";

export default function FoodDetailModal({ menuId, onClose }) {
  const [menuDetail, setMenuDetail] = useState(null);
  const [aiText, setAiText] = useState("");
  const [koreanText, setKoreanText] = useState("");
  const [isLoadingAI, setIsLoadingAI] = useState(false);
  const [isLoadingKR, setIsLoadingKR] = useState(false);

  useEffect(() => {
    setMenuDetail(menuDetailMock[menuId]);
  }, [menuId]);

  if (!menuDetail) return null;

  const handleAIExplain = async () => {
    setIsLoadingAI(true);
    setTimeout(() => {
      setAiText("This dish contains shrimp and eggs, which are common allergens and may cause severe allergic reactions.");
      setIsLoadingAI(false);
    }, 800);
  };

  const handleGenerateKorean = async () => {
    setIsLoadingKR(true);
    setTimeout(() => {
      setKoreanText("김치찌개에 돼지고기가 들어가나요?");
      setIsLoadingKR(false);
    }, 600);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container" onClick={e => e.stopPropagation()}>
        <section className="modal-body">
          <h3 className="font-5">{menuDetail.name_en}</h3>

          <div className="risk-summary">
            {menuDetail.summary?.danger > 0 && <span className="risk-badge danger">Danger {menuDetail.summary.danger}</span>}
            {menuDetail.summary?.warning > 0 && <span className="risk-badge warning">Warning {menuDetail.summary.warning}</span>}
            {menuDetail.summary?.safe > 0 && <span className="risk-badge safe">Safe {menuDetail.summary.safe}</span>}
          </div>
        </section>

        <section className="modal-body">
          <p className="font-8 modal-section-title">Ingredients</p>
          <ul className="ingredient-list">
            {menuDetail.ingredients.map(item => (
              <li key={item.tag} className={`ingredient-item status-${item.status.toLowerCase()}`}>
                {item.tag.replace("ALG_", "").toLowerCase()}
              </li>
            ))}
          </ul>
        </section>

        <div className="ai-actions-group">
          {menuDetail.ai_actions?.includes("WHY_DANGEROUS") && (
            <button className="button medium color-secondary" onClick={handleAIExplain} disabled={isLoadingAI}>
              {isLoadingAI ? "Analyzing…" : "Why is this risky for me?"}
            </button>
          )}
          {aiText && <div className="ai-result-box"><p>{aiText}</p></div>}

          {menuDetail.ai_actions?.includes("GENERATE_KOREAN") && (
            <button className="button medium color-secondary" onClick={handleGenerateKorean} disabled={isLoadingKR}>
              {isLoadingKR ? "Generating…" : "Translate for Staff (Korean)"}
            </button>
          )}
          {koreanText && <div className="ai-result-box"><p>{koreanText}</p></div>}
        </div>

        <footer className="modal-footer">
          <button className="button medium color-ghost" onClick={onClose}>Close</button>
        </footer>
      </div>
    </div>
  );
}
