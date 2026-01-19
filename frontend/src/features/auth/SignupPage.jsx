// src/features/auth/SignupPage.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../../common/components/ui/Header";
import { mockUser } from "../../assets/mock/mockData";
import './SignupPage.css';

// 상수: 성별, 국가 목록 (실제 서비스에서는 별도 파일로 분리 가능)
const GENDER_OPTIONS = ["Male", "Female", "Other"];
const COUNTRY_OPTIONS = ["Korea", "USA", "Japan", "China", "Other"];

export default function SignupPage() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: "",
    password: "",
    nickname: "",
    gender: "",
    country: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onChange = (e) =>
    setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (!form.email || !form.password || !form.nickname) {
        throw new Error("Email, Password, Nickname은 필수입니다.");
      }

      // =========================
      // 서버 호출 부분 (현재 주석)
      // =========================
      // const res = await fetch("/auth/signup", {
      //   method: "POST",
      //   headers: { "Content-Type": "application/json" },
      //   body: JSON.stringify(form),
      // });
      // if (!res.ok) {
      //   const err = await res.json().catch(() => ({}));
      //   throw new Error(err?.detail || `회원가입 실패 (${res.status})`);
      // }

      // =========================
      // 임시: 목업 데이터로 테스트
      // =========================
      const user = { ...mockUser, ...form };
      localStorage.setItem("final_project_session", JSON.stringify(user));
      window.dispatchEvent(new Event("session-changed"));

      navigate("/"); // 가입 후 홈으로 이동
    } catch (err) {
      setError(err?.message || "회원가입 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pageCenter">
      <Header showNav={false} showAuthArea={false} />

      <div className="signupBox">
        <form onSubmit={onSubmit} className="signupForm">
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
              type="password"
              name="password"
              value={form.password}
              onChange={onChange}
              placeholder="비밀번호"
              autoComplete="new-password"
            />
          </label>

          <label className="field">
            닉네임
            <input
              name="nickname"
              value={form.nickname}
              onChange={onChange}
              placeholder="닉네임"
            />
          </label>

          <label className="field">
            성별
            <select name="gender" value={form.gender} onChange={onChange}>
              <option value="">선택</option>
              {GENDER_OPTIONS.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            국가
            <select name="country" value={form.country} onChange={onChange}>
              <option value="">선택</option>
              {COUNTRY_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>

          {error && <div className="errorBox">{error}</div>}

          <button className="signupBtn wide" disabled={loading}>
            {loading ? "가입 중..." : "회원가입"}
          </button>

          <button
            type="button"
            className="loginBtn wide"
            onClick={() => navigate("/login")}
            disabled={loading}
          >
            로그인
          </button>
        </form>
      </div>
    </div>
  );
}
