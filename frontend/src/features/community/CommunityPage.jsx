import React, { useEffect, useState, useMemo } from "react";
import { createPortal } from "react-dom";
import Header from "../../common/components/ui/Header";
import CommunityPostModal from "./CommunityPostModal";
import CommunityPostDetailModal from "./CommunityPostDetailModal";
import { tagsToIcons } from "../../common/utils/allergyIcons";
import { mockUser, mockPosts } from "../../assets/mock/mockData";
import './CommunityPage.css';

export default function CommunityPage() {
  const memberId = useMemo(() => mockUser.member_id, []);
  const nickname = useMemo(() => mockUser.nickname, []);

  const [posts, setPosts] = useState([]);
  const [openPostId, setOpenPostId] = useState(null);
  const [writeOpen, setWriteOpen] = useState(false);

  const refresh = async () => {
    const rows = mockPosts; // mock data
    setPosts(rows);
  };

  useEffect(() => { refresh(); }, []);

  useEffect(() => {
    if (!writeOpen && !openPostId) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, [writeOpen, openPostId]);

  const openPost = posts.find((p) => String(p.id) === String(openPostId)) || null;

  const openWrite = (e) => { e?.preventDefault?.(); e?.stopPropagation?.(); setWriteOpen(true); };

  return (
    <div className="pageWrap">
      <Header />

      <div className="communityStickyBar">
        <div className="communityTop">
          <div>
            <div className="pageTitle">Community</div>
            <div className="muted">Hi, {nickname}</div>
          </div>
          <button className="btn primary" type="button" onClick={openWrite}>
            Create Post
          </button>
        </div>
      </div>

      <div className="communityList">
        {posts.length === 0 ? (
          <div className="muted">No posts yet.</div>
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
                onKeyDown={(e) => { if (e.key === "Enter") setOpenPostId(p.id); }}
              >
                <div className="postHeader">
                  <div className="postTitle">{p.title}</div>
                  <div className="muted">{new Date(p.createdAt).toLocaleString()}</div>
                </div>

                <div className="imageWrap">
                  <img className="postImage" src={p.imageUrl} alt="community" />
                  <div className="overlay topLeft">
                    {icons.length ? icons.map(x => <span key={x.tag} className="pill" title={x.tag}>{x.icon}</span>)
                      : <span className="pill muted">No allergy</span>}
                  </div>
                  <div className="overlay topRight">
                    <span className="pill">❤️ {p.likeCount || 0}</span>
                  </div>
                  <div className="overlay bottomRight">
                    <span className={`pill ${p.likedByMe ? "liked" : ""}`}>Like</span>
                  </div>
                </div>

                <div className="postBodyGroup">
                  <div className="postContent">{String(p.content || "").trim()}</div>
                  <div className="commentPreview">
                    <div className="muted">Latest comments</div>
                    {latest3.length === 0 ? (
                      <div className="muted">No comments</div>
                    ) : (
                      latest3.map(c => (
                        <div key={c.id} className="commentLine">
                          <span className="commentAuthor">{c.authorNickname || "Anonymous"}</span>
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

      {writeOpen && createPortal(
        <CommunityPostModal memberId={memberId} onClose={() => setWriteOpen(false)} onCreated={refresh} />,
        document.body
      )}

      {openPost && createPortal(
        <CommunityPostDetailModal post={openPost} onClose={() => setOpenPostId(null)} onChanged={refresh} />,
        document.body
      )}
    </div>
  );
}
