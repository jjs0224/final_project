
export function convertPolyToScreen(poly, original, rendered) {
  const scaleX = rendered.width / original.width;
  const scaleY = rendered.height / original.height;

  return poly.map(([x, y]) => [
    Math.round(x * scaleX),
    Math.round(y * scaleY),
  ]);
}
