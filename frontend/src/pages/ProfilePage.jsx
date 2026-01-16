import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Header from "../components/Header";

const SESSION_KEY = "final_project_session";

function getSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function ProfilePage() {
  const { memberId } = useParams();
  const nav = useNavigate();

  // ✅ session을 state로 들고 가야 deps 경고도 깔끔하고,
  //    로그인/로그아웃 시 같은 탭에서도 즉시 반영됨
  const [session, setSession] = useState(() => getSession());

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [profile, setProfile] = useState(null);
  const [nickname, setNickname] = useState("");
  const [gender, setGender] = useState("");
  const [country, setCountry] = useState("");

  // ✅ (추가) 세션 변경 감지: 다른 탭(storage) + 같은 탭(session-changed)
  useEffect(() => {
    const sync = () => setSession(getSession());

    window.addEventListener("storage", sync);
    window.addEventListener("session-changed", sync);

    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("session-changed", sync);
    };
  }, []);

  // ✅ 기존 useEffect 교체: deps에 nav/session 관련 포함
  useEffect(() => {
    const token = session?.token;
    const myId = session?.member_id;

    if (!token || !myId) {
      nav("/login");
      return;
    }

    // 원하면: 내 것만 보게 강제
    if (String(myId) !== String(memberId)) {
      nav(`/profile/${myId}`);
      return;
    }

    let ignore = false;

    (async () => {
      setLoading(true);
      setError("");

      try {
        const res = await fetch(`/members/${memberId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err?.detail || `프로필 조회 실패 (${res.status})`);
        }

        const data = await res.json();

        if (!ignore) {
          setProfile(data);
          setNickname(data?.nickname ?? "");
          setGender(data?.gender ?? "");
          setCountry(data?.country ?? "");
        }
      } catch (e) {
        if (!ignore) setError(e?.message || "프로필 조회 실패");
      } finally {
        if (!ignore) setLoading(false);
      }
    })();

    return () => {
      ignore = true;
    };
  }, [memberId, nav, session?.token, session?.member_id]);

  const onSave = async () => {
    setError("");

    try {
      const token = session?.token;
      if (!token) {
        nav("/login");
        return;
      }

      const payload = {
        nickname,
        gender,
        country,
        // 백엔드에서 item_ids/dislike_tags 필요하면 여기에 추가
        // item_ids: [],
        // dislike_tags: [],
      };

      const res = await fetch(`/members/${memberId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || `프로필 수정 실패 (${res.status})`);
      }

      const updated = await res.json();
      setProfile(updated);
      alert("저장 완료");
    } catch (e) {
      setError(e?.message || "저장 실패");
    }
  };

  return (
    <div>
      <Header />

      <div style={{ maxWidth: 520, margin: "24px auto", padding: 12 }}>
        <h2>My Profile</h2>

        {loading && <div>불러오는 중...</div>}
        {error && (
          <div style={{ border: "1px solid #b00020", padding: 10, color: "#b00020" }}>
            {error}
          </div>
        )}

        {!loading && profile && (
          <div style={{ display: "grid", gap: 12 }}>
            <label>
              Email (readonly)
              <input value={profile.email || ""} readOnly style={{ width: "100%" }} />
            </label>

            <label>
              Nickname
              <input
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                style={{ width: "100%" }}
              />
            </label>

            <label>
              Gender
              <input
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                style={{ width: "100%" }}
              />
            </label>

            <label>
              Country
              <input
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                style={{ width: "100%" }}
              />
            </label>

            <button onClick={onSave}>저장</button>
          </div>
        )}
      </div>
    </div>
  );
}
