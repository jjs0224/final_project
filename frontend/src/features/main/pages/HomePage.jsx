import React from "react";
import { useNavigate } from "react-router-dom";
import Header from "../../../common/components/ui/Header";
import icon from '../../../Symbol_icon.svg';
import "./HomePage.css";

export default function HomePage({ user }) {
  const navigate = useNavigate();
  const handleNavigate = (path) => () => navigate(path);

  return (
    <main className="home-container container">
      <Header showNav={true} isLoggedIn={user?.isLoggedIn} session={user} />

      <img src={icon} className="App-logo" alt="AppLogo" />
      <h1 className="font-3 home-title font-bold">FOOD RAY</h1>
      <p className="font-8 text-center" style={{ color: 'var(--gray-700)' }}>
        Your Smart Guide to Safe Dining
      </p>

      <div className="section-label font-9">Quick Scan</div>
      <div className="core-menu">
        <button className="button big color-main" onClick={handleNavigate("/camera")}>
          📷 Scan Menu
        </button>
        <button className="button big color-main" onClick={handleNavigate("/upload")}>
          🖼️ Upload Photo
        </button>
      </div>

      <div className="section-label font-9">Personalize & Explore</div>
      <div className="sub-menu">
        <button className="button medium color-secondary" onClick={handleNavigate("/avoid-list")}>
          My Avoid Ingredients
        </button>
        <button className="button medium color-secondary" onClick={handleNavigate("/reviews")}>
          Reviews
        </button>
        <button className="button medium color-secondary" onClick={handleNavigate("/community")}>
          Community
        </button>
      </div>
    </main>
  );
}
