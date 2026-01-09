import "./LoginPage.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../components/Header.jsx"
import Header from "../components/Header.jsx";


const SESSION_KEY = "final_project_session";

// 임시 로그인(백엔드 붙이면 fetch로 교체)
async function mockLogin({ email, password }) {
  await new Promise((r) => setTimeout(r, 200));
  if (!email || !password) throw new Error("이메일/비밀번호를 입력하세요.");

  return {
    token: "mock-token",
    user: { id: "u-1", nickname: "닉네임" },
  };
}

export default function LoginPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const session = await mockLogin(form);
      localStorage.setItem(SESSION_KEY, JSON.stringify(session));
      navigate("/review");
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

            <button className="solidBtn wide" disabled={loading}>
                {loading ? "로그인 중..." : "로그인"}
            </button>

            <button type="button" className="ghostBtn wide" onClick={() => navigate("/signup")}>
                회원가입
            </button>
            </form>
        </div>
    </div>
  );
}
