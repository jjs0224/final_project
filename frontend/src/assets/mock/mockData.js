
import processedPreview from "./processed_preview.jpg";

/**
 * ===============================
 * MAIN 기능 목데이터
 * 실제 API 호출 대신 테스트용으로 사용
 * ===============================
 */
export const analyzeResponseMock = {
  image: {
    url: processedPreview,
    width: 2342,
    height: 2217,
  },
  menus: [
    {
      menuId: "menu_001",
      name_en: "Ebi Don",
      poly: [
        [282, 255],
        [1178, 247],
        [1180, 483],
        [284, 491],
      ],
      summary: { danger: 2, warning: 0, safe: 0 },
    },
  ],
};

export const menuDetailMock = {
  menu_001: {
    menuId: "menu_001",
    name_en: "Ebi Don",
    ingredients: [
      { tag: "ALG_CRUSTACEANS", status: "DANGEROUS" },
      { tag: "ALG_EGGS", status: "DANGEROUS" },
    ],
    ai_actions: [
      "WHY_DANGEROUS",
      "SUGGEST_ALTERNATIVE",
      "GENERATE_KOREAN",
    ],
  },
};

/**
 * ===============================
 * AUTH / REVIEW / COMMUNITY 목데이터
 * 실제 API 호출 대신 초기 화면 테스트용
 * ===============================
 */
export const mockUser = {
  isLoggedIn: true,
  member_id: "user_001",
  nickname: "TestUser",
  email: "test@example.com",
  // role: "user", // 필요 시 role 포함
};

export const mockReviews = [
  {
    id: "rev_001",
    title: "Delicious Sushi",
    summary: "Ebi Don was very fresh and tasty!",
  },
  {
    id: "rev_002",
    title: "Spicy Ramen",
    summary: "The ramen had too much chili for me.",
  },
  {
    id: "rev_003",
    title: "Sweet Mochi",
    summary: "The mochi was chewy and delightful.",
  },
];

export const mockPosts = [
  {
    id: "post_001",
    title: "Allergy Tips for Ebi Don",
    content: "Check for crustaceans and eggs in menu.",
    createdAt: new Date().toISOString(),
    imageUrl: "/images/menu_abc.jpg",
    likeCount: 3,
    likedByMe: true,
    allergy_tags: ["ALG_CRUSTACEANS"],
    comments: [
      { id: "cmt_001", authorNickname: "Alice", text: "Thanks for the tip!" },
      { id: "cmt_002", authorNickname: "Bob", text: "Very useful!" },
    ],
  },
  {
    id: "post_002",
    title: "Ramen Spice Level",
    content: "Be careful with spice levels in the ramen.",
    createdAt: new Date().toISOString(),
    imageUrl: "/images/menu_abc.jpg",
    likeCount: 1,
    likedByMe: false,
    allergy_tags: [],
    comments: [],
  },
];

/**
 * ===============================
 * 공통 유틸 및 상수 테스트용
 * ===============================
 */
export const testMemberId = mockUser.member_id;
export const testNickname = mockUser.nickname;

/**
 * ===============================
 * 사용 예시
 * ===============================
 *
 * import { analyzeResponseMock, menuDetailMock, mockUser, mockReviews, mockPosts } from '../assets/mock/mockData';
 *
 * // MAIN 페이지
 * const data = analyzeResponseMock;
 * const detail = menuDetailMock[data.menus[0].menuId];
 *
 * // REVIEW 페이지
 * const reviews = mockReviews;
 *
 * // COMMUNITY 페이지
 * const posts = mockPosts;
 *
 * // AUTH 페이지
 * const user = mockUser;
 */
