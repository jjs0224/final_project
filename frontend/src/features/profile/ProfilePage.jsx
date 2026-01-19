// src/features/profile/ProfilePage.jsx
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Header from "../../common/components/ui/Header";
import { mockUser } from "../../assets/mock/mockData";

const SESSION_KEY = "final_project_session";

// 세션 읽기 + 동기화용 유틸
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
  const navigate = useNavigate();

  const [session, setSession] = useState(() => getSession());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 프로필 데이터
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
      navigate("/login");
      return;
    }

    // 내 것만 보게 강제
    if (String(myId) !== String(memberId)) {
      navigate(`/profile/${myId}`);
      return;
    }

    let ignore = false;

    (async () => {
      setLoading(true);
      setError("");

      try {
        // ===============================
        // 서버 연결용 (실제 환경)
        // const res = await fetch(`/members/${memberId}`, {
        //   headers: { Authorization: `Bearer ${token}` },
        // });
        // if (!res.ok) throw new Error(`프로필 조회 실패 (${res.status})`);
        // const data = await res.json();

        // ===============================
        // 목업 테스트용
        const data = mockUser;

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
  }, [memberId, navigate, session?.access_token, session?.member_id]);

  // 저장(PATCH)
  const onSave = async () => {
    setError("");

    try {
      const token = session?.access_token;
      if (!token) {
        navigate("/login");
        return;
      }

      const payload = {
        nickname,
        gender,
        country,
        // item_ids / dislike_tags 필요 시 여기에 추가
        // item_ids: [],
        // dislike_tags: [],
      };

      // ===============================
      // 서버 연결용
      // const res = await fetch(`/members/${memberId}`, {
      //   method: "PATCH",
      //   headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      //   body: JSON.stringify(payload),
      // });
      // if (!res.ok) throw new Error(`프로필 수정 실패 (${res.status})`);
      // const updated = await res.json();

      // ===============================
      // 목업용
      const updated = { ...profile, ...payload };

      setProfile(updated);
      alert("저장 완료");
    } catch (e) {
      setError(e?.message || "저장 실패");
    }
  };

  // 좌측 메뉴 이동
  const goReviewList = () => navigate("/review");
  const goCommunity = () => navigate("/community");
  const goEdit = () => navigate(`/profile/${memberId}/edit`);

  return (
    <div>
      <Header showNav={true} showAuthArea={true} />

      <div className="profileWrap">
        <div className="profileLayout">
          {/* LEFT SIDEBAR */}
          <aside className="profileSidebar">
            <div className="sideTop">
              <div className="bannerBox">배너</div>
              <div className="profileTitle">Profile</div>
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
              <button className="menuBtn" type="button" onClick={goCommunity}>
                커뮤니티
              </button>
              <button className="menuBtn" type="button" onClick={goEdit}>
                회원정보 수정
              </button>
            </div>
          </aside>

          {/* RIGHT MAIN */}
          <section className="profileMain">
            {error && <div className="errorBox">{error}</div>}

            {/* MAP AREA */}
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
                <button className="moreBtn" type="button" onClick={goReviewList}>
                  더보기
                </button>
                <div className="cardBodyText">
                  내가 작성한
                  <br />
                  리뷰 리스트
                </div>
              </div>

              <div className="mainCard">
                <button className="moreBtn" type="button" onClick={goCommunity}>
                  더보기
                </button>
                <div className="cardBodyText">
                  나의 리뷰
                  <br />
                  기반으로 만든
                  <br />
                  커뮤니티 글
                </div>
              </div>
            </div>

            {/* 회원정보 수정 폼 */}
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
                    <input value={nickname} onChange={(e) => setNickname(e.target.value)} />
                  </label>

                  <label className="field">
                    <div className="label">Gender</div>
                    <input value={gender} onChange={(e) => setGender(e.target.value)} />
                  </label>

                  <label className="field">
                    <div className="label">Country</div>
                    <input value={country} onChange={(e) => setCountry(e.target.value)} />
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
