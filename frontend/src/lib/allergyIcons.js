// src/lib/allergyIcons.js
export const ALLERGY_ICON = {
  milk: "🥛",
  egg: "🥚",
  peanut: "🥜",
  wheat: "🌾",
  shrimp: "🦐",
  fish: "🐟",
  soy: "🫘",
  nuts: "🌰",
  sesame: "🧂",
};

export function normalizeAllergyTag(tag) {
  if (!tag) return null;
  const t = String(tag).trim().toLowerCase();
  return ALLERGY_ICON[t] ? t : null;
}

export function tagsToIcons(tags = []) {
  const normalized = tags
    .map(normalizeAllergyTag)
    .filter(Boolean);

  // 중복 제거
  return Array.from(new Set(normalized)).map((t) => ({
    tag: t,
    icon: ALLERGY_ICON[t],
  }));
}
