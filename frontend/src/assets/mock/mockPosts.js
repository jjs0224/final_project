// Community 페이지용 목업

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
];