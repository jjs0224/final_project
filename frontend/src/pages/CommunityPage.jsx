import "./CommunityPage.css";
import { useEffect, useRef, useState } from "react";
import Modal from "../components/Modal";
import Header from "../components/Header";

function buildPost(n) {
  return {
    id: `p-${n}`,
    title: `논문/게시글 ${n}`,
    author: { id: "u-1", nickname: `작성자${(n % 5) + 1}` },
    veganInfo: ["비건", "락토", "오보", "페스코"][n % 4],
    likes: Math.floor(Math.random() * 50),
    comments: Array.from({ length: n % 4 }, (_, c) => ({
      id: `c-${n}-${c + 1}`,
      nickname: `댓글러${c + 1}`,
      content: `댓글 내용 ${c + 1}`,
      mine: c === 0,
    })),
    paperText: `여기는 논문/본문 영역(임시)\n\n본문 ${n}`,
  };
}

export default function CommunityPage() {
  const [posts, setPosts] = useState(() => Array.from({ length: 12 }, (_, i) => buildPost(i + 1)));
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  // 모달
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(null);
  const [commentText, setCommentText] = useState("");

  const sentinelRef = useRef(null);
  const nextIndexRef = useRef(13);

  const loadMore = async () => {
    if (!hasMore || loadingMore) return;
    setLoadingMore(true);
    await new Promise((r) => setTimeout(r, 150));

    const start = nextIndexRef.current;
    const add = Array.from({ length: 10 }, (_, i) => buildPost(start + i));

    nextIndexRef.current = start + 10;

    setPosts((p) => [...p, ...add]);
    if (nextIndexRef.current > 80) setHasMore(false);

    setLoadingMore(false);
  };

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;

    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) loadMore();
      },
      { threshold: 1 }
    );

    io.observe(el);
    return () => io.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sentinelRef.current, hasMore, loadingMore]);

  const openPost = (post) => {
    setActive(post);
    setOpen(true);
    setCommentText("");
  };

  const closePost = () => {
    setOpen(false);
    setActive(null);
    setCommentText("");
  };

  const onLike = () => {
    if (!active) return;
    setActive((p) => ({ ...p, likes: p.likes + 1 }));
    setPosts((list) => list.map((x) => (x.id === active.id ? { ...x, likes: x.likes + 1 } : x)));
  };

  const onAddComment = () => {
    if (!active) return;
    if (!commentText.trim()) return;

    const newC = {
      id: `c-${active.id}-${Date.now()}`,
      nickname: "닉네임",
      content: commentText,
      mine: true,
    };

    setActive((p) => ({ ...p, comments: [...p.comments, newC] }));
    setCommentText("");
  };

  const onDeleteComment = (commentId) => {
    if (!active) return;
    setActive((p) => ({ ...p, comments: p.comments.filter((c) => c.id !== commentId) }));
  };

  return (
    <div className="pageWrap">
      <Header />
      <div className="communityGrid">
        {posts.map((p) => (
          <button key={p.id} className="postCard" onClick={() => openPost(p)} type="button">
            <div className="thumb">논문 사진</div>
            <div className="postMeta">
              <div className="postTitle">{p.title}</div>
              <div className="postSub">
                <span className="chip">작성자: {p.author.nickname}</span>
                <span className="chip">비/논비: {p.veganInfo}</span>
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="muted bottomHint">
        {loadingMore ? "불러오는 중..." : hasMore ? "아래로 스크롤하면 계속 로딩" : "마지막입니다."}
      </div>

      <div ref={sentinelRef} style={{ height: 1 }} />

      <Modal open={open} title="게시글" onClose={closePost}>
        {!active ? null : (
          <div className="communityModal">
            <section className="paperPane">
              <div className="paperBox">
                <div className="paperTitle">{active.title}</div>
                <div className="paperInfo">
                  작성자: {active.author.nickname} / 비/논비: {active.veganInfo}
                </div>
                <pre className="paperText">{active.paperText}</pre>
              </div>
            </section>

            <section className="commentPane">
              <div className="likeRow">
                <button className="solidBtn" onClick={onLike}>
                  좋아요 ({active.likes})
                </button>
              </div>

              <div className="commentList">
                {active.comments.length === 0 ? (
                  <div className="muted">댓글이 없습니다.</div>
                ) : (
                  active.comments.map((c) => (
                    <div key={c.id} className="commentItem">
                      <div className="commentHead">
                        <strong>{c.nickname}</strong>
                        {c.mine && (
                          <button className="ghostBtn" onClick={() => onDeleteComment(c.id)}>
                            삭제
                          </button>
                        )}
                      </div>
                      <div className="commentBody">{c.content}</div>
                    </div>
                  ))
                )}
              </div>

              <div className="commentWrite">
                <div className="muted">닉네임: 닉네임</div>
                <textarea
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  placeholder="댓글내용"
                  rows={3}
                />
                <button className="solidBtn" onClick={onAddComment}>
                  등록
                </button>
              </div>
            </section>
          </div>
        )}
      </Modal>
    </div>
  );
}
