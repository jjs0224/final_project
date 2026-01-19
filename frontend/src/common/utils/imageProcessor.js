
export async function resizeImage(blob, maxWidth = 1024) {
  const img = document.createElement("img");
  const url = URL.createObjectURL(blob);

  img.src = url;
  await img.decode();

  const scale = Math.min(1, maxWidth / img.width);
  const canvas = document.createElement("canvas");

  canvas.width = img.width * scale;
  canvas.height = img.height * scale;

  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

  return new Promise((resolve) => {
    canvas.toBlob((resizedBlob) => {
      URL.revokeObjectURL(url);
      resolve(resizedBlob);
    }, "image/jpeg", 0.9);
  });
}
