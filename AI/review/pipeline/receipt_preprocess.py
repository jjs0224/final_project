import cv2
import numpy as np

def preprocess_image(image_bytes: bytes) -> np.ndarray:
    img_array = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    img = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cv2.imwrite("../gray.png", gray)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    cv2.imwrite("../color.png", blur)

    thresh = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 5
    )
    cv2.imwrite("../preprocess_0.png", thresh)

    # Convert back to 3 channels
    thresh_bgr = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
    cv2.imwrite("../preprocess.png", thresh_bgr)
    return thresh_bgr
