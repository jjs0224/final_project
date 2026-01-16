// src/pages/CommunityPage.jsx
import { useLayoutEffect, useMemo, useRef, useState, useEffect } from "react";
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

  const headerRef = useRef(null);
  const [headerH, setHeaderH] = useState(64); // 초기값: 대략적인 헤더 높이(플리커 방지)

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

  // ✅ 헤더 높이 측정 (Community에서만 fixed를 쓰므로 정확한 높이를 padding/top에 반영)
  useLayoutEffect(() => {
    const el = headerRef.current;
    if (!el) return;

    const update = () => {
      const h = el.getBoundingClientRect().height;
      if (h && Math.abs(h - headerH) > 0.5) setHeaderH(h);
    };

    update();

    const ro = new ResizeObserver(update);
    ro.observe(el);

    window.addEventListener("resize", update);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", update);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openPost = posts.find((p) => String(p.id) === String(openPostId)) || null;

  return (
    <div
      className="pageWrap communityPageWrap"
      style={{ "--header-h": `${headerH}px` }}
    >
      {/* Header는 CommunityPage.css에서 fixed로 강제됨 */}
      <div ref={headerRef}>
        <Header />
      </div>

      {/* ✅ 헤더 아래에 붙는 sticky bar */}
      <div className="communityStickyBar">
        <div className="communityTop">
          <div>
            <div className="pageTitle">Community</div>
            <div className="muted">안녕하세요, {nickname}</div>
          </div>

          <button className="btn primary" type="button" onClick={() => setWriteOpen(true)}>
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

                    <div className="muted" style={{ marginTop: 6 }}>
                      게시글을 클릭하면 전체 보기/댓글 작성이 가능합니다.
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {writeOpen ? (
        <CommunityPostModal
          memberId={memberId}
          onClose={() => setWriteOpen(false)}
          onCreated={async () => {
            setWriteOpen(false);
            await refresh();
          }}
        />
      ) : null}

      {openPost ? (
        <CommunityPostDetailModal
          post={openPost}
          onClose={() => setOpenPostId(null)}
          onChanged={async () => {
            await refresh();
          }}
        />
      ) : null}
    </div>
  );
}
