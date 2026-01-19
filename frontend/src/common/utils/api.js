// 서버 mock
// Main, Review, Community, Auth용 fetch mock
export async function fetchMenuAnalysis(imageFile) {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        url: URL.createObjectURL(imageFile),
        menus: [
          { menuId: 1, poly: [{ x: 10, y: 10 }, { x: 50, y: 10 }, { x: 50, y: 50 }, { x: 10, y: 50 }], summary: { danger: 1, warning: 0, safe: 2 }, riskStatus: "danger" },
        ],
      });
    }, 500);
  });
}

export async function loginUser({ email, password }) {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (email === "test@test.com" && password === "1234") {
        resolve({ member_id: 1, nickname: "Tester", isLoggedIn: true });
      } else {
        reject(new Error("Invalid credentials"));
      }
    }, 300);
  });
}

export async function signupUser(data) {
  return new Promise((resolve) => {
    setTimeout(() => resolve({ success: true, ...data }), 300);
  });
}

export async function fetchProfile(memberId) {
  return new Promise((resolve) => {
    setTimeout(() => resolve({ email: "test@test.com", nickname: "Tester", gender: "M", country: "KR" }), 300);
  });
}

export async function fetchCommunityPosts() {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve([
        {
          id: 1,
          title: "Sample Post",
          content: "This is a test post",
          createdAt: new Date().toISOString(),
          allergy_tags: ["MILK", "EGG"],
          comments: [{ id: 1, authorNickname: "Alice", text: "Nice!" }],
          likeCount: 5,
          likedByMe: true,
        },
      ]);
    }, 300);
  });
}

export async function fetchReviews() {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve([{ id: 1, title: "Good Food", summary: "Tasty and safe!" }]);
    }, 300);
  });
}

