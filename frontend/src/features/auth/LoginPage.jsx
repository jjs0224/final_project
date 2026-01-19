// src/features/auth/LoginPage.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../../common/components/ui/Header.jsx";
import './LoginPage.css';

// 테스트/통합 기준 세션 키
const SESSION_KEY = "final_project_session";

// 실제 서버 호출 URL
const LOGIN_URL = "/auth/login";
const ME_URL = "/auth/me";

// 목업 데이터 예시 (서버 연결 전 테스트용)
// const mockUser = { access_token: "mock_access", member_id: "user_001", nickname: "TestUser" };

export default function LoginPage() {
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onChange = (e) =>
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (!form.email || !form.password) {
        throw new Error("Please enter email and password.");
      }

      // 서버 연결: FastAPI OAuth2PasswordRequestForm 규격
      const body = new URLSearchParams();
      body.set("username", form.email);
      body.set("password", form.password);

      const res = await fetch(LOGIN_URL, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || `Login failed (${res.status})`);
      }

      const tokenData = await res.json();
      const accessToken = tokenData?.access_token;
      if (!accessToken) throw new Error("No access token in login response.");

      // 서버 연결: /auth/me 호출
      const meRes = await fetch(ME_URL, {
        method: "GET",
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (!meRes.ok) {
        const err = await meRes.json().catch(() => ({}));
        throw new Error(err?.detail || `Failed to fetch user info (${meRes.status})`);
      }

      const me = await meRes.json();
      const memberId = me?.member_id;
      if (!memberId) throw new Error("No member_id in /auth/me response.");

      // 세션 저장 및 이벤트 통일
      const sessionObj = {
        access_token: accessToken,
        member_id: memberId,
        nickname: me?.nickname ?? "",
      };
      localStorage.setItem(SESSION_KEY, JSON.stringify(sessionObj));
      window.dispatchEvent(new Event("session-changed"));

      navigate("/");

    } catch (err) {
      setError(err?.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pageCenter">
      <Header showNav={false} showAuthArea={false} />

      <div className="loginBox">
        <form onSubmit={onSubmit} className="loginForm">
          <label className="field">
            Email
            <input
              name="email"
              value={form.email}
              onChange={onChange}
              placeholder="example@email.com"
              autoComplete="email"
            />
          </label>

          <label className="field">
            Password
            <input
              name="password"
              type="password"
              value={form.password}
              onChange={onChange}
              placeholder="Password"
              autoComplete="current-password"
            />
          </label>

          {error && <div className="errorBox">{error}</div>}

          <button className="loginBtn wide" disabled={loading}>
            {loading ? "Logging in..." : "Login"}
          </button>

          <button
            type="button"
            className="signupBtn wide"
            onClick={() => navigate("/signup")}
            disabled={loading}
          >
            Sign Up
          </button>
        </form>
      </div>
    </div>
  );
}
