import "./Header.css";
import { NavLink, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

const SESSION_KEY = "final_project_session";

function getSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

export default function Header({
  showNav = true,
  showAuthArea = true,
  showLogin = true,
  showSignup = true,
}) {
  const navigate = useNavigate();
  const [session, setSession] = useState(getSession());

  useEffect(() => {
    const sync = () => setSession(getSession());

    // ✅ 다른 탭/창 변경 감지
    window.addEventListener("storage", sync);

    // ✅ 같은 탭에서 LoginPage가 쏘는 이벤트 감지
    window.addEventListener("session-changed", sync);

    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("session-changed", sync);
    };
  }, []);

  const onLogout = () => {
    clearSession();
    setSession(null);
    window.dispatchEvent(new Event("session-changed"));
    navigate("/login");
  };

  const isLoggedIn = !!session?.access_token && !!session?.member_id;

  return (
    <header className="appHeader">
      <div className="headerInner">
        <button type="button" className="brand" onClick={() => navigate("/")}>
          해넷
        </button>

        {showNav && (
          <nav className="nav">
            <NavLink className="navItem" to="/review">Review</NavLink>
            <NavLink className="navItem" to="/community">Community</NavLink>
          </nav>
        )}

        {showAuthArea && (
          <div className="authArea">
            {isLoggedIn ? (
              <>
                <button
                  type="button"
                  className="ghostBtn"
                  onClick={() => navigate(`/profile/${session.member_id}`)}
                  title="프로필로 이동"
                >
                  {session.nickname || "Profile"}
                </button>
                <button type="button" className="solidBtn" onClick={onLogout}>
                  로그아웃
                </button>
              </>
            ) : (
              <>
                {showLogin && (
                  <button type="button" className="ghostBtn" onClick={() => navigate("/login")}>
                    로그인
                  </button>
                )}
                {showSignup && (
                  <button type="button" className="solidBtn" onClick={() => navigate("/signup")}>
                    회원가입
                  </button>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
