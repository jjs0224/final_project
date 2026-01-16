// src/services/generativeImageApi.js
function escapeXml(s) {
  return String(s || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function makeSvgDataUrl({ title, lines }) {
  const w = 900;
  const h = 520;
  const safeTitle = escapeXml(title);
  const safeLines = lines.map((l) => escapeXml(l));

  const textLines = safeLines
    .slice(0, 10)
    .map(
      (l, i) =>
        `<text x="40" y="${140 + i * 34}" font-size="22" fill="#222">${l}</text>`
    )
    .join("");

  const svg = `
  <svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">
    <defs>
      <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
        <stop offset="0" stop-color="#f6f8ff"/>
        <stop offset="1" stop-color="#fff7f0"/>
      </linearGradient>
    </defs>
    <rect width="100%" height="100%" fill="url(#bg)"/>
    <rect x="24" y="24" width="${w - 48}" height="${h - 48}" rx="20" fill="#ffffff" stroke="#e7e7e7"/>
    <text x="40" y="90" font-size="30" font-weight="700" fill="#111">${safeTitle}</text>
    <text x="40" y="120" font-size="16" fill="#666">Generated (Community Seed)</text>
    ${textLines}
  </svg>`.trim();

  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export async function generateCommunityImage({ reviews }) {
  await new Promise((r) => setTimeout(r, 180));

  const lines = (reviews || []).map((r, idx) => {
    const store = r.store_name || "식당";
    const menus = (r.menu_name || []).slice(0, 2).join(", ");
    const snippet = (r.review_content || "").slice(0, 26);
    return `${idx + 1}. ${store} | ${menus || "메뉴"} | ${snippet}${snippet.length >= 26 ? "..." : ""}`;
  });

  return makeSvgDataUrl({ title: "Community Food Collage", lines });
}
