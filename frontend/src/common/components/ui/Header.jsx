import React from "react";
import { useNavigate, NavLink } from "react-router-dom";
import "./Header.css";

export default function Header({ showNav = true, showAuthArea = true, session, isLoggedIn, showLogin, showSignup, onLogout }) {
  const navigate = useNavigate();

  return (
    <header>
      <button onClick={() => navigate("/")}>FOOD RAY</button>
      {showNav && (
        <nav>
          <NavLink to="/review">Review</NavLink>
          <NavLink to="/community">Community</NavLink>
        </nav>
      )}
      {showAuthArea && (
        <div>
          {isLoggedIn ? (
            <>
              <button onClick={() => navigate("/profile")}>{session?.nickname || "Profile"}</button>
              <button onClick={onLogout}>로그아웃</button>
            </>
          ) : (
            <>
              {showLogin && <button onClick={() => navigate("/login")}>로그인</button>}
              {showSignup && <button onClick={() => navigate("/signup")}>회원가입</button>}
            </>
          )}
        </div>
      )}
    </header>
  );
}
