import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path

# ============================
# PATHS
# ============================
IMAGE_PATH = "tmp_receipt/receipt_7.jpg"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================
# LOAD YOLO MODEL
# ============================
# This model detects documents very well
model = YOLO("yolov8n.pt")  # lightweight, fast

# ============================
# VISUALIZE YOLO DETECTIONS
# ============================
def visualize_yolo(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(image_path)

    results = model(image)[0]
    # Draw boxes and confidence
    for i, (box, conf) in enumerate(zip(results.boxes.xyxy, results.boxes.conf)):
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            image, f"{conf:.2f}", (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
        )

        print(f"Box {i}: ({x1},{y1}) -> ({x2},{y2}), Confidence: {conf:.2f}")

    # Crop using Box 0 coordinates

    cropped = image[y1:y2, x1:x2]

    # Optionally, resize for better viewing
    cropped_resized = cv2.resize(cropped, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    # Save cropped image
    cv2.imwrite(OUTPUT_DIR / "cropped_box0.jpg", cropped_resized)
    print(f"✅ Cropped image saved to {OUTPUT_DIR / 'cropped_box0.jpg'}")

    # Show cropped image
    cv2.imshow("Cropped Document", cropped_resized)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# ============================
# DESKEW FUNCTION
# ============================
def deskew(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 50:
        return image

    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    h, w = image.shape[:2]
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)

    return cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )

# ============================
# MAIN RECEIPT DETECTION
# ============================
def detect_and_crop_receipt(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(image_path)

    # YOLO inference
    results = model(image)[0]



    if len(results.boxes) == 0:
        print("⚠ No document detected — returning original")
        return image

    # pick largest box (receipt)
    boxes = results.boxes.xyxy.cpu().numpy()
    areas = [(b[2]-b[0]) * (b[3]-b[1]) for b in boxes]
    box = boxes[np.argmax(areas)]

    x1, y1, x2, y2 = map(int, box)

    cropped = image[y1:y2, x1:x2]

    # enlarge to fill screen
    cropped = cv2.resize(
        cropped, None,
        fx=3, fy=3,
        interpolation=cv2.INTER_CUBIC
    )

    return cropped

# ============================
# PIPELINE
# ============================
def normalize_receipt(image_path):
    cropped = detect_and_crop_receipt(image_path)
    straight = deskew(cropped)

    cv2.imwrite(OUTPUT_DIR / "01_cropped.jpg", cropped)
    cv2.imwrite(OUTPUT_DIR / "02_straight.jpg", straight)

    print("✅ Receipt normalized successfully")
    return straight

# ============================
# ENTRY POINT
# ============================
if __name__ == "__main__":
    normalize_receipt(IMAGE_PATH)
    visualize_yolo(IMAGE_PATH)
