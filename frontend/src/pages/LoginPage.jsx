import "./LoginPage.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header.jsx";

const SESSION_KEY = "final_project_session";

const LOGIN_URL = "/auth/login"
const ME_URL = "/auth/me"

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

      // login data
      const body = new URLSearchParams();
      body.set("username", form.email);
      body.set("password", form.password);

      console.log("login form data :: ", body)

      const res = await fetch(LOGIN_URL, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      console.log("res :: ", res)

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        // FastAPI에서 보통 { detail: "..." }
        throw new Error(err?.detail || `로그인 실패 (${res.status})`);
      }

      const tokenData = await res.json();
      console.log("token data :: ", tokenData)

      // 인증에 사용될 accToken
      const accessToken = tokenData.access_token;

      const meRes = await fetch(ME_URL, {
        method: "GET",
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      const me = await meRes.json();
      console.log("me.member_id :: ", me.member_id)
      console.log("me :: ", me)



      // ✅ 백엔드 응답 형태가 달라도 최대한 대응
      const memberId =
        me?.member_id ?? me?.user?.member_id ?? me?.user?.id ?? me?.id;
      if (!memberId) {
        throw new Error("로그인 응답에 member_id(id)가 없습니다.");
      }



      const session = {
        token: me?.token ?? me?.access_token ?? null,
        member_id: memberId,
        nickname: me?.nickname ?? me?.user?.nickname ?? "",
      };

      localStorage.setItem(SESSION_KEY, JSON.stringify(session));

      // ✅ 로그인 후 이동 페이지
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