// src/services/communityApi.js
import { getMyReviews } from "./myReviewsSource";
import { generateCommunityImage } from "./generativeImageApi";

const KEY = "community_posts_v1";

function safeParse(raw, fallback) {
  try {
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function load() {
  return safeParse(localStorage.getItem(KEY), []);
}

function save(rows) {
  localStorage.setItem(KEY, JSON.stringify(rows));
}

function uniq(arr) {
  return Array.from(new Set(arr.filter(Boolean)));
}

function pick3Random(reviews) {
  const shuffled = [...reviews].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, 3);
}

function nowIso() {
  return new Date().toISOString();
}

function seedComments() {
  const samples = [
    { author: "민지", text: "여기 저도 가봤는데 공감해요!" },
    { author: "철수", text: "메뉴 조합 좋아 보이네요." },
    { author: "지수", text: "알러지 표기 좋은 기능이에요." },
    { author: "영훈", text: "사진 분위기 감성 좋다." },
    { author: "수빈", text: "다음엔 다른 메뉴도 추천해주세요!" },
  ];
  const n = 2 + Math.floor(Math.random() * 4); // 2~5개
  const shuffled = [...samples].sort(() => Math.random() - 0.5).slice(0, n);
  return shuffled.map((c, idx) => ({
    id: `c-${Date.now()}-${idx}`,
    authorNickname: c.author,
    text: c.text,
    createdAt: nowIso(),
  }));
}

async function ensureSeedPosts(memberId) {
  const rows = load();
  if (rows.length > 0) return;

  const myReviews = getMyReviews(memberId);
  if (myReviews.length < 3) return;

  // seed 게시글 5개 생성 (각각 랜덤 3개 리뷰 기반)
  const seedCount = 5;
  const seeded = [];

  for (let i = 0; i < seedCount; i += 1) {
    const selected = pick3Random(myReviews);
    const selectedIds = selected.map((r) => String(r.review_id));

    const allergyTags = uniq(selected.flatMap((r) => r.allergy_tags || []));
    const imageUrl = await generateCommunityImage({ reviews: selected });

    const post = {
      id: `p-seed-${Date.now()}-${i}`,
      authorMemberId: memberId,
      authorNickname: "게스트", // 필요 시 session 연동 가능
      title: `오늘의 식사 기록 ${i + 1}`,
//      content: `리뷰 3개를 기반으로 생성된 커뮤니티 게시글입니다.\n선택된 리뷰: ${selectedIds.join(", ")}`,
      imageUrl,
      selectedReviewIds: selectedIds,

      // 핵심 메타
      allergy_tags: allergyTags,

      // 좋아요/댓글
      likeCount: 5 + Math.floor(Math.random() * 120),
      likedByMe: false,
      comments: seedComments(),

      createdAt: nowIso(),
    };

    seeded.push(post);
  }

  save(seeded);
}

export async function listCommunityPosts({ memberId }) {
  await ensureSeedPosts(memberId);
  const rows = load();
  rows.sort((a, b) => (b.createdAt || "").localeCompare(a.createdAt || ""));
  return rows;
}

export function createCommunityPost(post) {
  const rows = load();
  const next = {
    id: `p-${Date.now()}`,
    ...post,
    createdAt: nowIso(),
  };
  save([next, ...rows]);
  return next;
}

export function toggleLike(postId) {
  const rows = load();
  const idx = rows.findIndex((p) => String(p.id) === String(postId));
  if (idx < 0) return null;

  const p = rows[idx];
  const liked = !p.likedByMe;

  const updated = {
    ...p,
    likedByMe: liked,
    likeCount: Math.max(0, Number(p.likeCount || 0) + (liked ? 1 : -1)),
  };

  const nextRows = [...rows];
  nextRows[idx] = updated;
  save(nextRows);

  return updated;
}

export function addComment(postId, { authorNickname, text }) {
  const rows = load();
  const idx = rows.findIndex((p) => String(p.id) === String(postId));
  if (idx < 0) return null;

  const p = rows[idx];
  const comment = {
    id: `c-${Date.now()}`,
    authorNickname: authorNickname || "익명",
    text: String(text || "").trim(),
    createdAt: nowIso(),
  };

  if (!comment.text) return p;

  const updated = {
    ...p,
    comments: [...(p.comments || []), comment],
  };

  const nextRows = [...rows];
  nextRows[idx] = updated;
  save(nextRows);

  return updated;
}
