const SESSION_KEY = "final_project_session";

export function getSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function getMemberId() {
  const s = getSession();
  // 프로젝트에 따라 user.member_id / user.id 혼재 가능
  return s?.user?.member_id ?? s?.user?.id ?? 5; // fallback: 첨부 코드의 member_id=5 :contentReference[oaicite:3]{index=3}
}

export function getNickname() {
  const s = getSession();
  return s?.user?.nickname || "게스트";
}
