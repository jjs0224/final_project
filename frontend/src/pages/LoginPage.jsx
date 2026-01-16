import "./LoginPage.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header.jsx";

const SESSION_KEY = "final_project_session";

const LOGIN_URL = "/auth/login";
const ME_URL = "/auth/me";

export default function LoginPage() {
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onChange = (e) =>
    setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (!form.email || !form.password) {
        throw new Error("이메일/비밀번호를 입력하세요.");
      }

      // FastAPI OAuth2PasswordRequestForm 규격
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
        throw new Error(err?.detail || `로그인 실패 (${res.status})`);
      }

      const tokenData = await res.json();
      const accessToken = tokenData?.access_token;

      if (!accessToken) throw new Error("로그인 응답에 access_token이 없습니다.");

      // /auth/me로 사용자 정보 조회
      const meRes = await fetch(ME_URL, {
        method: "GET",
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (!meRes.ok) {
        const err = await meRes.json().catch(() => ({}));
        throw new Error(err?.detail || `me 조회 실패 (${meRes.status})`);
      }

      const me = await meRes.json();
      const memberId = me?.member_id;
      if (!memberId) throw new Error("/auth/me 응답에 member_id가 없습니다.");

      // 너가 보여준 형태 그대로 저장
      const session = {
        token: accessToken,          // <-- 여기 핵심 (null 방지)
        member_id: memberId,
        nickname: me?.nickname ?? "",
      };

      localStorage.setItem(SESSION_KEY, JSON.stringify(session));
      // 같은 탭에서도 Header가 즉시 반영되게 이벤트 발생
      window.dispatchEvent(new Event("session-changed"));

      navigate("/");
    } catch (err) {
      setError(err?.message || "로그인 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pageCenter">
      <div>
        <Header showNav={false} showAuthArea={false} />
      </div>

      <div className="loginBox">
        <form onSubmit={onSubmit} className="loginForm">
          <label className="field">
            이메일
            <input
              name="email"
              value={form.email}
              onChange={onChange}
              placeholder="example@email.com"
              autoComplete="email"
            />
          </label>

          <label className="field">
            비밀번호
            <input
              name="password"
              type="password"
              value={form.password}
              onChange={onChange}
              placeholder="비밀번호"
              autoComplete="current-password"
            />
          </label>

          {error && <div className="errorBox">{error}</div>}

          <button className="loginBtn wide" disabled={loading}>
            {loading ? "로그인 중..." : "로그인"}
          </button>

          <button
            type="button"
            className="signupBtn wide"
            onClick={() => navigate("/signup")}
            disabled={loading}
          >
            회원가입
          </button>
        </form>
      </div>
    </div>
  );
}
