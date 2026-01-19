/**
 * navigateToPreview
 *
 * 역할
 * - PreviewPage로 이동하는 단일 진입점
 * - Camera / Upload 공통 사용
 * - 향후 옵션 확장 대비
 */
export function navigateToPreview(navigate, imageBlob, options = {}) {
  if (!imageBlob) return;

  const {
    source = "camera",      // camera | upload
    mock = false,           // 개발용
    meta = {},              // 향후 확장용
  } = options;

  navigate("/preview", {
    state: {
      imageBlob,
      source,
      mock,
      meta,
    },
  });
}
