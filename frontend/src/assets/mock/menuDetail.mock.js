// Main 기능용 목업

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
      "GENERATE_KOREAN"
    ]
  },
};
