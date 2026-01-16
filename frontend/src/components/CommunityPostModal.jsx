import { useEffect, useMemo, useState } from "react";
import { getMyReviews } from "../services/myReviewsSource";
import { generateCommunityImage } from "../services/generativeImageApi";
import { createCommunityPost } from "../services/communityApi";
import { getNickname } from "../lib/session";

import "./CommunityPostModal.css"; // 없으면 생성(선택)

export default function CommunityPostModal({ memberId, onClose, onCreated }) {
  const [reviews, setReviews] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const [generating, setGenerating] = useState(false);
  const [imageUrl, setImageUrl] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const my = getMyReviews(memberId);
    setReviews(my);
  }, [memberId]);

  const selectedReviews = useMemo(
    () => reviews.filter((r) => selectedIds.includes(String(r.review_id))),
    [reviews, selectedIds]
  );

  const toggle = (id) => {
    setError("");
    const sid = String(id);
    setSelectedIds((prev) => {
      const has = prev.includes(sid);
      if (has) return prev.filter((x) => x !== sid);
      if (prev.length >= 3) return prev; // 3개 제한
      return [...prev, sid];
    });
  };

  const pickRandom3 = () => {
    setError("");
    if (reviews.length < 3) {
      setError("리뷰가 3개 이상 필요합니다.");
      return;
    }
    const shuffled = [...reviews].sort(() => Math.random() - 0.5);
    const picked = shuffled.slice(0, 3).map((r) => String(r.review_id));
    setSelectedIds(picked);
    setImageUrl(""); // 선택이 바뀌면 기존 이미지 무효화
  };

  const canGenerate = selectedIds.length === 3 && !generating;
  const canSubmit =
    title.trim() &&
    content.trim() &&
    selectedIds.length === 3 &&
    !!imageUrl &&
    !generating;

  const onGenerate = async () => {
    if (!canGenerate) return;
    setGenerating(true);
    setError("");
    try {
      // 생성형 AI에 넘길 핵심 입력: “리뷰 3개 내용 기반”
      const url = await generateCommunityImage({ reviews: selectedReviews });
      setImageUrl(url);
    } catch (e) {
      setError(e?.message || "이미지 생성 실패");
    } finally {
      setGenerating(false);
    }
  };

  const onSubmit = () => {
    if (!canSubmit) return;
    setError("");

    const post = createCommunityPost({
      title: title.trim(),
      content: content.trim(),
      imageUrl,
      memberId,
      authorNickname: getNickname(),
      selectedReviewIds: selectedIds,
    });

    onCreated?.(post);
  };

  return (
    <div className="modalOverlay" onMouseDown={onClose}>
      <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
        <div className="modalHeader">
          <div className="modalTitle">게시글 작성</div>
          <button className="btn ghost" type="button" onClick={onClose}>
            닫기
          </button>
        </div>

        {error ? <div className="errorBox">{error}</div> : null}

        {/* 1) 리뷰 3개 선택 */}
        <div className="section">
          <div className="sectionTitle">
            내 리뷰 선택 (3개) <span className="muted">({selectedIds.length}/3)</span>
          </div>

          <div className="row">
            <button className="btn ghost" type="button" onClick={pickRandom3} disabled={reviews.length < 3}>
              랜덤 3개 선택
            </button>
            <div className="muted">체크박스로 최대 3개까지 선택 가능합니다.</div>
          </div>

          <div className="reviewPickList">
            {reviews.map((r) => {
              const id = String(r.review_id);
              const checked = selectedIds.includes(id);
              return (
                <label key={id} className={`pickItem ${checked ? "checked" : ""}`}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggle(id)}
                    disabled={!checked && selectedIds.length >= 3}
                  />
                  <div className="pickMeta">
                    <div className="pickTitle">
                      {r.review_title || "(제목 없음)"}{" "}
                      <span className="muted">· {r.store_name || "식당"} · {r.location || "-"}</span>
                    </div>
                    <div className="pickDesc muted">
                      {(r.review_content || "").slice(0, 60)}
                      {(r.review_content || "").length > 60 ? "..." : ""}
                    </div>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        {/* 2) 이미지 생성 */}
        <div className="section">
          <div className="sectionTitle">사진 생성 (리뷰 3개 기반)</div>
          <div className="row">
            <button className="btn primary" type="button" onClick={onGenerate} disabled={!canGenerate}>
              {generating ? "생성 중..." : "이미지 생성"}
            </button>
            <div className="muted">선택된 3개 리뷰의 내용을 기반으로 생성합니다.</div>
          </div>

          {imageUrl ? (
            <div className="imagePreview">
              <img src={imageUrl} alt="generated-preview" />
            </div>
          ) : (
            <div className="muted">아직 생성된 이미지가 없습니다.</div>
          )}
        </div>

        {/* 3) 게시글 작성 */}
        <div className="section">
          <div className="sectionTitle">게시글 내용</div>

          <label className="field">
            <div className="label">제목</div>
            <input className="textInput" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={60} />
          </label>

          <label className="field">
            <div className="label">내용</div>
            <textarea className="textArea" value={content} onChange={(e) => setContent(e.target.value)} rows={6} maxLength={2000} />
          </label>

          <div className="modalActions">
            <button className="btn ghost" type="button" onClick={onClose} disabled={generating}>
              취소
            </button>
            <button className="btn primary" type="button" onClick={onSubmit} disabled={!canSubmit}>
              등록
            </button>
          </div>

          {!imageUrl ? (
            <div className="muted" style={{ marginTop: 8 }}>
              등록하려면 먼저 이미지를 생성해야 합니다.
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
