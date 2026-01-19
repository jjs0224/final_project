export const tagsToIcons = (tags = []) => {
  const mapping = {
    ALG_CRUSTACEANS: "🦀",
    ALG_EGGS: "🥚",
    ALG_MILK: "🥛",
    ALG_PEANUTS: "🥜",
  };
  return tags.map((tag) => ({ tag, icon: mapping[tag] || "❓" }));
};
