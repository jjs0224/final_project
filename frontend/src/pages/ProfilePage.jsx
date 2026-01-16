import "./ProfilePage.css";
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

  // session을 state로 들고 가기(탭 내 즉시 반영)
  const [session, setSession] = useState(() => getSession());

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [profile, setProfile] = useState(null);
  const [nickname, setNickname] = useState("");
  const [gender, setGender] = useState("");
  const [country, setCountry] = useState("");

  // 세션 변경 감지: 다른 탭(storage) + 같은 탭(session-changed)
  useEffect(() => {
    const sync = () => setSession(getSession());

    window.addEventListener("storage", sync);
    window.addEventListener("session-changed", sync);

    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("session-changed", sync);
    };
  }, []);

  // 프로필 조회
  useEffect(() => {
    const token = session?.access_token;
    const myId = session?.member_id;

    if (!token || !myId) {
      nav("/login");
      return;
    }

    // 내 것만 보게 강제
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
  }, [memberId, nav, session?.access_token, session?.member_id]);

  // 저장(PATCH)
  const onSave = async () => {
    setError("");

    try {
      const token = session?.access_token;
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

  // 좌측 메뉴 이동(너 프로젝트 라우트에 맞춰 조정 가능)
  const goReviewList = () => nav("/review");
  const goPaperList = () => nav("/community"); // 임시: 논문 페이지 라우트가 따로 있으면 바꿔
  const goEdit = () => nav(`/profile/${memberId}/edit`); // 편집 전용 라우트 쓰면 바꿔

  return (
    <div>
      <Header />

      <div className="profileWrap">
        <div className="profileLayout">
          {/* LEFT SIDEBAR */}
          <aside className="profileSidebar">
            <div className="sideTop">
              <div className="bannerBox">배너</div>
              <div className="profileTitle">profile</div>
            </div>

            <div className="sideCard infoCard">
              {loading ? (
                <div className="muted">불러오는 중...</div>
              ) : (
                <>
                  <div className="infoText">{profile?.nickname ?? "-"}</div>
                  <div className="infoText">{profile?.email ?? "-"}</div>
                </>
              )}
            </div>

            <div className="sideCard menuCard">
              <button className="menuBtn" type="button" onClick={goReviewList}>
                리뷰 리스트
              </button>
              <button className="menuBtn" type="button" onClick={goPaperList}>
                논문 리스트
              </button>
              <button className="menuBtn" type="button" onClick={goEdit}>
                회원정보 수정
              </button>
            </div>
          </aside>

          {/* RIGHT MAIN */}
          <section className="profileMain">
            {/* ERROR BOX */}
            {error && (
              <div className="errorBox">
                {error}
              </div>
            )}

            {/* MAP AREA (지금은 박스만, 나중에 지도 컴포넌트 꽂으면 됨) */}
            <div className="mapBox">
              <div className="mapText">
                내가 다닌 장소를 표시하는 지도
                <br />
                보이는 위치
              </div>
            </div>

            {/* CARDS */}
            <div className="cardRow">
              <div className="mainCard">
                <button
                  className="moreBtn"
                  type="button"
                  onClick={goReviewList}
                >
                  더보기
                </button>

                <div className="cardBodyText">
                  내가 작성한
                  <br />
                  리뷰 리스트들
                </div>
              </div>

              <div className="mainCard">
                <button
                  className="moreBtn"
                  type="button"
                  onClick={goPaperList}
                >
                  더보기
                </button>

                <div className="cardBodyText">
                  나의 리뷰
                  <br />
                  기반으로 만든
                  <br />
                  논문 리스트들
                </div>
              </div>
            </div>

            {/* 회원정보 수정(우측 하단 편집 폼) - 와이어프레임엔 없지만 기능 유지하려고 접어둠 */}
            <details className="editDetails">
              <summary className="editSummary">회원정보 수정 열기</summary>

              <div className="editPanel">
                <div className="editGrid">
                  <label className="field">
                    <div className="label">Email (readonly)</div>
                    <input value={profile?.email || ""} readOnly />
                  </label>

                  <label className="field">
                    <div className="label">Nickname</div>
                    <input
                      value={nickname}
                      onChange={(e) => setNickname(e.target.value)}
                    />
                  </label>

                  <label className="field">
                    <div className="label">Gender</div>
                    <input
                      value={gender}
                      onChange={(e) => setGender(e.target.value)}
                    />
                  </label>

                  <label className="field">
                    <div className="label">Country</div>
                    <input
                      value={country}
                      onChange={(e) => setCountry(e.target.value)}
                    />
                  </label>

                  <button className="saveBtn" type="button" onClick={onSave}>
                    저장
                  </button>
                </div>
              </div>
            </details>
          </section>
        </div>
      </div>
    </div>
  );
}
