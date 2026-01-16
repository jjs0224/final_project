// src/components/CommunityPostModal.jsx
import { useEffect, useMemo, useState } from "react";
import "./CommunityPostModal.css";

import { createCommunityPost } from "../services/communityApi";
import { generateCommunityImage } from "../services/generativeImageApi";
import { getNickname } from "../lib/session";

const COMMUNITY_MY_REVIEWS_KEY = "community_my_reviews_v1";

function nowISO() {
  return new Date().toISOString();
}

function readMyReviews() {
  try {
    const raw = localStorage.getItem(COMMUNITY_MY_REVIEWS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function writeMyReviews(rows) {
  localStorage.setItem(COMMUNITY_MY_REVIEWS_KEY, JSON.stringify(rows));
}

function ensureSeedMyReviews(memberId) {
  const rows = readMyReviews();
  if (rows.length > 0) return;

  const seed = Array.from({ length: 10 }, (_, i) => ({
    review_id: i + 1,
    member_id: memberId ?? 1,

    review_title: `리뷰 ${i + 1} - 오늘의 식사`,
    review_content: `리뷰 본문 ${i + 1}: 음식/식당 경험을 기록한 내용입니다.`,
    rating: Math.floor(Math.random() * 11), // 0~10
    location: "Seoul",
    create_review: nowISO(),
    availability: true,

    allergy_tags: i % 4 === 0 ? ["egg"] : i % 4 === 1 ? ["milk"] : [],
    summary: `리뷰 요약 ${i + 1}`,
  }));

  writeMyReviews(seed);
}

function pickRandom3(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a.slice(0, 3);
}

export default function CommunityPostModal({ memberId, onClose, onCreated }) {
  const nickname = useMemo(() => getNickname(), []);

  const [loadingReviews, setLoadingReviews] = useState(false);
  const [myReviews, setMyReviews] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);

  const [imgLoading, setImgLoading] = useState(false);
  const [generatedImageUrl, setGeneratedImageUrl] = useState("");

  const [title, setTitle] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoadingReviews(true);
      try {
        ensureSeedMyReviews(memberId);
        const rows = readMyReviews().filter(
          (r) => String(r.member_id) === String(memberId ?? r.member_id)
        );
        if (!alive) return;
        setMyReviews(rows);
      } finally {
        if (alive) setLoadingReviews(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [memberId]);

  const selectedReviews = useMemo(() => {
    const map = new Map(myReviews.map((r) => [String(r.review_id ?? r.id), r]));
    return selectedIds.map((id) => map.get(String(id))).filter(Boolean);
  }, [myReviews, selectedIds]);

  const canGenerate = selectedIds.length === 3 && !imgLoading;

  const toggle = (id) => {
    const sid = String(id);
    setGeneratedImageUrl("");
    setSelectedIds((prev) => {
      if (prev.includes(sid)) return prev.filter((x) => x !== sid);
      if (prev.length >= 3) return prev;
      return [...prev, sid];
    });
  };

  const randomPick = () => {
    setGeneratedImageUrl("");
    if (myReviews.length < 3) return;
    const picked = pickRandom3(myReviews).map((r) => String(r.review_id ?? r.id));
    setSelectedIds(picked);
  };

  const runGenerateImage = async () => {
    if (selectedIds.length !== 3) return;
    setImgLoading(true);
    setGeneratedImageUrl("");
    try {
      const url = await generateCommunityImage({
        memberId,
        reviews: selectedReviews,
      });
      setGeneratedImageUrl(url || "");
    } finally {
      setImgLoading(false);
    }
  };

  const submit = async () => {
    if (!generatedImageUrl) {
      alert("이미지 생성이 완료되어야 게시글을 등록할 수 있습니다.");
      return;
    }

    const safeTitle = title?.trim() || "오늘의 식사 기록";

    await createCommunityPost({
      memberId,
      title: safeTitle,
      content: "",
      imageUrl: generatedImageUrl,
      selectedReviewIds: selectedIds,
      authorNickname: nickname,

      likeCount: 0,
      likedByMe: false,
      comments: [],
      createdAt: new Date().toISOString(),

      allergy_tags: Array.from(
        new Set(selectedReviews.flatMap((r) => r.allergy_tags || []))
      ),
    });

    onCreated?.();
  };

  return (
    <div className="modalBackdrop" role="dialog" aria-modal="true" onMouseDown={onClose}>
      <div className="modalCard" onMouseDown={(e) => e.stopPropagation()}>
        <div className="modalHeader">
          <div className="modalTitle">게시글 작성</div>
          <button className="btn ghost" type="button" onClick={onClose}>
            닫기
          </button>
        </div>

        <div className="field">
          <div className="label">제목</div>
          <input
            className="input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="예) 오늘의 식사 기록"
          />
        </div>

        <div className="field">
          <div className="rowBetween">
            <div className="label">내 리뷰 선택 (3개)</div>
            <button
              className="btn ghost"
              type="button"
              onClick={randomPick}
              disabled={myReviews.length < 3}
            >
              랜덤 3개
            </button>
          </div>

          {loadingReviews ? (
            <div className="muted">리뷰 불러오는 중...</div>
          ) : myReviews.length === 0 ? (
            <div className="muted">선택할 리뷰가 없습니다.</div>
          ) : (
            <div className="reviewPickList">
              {myReviews.map((r) => {
                const id = String(r.review_id ?? r.id);
                const checked = selectedIds.includes(id);
                const titleText = r.review_title ?? "(제목 없음)";
                const summaryText =
                  r.summary ?? (r.review_content ? String(r.review_content).slice(0, 40) : "");

                return (
                  <label key={id} className={`pickRow ${checked ? "checked" : ""}`}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(id)}
                      disabled={!checked && selectedIds.length >= 3}
                    />
                    <div className="pickText">
                      <div className="pickTitle">{titleText}</div>
                      <div className="muted">{summaryText}</div>
                    </div>
                  </label>
                );
              })}
            </div>
          )}

          <div className="muted" style={{ marginTop: 6 }}>
            선택됨: {selectedIds.length}/3
          </div>
        </div>

        <div className="field">
          <div className="label">커뮤니티 이미지</div>

          {!generatedImageUrl && !imgLoading ? (
            <div className="muted">리뷰 3개를 선택한 뒤 “이미지 생성”을 눌러주세요.</div>
          ) : null}

          {imgLoading ? <div className="muted" style={{ padding: "10px 0" }}>이미지 생성중..</div> : null}

          {!imgLoading && generatedImageUrl ? (
            <div className="genPreview">
              <img className="genImage" src={generatedImageUrl} alt="generated" />
            </div>
          ) : null}

          <div className="rowBetween" style={{ marginTop: 10 }}>
            <button className="btn ghost" type="button" onClick={runGenerateImage} disabled={!canGenerate}>
              이미지 생성
            </button>
            <button className="btn primary" type="button" onClick={submit} disabled={!generatedImageUrl}>
              등록
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
