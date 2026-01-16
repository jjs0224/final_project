// src/components/CommunityPostDetailModal.jsx
import { useMemo, useState } from "react";
import "./CommunityPostDetailModal.css";

import { tagsToIcons } from "../lib/allergyIcons";
import { toggleLike, addComment } from "../services/communityApi";
import { getNickname } from "../lib/session";

export default function CommunityPostDetailModal({ post, onClose, onChanged }) {
  const icons = useMemo(() => tagsToIcons(post.allergy_tags || []), [post]);
  const comments = Array.isArray(post.comments) ? post.comments : [];

  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);

  const onToggleLike = async () => {
    setSaving(true);
    try {
      toggleLike(post.id);
      await onChanged?.();
    } finally {
      setSaving(false);
    }
  };

  const onSubmitComment = async () => {
    const t = String(text || "").trim();
    if (!t) return;

    setSaving(true);
    try {
      addComment(post.id, { authorNickname: getNickname(), text: t });
      setText("");
      await onChanged?.();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modalOverlay" onMouseDown={onClose}>
      <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
        <div className="modalHeader">
          <div className="modalTitle">{post.title}</div>
          <button className="btn ghost" type="button" onClick={onClose}>
            닫기
          </button>
        </div>

        <div className="imageWrap">
          <img className="postImage" src={post.imageUrl} alt="community" />

          {/* 좌상단: 알러지 아이콘 */}
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

          {/* 우상단: 좋아요 수 */}
          <div className="overlay topRight">
            <span className="pill">❤️ {post.likeCount || 0}</span>
          </div>

          {/* 우하단: 좋아요 버튼 */}
          <div className="overlay bottomRight">
            <button
              className={`likeBtn ${post.likedByMe ? "liked" : ""}`}
              type="button"
              onClick={onToggleLike}
              disabled={saving}
            >
              {post.likedByMe ? "좋아요 취소" : "좋아요"}
            </button>
          </div>
        </div>

        <div className="postContent">{post.content}</div>

        {/* 이미지 하단: 댓글 입력 */}
        <div className="commentInputRow">
          <input
            className="textInput"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="댓글을 입력하세요"
            disabled={saving}
          />
          <button className="btn primary" type="button" onClick={onSubmitComment} disabled={saving || !text.trim()}>
            등록
          </button>
        </div>

        {/* 댓글 전체 */}
        <div className="commentList">
          <div className="sectionTitle">댓글</div>
          {comments.length === 0 ? (
            <div className="muted">댓글이 없습니다.</div>
          ) : (
            comments
              .slice()
              .sort((a, b) => String(a.createdAt || "").localeCompare(String(b.createdAt || "")))
              .map((c) => (
                <div key={c.id} className="commentItem">
                  <div className="commentTop">
                    <span className="commentAuthor">{c.authorNickname || "익명"}</span>
                    <span className="muted">{c.createdAt ? new Date(c.createdAt).toLocaleString() : ""}</span>
                  </div>
                  <div className="commentText">{c.text}</div>
                </div>
              ))
          )}
        </div>
      </div>
    </div>
  );
}
