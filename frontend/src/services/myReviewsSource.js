// src/services/myReviewsSource.js
const KEY = "community_my_reviews_v1";

function safeParse(raw, fallback) {
  try {
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function loadArray() {
  return safeParse(localStorage.getItem(KEY), []);
}

function saveArray(arr) {
  localStorage.setItem(KEY, JSON.stringify(arr));
}

function ensureSeed(memberId) {
  const existing = loadArray();
  if (existing.length > 0) return;

  // seed 리뷰: 알러지 태그 포함 (예: milk, egg, peanut, wheat, shrimp, fish, soy, nuts, sesame)
  const seeded = [
    {
      review_id: `${memberId}-1`,
      member_id: memberId,
      review_title: "비건 샐러드 후기",
      review_content: "드레싱이 상큼했고 채소 신선도가 좋았습니다. 재방문 의사 있음.",
      rating: 8,
      location: "서울",
      store_name: "그린볼",
      address: "서울특별시 ...",
      menu_name: ["비건샐러드", "레몬드레싱"],
      allergy_tags: ["nuts", "sesame"],
    },
    {
      review_id: `${memberId}-2`,
      member_id: memberId,
      review_title: "라멘 맛집",
      review_content: "국물 농도가 진하고 면 식감이 좋았어요. 다만 짭짤한 편.",
      rating: 9,
      location: "부산",
      store_name: "멘야",
      address: "부산광역시 ...",
      menu_name: ["돈코츠라멘", "교자"],
      allergy_tags: ["wheat", "egg"],
    },
    {
      review_id: `${memberId}-3`,
      member_id: memberId,
      review_title: "해산물 파스타",
      review_content: "해산물 신선했고 소스가 잘 어울렸습니다. 가격대는 조금 있음.",
      rating: 7,
      location: "서울",
      store_name: "오션키친",
      address: "서울특별시 ...",
      menu_name: ["해산물파스타"],
      allergy_tags: ["shrimp", "fish", "wheat"],
    },
    {
      review_id: `${memberId}-4`,
      member_id: memberId,
      review_title: "수제버거",
      review_content: "패티 육즙 좋고 번이 부드러워요. 감자튀김도 괜찮았습니다.",
      rating: 8,
      location: "인천",
      store_name: "버거하우스",
      address: "인천광역시 ...",
      menu_name: ["치즈버거", "감자튀김"],
      allergy_tags: ["milk", "wheat"],
    },
    {
      review_id: `${memberId}-5`,
      member_id: memberId,
      review_title: "두부덮밥",
      review_content: "담백하고 부담 없어요. 간이 조금 약해서 소스 추가 추천.",
      rating: 6,
      location: "대전",
      store_name: "소이테이블",
      address: "대전광역시 ...",
      menu_name: ["두부덮밥"],
      allergy_tags: ["soy"],
    },
    {
      review_id: `${memberId}-6`,
      member_id: memberId,
      review_title: "땅콩 아이스크림",
      review_content: "땅콩 향이 강하고 식감이 좋아요. 달달한 디저트로 만족.",
      rating: 9,
      location: "서울",
      store_name: "스윗스쿱",
      address: "서울특별시 ...",
      menu_name: ["땅콩아이스크림"],
      allergy_tags: ["peanut", "milk", "nuts"],
    },
  ];

  saveArray(seeded);
}

export function getMyReviews(memberId) {
  ensureSeed(memberId);
  return loadArray();
}
