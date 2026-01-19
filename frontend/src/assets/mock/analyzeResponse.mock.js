// Main 기능용 목업

import processedPreview from "./processed_preview.jpg";

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
      summary: {
        danger: 2,
        warning: 0,
        safe: 0,
      },
    },
  ],
};
