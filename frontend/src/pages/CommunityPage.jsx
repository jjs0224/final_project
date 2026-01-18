// src/pages/CommunityPage.jsx
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import Header from "../components/Header";
import "./CommunityPage.css";

import { listCommunityPosts } from "../services/communityApi";
import { getMemberId, getNickname } from "../lib/session";
import { tagsToIcons } from "../lib/allergyIcons";

import CommunityPostDetailModal from "../components/CommunityPostDetailModal";
import CommunityPostModal from "../components/CommunityPostModal";

export default function CommunityPage() {
  const memberId = useMemo(() => getMemberId(), []);
  const nickname = useMemo(() => getNickname(), []);

  const [posts, setPosts] = useState([]);
  const [openPostId, setOpenPostId] = useState(null);
  const [writeOpen, setWriteOpen] = useState(false);

  const refresh = async () => {
    const rows = await listCommunityPosts({ memberId });
    setPosts(rows);
  };

  useEffect(() => {
    refresh();
  }, []);

  // ✅ Header 높이를 측정해서 communityStickyBar top 오프셋으로 사용
  useEffect(() => {
    const headerEl = document.querySelector(".appHeader");
    if (!headerEl) return;

    const setVar = () => {
      const h = headerEl.getBoundingClientRect().height || 0;
      document.documentElement.style.setProperty("--appHeaderH", `${h}px`);
    };

    setVar();

    // 헤더 높이가 바뀌는 경우(반응형/폰트/로그인 영역 변화) 대응
    let ro;
    try {
      ro = new ResizeObserver(() => setVar());
      ro.observe(headerEl);
    } catch {
      // ResizeObserver 미지원이면 무시
    }

    window.addEventListener("resize", setVar);
    return () => {
      window.removeEventListener("resize", setVar);
      if (ro) ro.disconnect();
    };
  }, []);

  // ✅ 모달 열릴 때 body 스크롤 잠금
  useEffect(() => {
    if (!writeOpen && !openPostId) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, [writeOpen, openPostId]);

  const openPost = posts.find((p) => String(p.id) === String(openPostId)) || null;

  const openWrite = (e) => {
    try {
      e?.preventDefault?.();
      e?.stopPropagation?.();
    } catch {}
    setWriteOpen(true);
  };

  return (
    <div className="pageWrap">
      <Header />

      <div className="communityStickyBar">
        <div className="communityTop">
          <div>
            <div className="pageTitle">Community</div>
            <div className="muted">안녕하세요, {nickname}</div>
          </div>

          <button
            className="btn primary"
            type="button"
            onPointerDownCapture={openWrite}
            onClickCapture={openWrite}
            onClick={openWrite}
          >
            게시글 작성
          </button>
        </div>
      </div>

      <div className="communityList">
        {posts.length === 0 ? (
          <div className="muted">게시글이 없습니다.</div>
        ) : (
          posts.map((p) => {
            const icons = tagsToIcons(p.allergy_tags || []);
            const comments = Array.isArray(p.comments) ? p.comments : [];
            const latest3 = comments.slice(-3);

            return (
              <div
                key={p.id}
                className="postCard"
                role="button"
                tabIndex={0}
                onClick={() => setOpenPostId(p.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") setOpenPostId(p.id);
                }}
              >
                <div className="postHeader">
                  <div className="postTitle">{p.title}</div>
                  <div className="muted">{new Date(p.createdAt).toLocaleString()}</div>
                </div>

                <div className="imageWrap">
                  <img className="postImage" src={p.imageUrl} alt="community" />

                  <div className="overlay topLeft">
                    {icons.length ? (
                      icons.map((x) => (
                        <span key={x.tag} className="pill" title={x.tag}>
                          {x.icon}
                        </span>
                      ))
                    ) : (
                      <span className="pill muted">No allergy</span>
                    )}
                  </div>

                  <div className="overlay topRight">
                    <span className="pill">❤️ {p.likeCount || 0}</span>
                  </div>

                  <div className="overlay bottomRight">
                    <span className={`pill ${p.likedByMe ? "liked" : ""}`}>좋아요</span>
                  </div>
                </div>

                <div className="postBodyGroup">
                  <div className="postContent">{String(p.content || "").trim()}</div>

                  <div className="commentPreview">
                    <div className="muted">최신 댓글</div>

                    {latest3.length === 0 ? (
                      <div className="muted">댓글이 없습니다.</div>
                    ) : (
                      latest3.map((c) => (
                        <div key={c.id} className="commentLine">
                          <span className="commentAuthor">{c.authorNickname || "익명"}</span>
                          <span className="commentText">{c.text}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* ✅ 작성 모달 (Portal) */}
      {writeOpen
        ? createPortal(
            <CommunityPostModal
              memberId={memberId}
              onClose={() => setWriteOpen(false)}
              onCreated={async () => {
                setWriteOpen(false);
                await refresh();
              }}
            />,
            document.body
          )
        : null}

      {/* ✅ 상세 모달 (Portal) */}
      {openPost
        ? createPortal(
            <CommunityPostDetailModal
              post={openPost}
              onClose={() => setOpenPostId(null)}
              onChanged={async () => {
                await refresh();
              }}
            />,
            document.body
          )
        : null}
    </div>
  );
}