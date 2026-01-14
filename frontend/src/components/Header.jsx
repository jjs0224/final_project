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

/**
 * ✅ 옵션(props)
 * - showNav: 네비게이션(Review/Community/Profile) 보여줄지
 * - showAuthArea: 우측 authArea 전체를 보여줄지
 * - showLogin: (비로그인 상태일 때) "로그인" 버튼 보여줄지
 * - showSignup: (비로그인 상태일 때) "회원가입" 버튼 보여줄지
 */
export default function Header({
  showNav = true,
  showAuthArea = true,
  showLogin = true,
  showSignup = true,
}) {
  const navigate = useNavigate();
  const [session, setSession] = useState(getSession());

  // 다른 탭/창에서 로그인/로그아웃해도 갱신되게
  useEffect(() => {
    const onStorage = () => setSession(getSession());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  // 같은 탭에서 LoginPage가 localStorage 바꾸면 즉시 반영되도록(간단 폴링)
  useEffect(() => {
    const id = setInterval(() => setSession(getSession()), 500);
    return () => clearInterval(id);
  }, []);

  const onLogout = () => {
    clearSession();
    setSession(null);
    navigate("/login");
  };

  return (
    <header className="appHeader">
      <div className="headerInner">
        <button className="brand" onClick={() => navigate("/")}>
          해넷
        </button>

        {showNav && (
          <nav className="nav">
            <NavLink className="navItem" to="/review">
              Review
            </NavLink>
            <NavLink className="navItem" to="/community">
              Community
            </NavLink>
          </nav>
        )}

        {showAuthArea && (
          <div className="authArea">
            {session?.user ? (
              <>
                <button
                  className="ghostBtn"
                  onClick={() => navigate(`/profile/${session.user.id}`)}
                  title="프로필로 이동"
                >
                  {session.user.nickname}
                </button>
                <button className="solidBtn" onClick={onLogout}>
                  로그아웃
                </button>
              </>
            ) : (
              <>
                {showLogin && (
                  <button className="ghostBtn" onClick={() => navigate("/login")}>
                    로그인
                  </button>
                )}
                {showSignup && (
                  <button className="solidBtn" onClick={() => navigate("/signup")}>
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
