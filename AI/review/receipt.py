import os
from pathlib import Path
import cv2
import numpy as np
from paddleocr import PaddleOCR
import json
import requests

os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"

# MODEL_NAME = "Helsinki-NLP/opus-mt-ko-en"
#
# def build_translator():
#     from transformers import pipeline
#     return pipeline("translation", model="Helsinki-NLP/opus-mt-ko-en")
#
# translator = build_translator()

# ===============================
# PATH SETUP
# ===============================
BASE_DIR = Path(__file__).resolve().parent              # model_testing
UPLOAD_DIR = BASE_DIR / "tmp_receipt"
OUTPUT_DIR = BASE_DIR / "tmp_output"

OUTPUT_DIR.mkdir(exist_ok=True)

# def ko_to_en(text: str) -> str:
#     if not text:
#         return ""
#     out = translator(text, max_length=128)
#     return out[0]["translation_text"].strip()

# ================================
# OCR normalization
# ================================
def normalize_ocr_lines(ocr_lines):
    tokens = []

    for line in ocr_lines:
        bbox=line[0]
        text, conf = line[1]

        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]

        tokens.append({
            "text": text.strip(),
            "conf": conf,
            "bbox": bbox,
            "x_min": min(xs),
            "x_max": max(xs),
            "y_min": min(ys),
            "y_max": max(ys),
        })
    tokens.sort(key=lambda t: (t["y_min"], t["x_min"]))

    return tokens

# =======================================
# TOKEN 라인별로 조인해주기
# =======================================
def join_split_tokens(tokens, y_threshold=15):
    # 1. Y좌표 순으로 정렬
    tokens.sort(key=lambda x: x['y_min'])

    lines = []
    if not tokens: return lines

    current_line = [tokens[0]]

    for i in range(1, len(tokens)):
        # 이전 토큰과 Y좌표 차이가 threshold(예: 10px) 이내면 같은 줄로 간주
        if abs(tokens[i]['y_min'] - current_line[-1]['y_min']) < y_threshold:
            current_line.append(tokens[i])
        else:
            # 줄이 바뀌면 현재까지 모인 토큰들을 합쳐서 저장
            current_line.sort(key=lambda x: x['x_min'])  # X좌표 순(왼쪽->오른쪽) 정렬
            lines.append(" ".join([t['text'] for t in current_line]))
            current_line = [tokens[i]]

    # 마지막 줄 처리
    current_line.sort(key=lambda x: x['x_min'])
    lines.append(" ".join([t['text'] for t in current_line]))

    print(lines)
    return lines


# 지역명 키워드와 지역번호 매핑
AREA_CODE_MAP = {
    "서울": "02",
    "경기": "031",
    "인천": "032",
    "경북": "054",
    "경상북도": "054",
    "부산": "051",
    "대구": "053",
    "포항": "054"  # 포항은 경북이므로 054
}

#지역번호 없을때 텍스트값으로 번호찾아주기 (default=서울(02))
def detect_area_code(lines):
    # 기본값 설정
    detected_code = "02"

    for line in lines:
        # line이 아무리 길어도 '경상북도'가 포함되어 있는지 확인
        for city, code in AREA_CODE_MAP.items():
            if city in line:
                print(f"지역 키워드 발견: '{city}' (문장: {line[:30]}...) -> 지역번호 {code} 적용")
                return code

    return detected_code

#전화번호 추출
def extract_phone(lines):
    PHONE_REGEX = re.compile(
        r'(0\d{1,2})[-\s]?(\d{3,4})[-\s]?(\d{4})'
    )

    for line in lines:
        match = PHONE_REGEX.search(line)
        if match:
            phone = "".join(match.groups())
            return phone

    return None

#전화번호로 사업자 정보 검색(가게명, 주소, 번호, 위치)
def find_location(query):
    client_id = "45476rdzYavZqCFMWGI5"
    client_secret = "PDPZB2w7RS"
    print(query)
    # 지역 검색 API 엔드포인트
    url = "https://openapi.naver.com/v1/search/local.json"
    params = {
        "query": query,  # 전화번호나 상호명
        "display": 1  # 가장 정확한 1건만 출력
    }
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        items = response.json().get('items')
        if items:
            place = items[0]
            print(f"상호명: {place['title'].replace('<b>', '').replace('</b>', '')}")
            print(f"주소: {place['roadAddress']}")
            print(f"좌표(X, Y): {place['mapx']}, {place['mapy']}")
            return place
        else:
            print("결과를 찾을 수 없습니다.")
    else:
        print(f"Error: {response.status_code}")

# ==============================================
# 메뉴명 추출
# ==============================================
import re

def extract_menu_items(lines):
    menu_items = []

    START_KEYWORDS = ["메뉴", "단가", "금액", "수량", "품명"]
    STOP_KEYWORDS = ["부가세", "합계", "결제", "신용", "카드", "총액"]

    in_menu_section = False

    for line in lines:
        # 1. Start condition (단가/수량 등 찾기)
        if not in_menu_section and any(k in line for k in START_KEYWORDS):
            in_menu_section = True
            continue

        # 2. Stop condition
        if in_menu_section and any(k in line for k in STOP_KEYWORDS):
            break

        if not in_menu_section:
            continue

        # 3. Normalize line
        #clean = re.sub(r"[^\w가-힣\s]", " ", line)
        # tokens = clean.split()
        #
        # if len(tokens) < 2:
        #     continue

        # # 4. Extract price (last numeric token)
        # price = None
        # for t in reversed(tokens):
        #     if t.isdigit():
        #         price = int(t)
        #         break
        #
        # if not price:
        #     continue
        #
        # # 5. Extract menu name
        # price_index = tokens.index(str(price))
        name_tokens = line.split(" ")[0]
        # name = " ".join(name_tokens).strip()
        #
        # if len(name) < 2:
        #     continue

        menu_items.append(name_tokens)
    print("menu", menu_items)
    return menu_items


def is_menu_token(token_text, menu_lines):
    return any(token_text in line for line in menu_lines)

#영수증 JSON 으로 저장
def build_receipt_json(ocr_lines):
    tokens = normalize_ocr_lines(ocr_lines)
    lines = join_split_tokens(tokens)

    phone = extract_phone(lines)

    menu_ko = extract_menu_items(lines)
    menu = []

    # for line in menu_ko:
    #     ko_text = line
    #     en_text = ko_to_en(ko_text)
    #
    #     menu.append({
    #         "ko": ko_text,
    #         "en": en_text
    #     })

    print("phone:",phone)

    store_info = None
    receipt_json = {}

    if phone:
        store_info = find_location(phone)



    #네이버 검색 결과가 있을 경우 데이터 구성
    if store_info:
        receipt_json = {
            "store_name": store_info['title'].replace('<b>', '').replace('</b>', ''),
            "address": store_info['roadAddress'],
            "city": store_info['roadAddress'].split(" ")[0],
            "phone": phone,
            "coords": {"x": store_info['mapx'], "y": store_info['mapy']},
            "menu_name": menu_ko
        }
    else:
        receipt_json = [{"error": "Store information not found"}]

    path = Path("tmp_output/receipt_to_store.json")

    if path.exists():

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

            if isinstance(data, dict):
                data = [data]

    else:
        data = []

    data.append(receipt_json)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        print("receipt_to_store.json saved")

    return receipt_json



def normalize_receipt(image_path: Path, i):
    '''
    1. 2배확대 (작은 전화번호 인식용)
    2. Contrast 대폭향상 -> 흑백으로만들어서 글자 도드라지게만듬
    3. 전처리된 이미지 저장
    4. OCR 진행
    '''
    temp_path = OUTPUT_DIR / f"temp_modified{i}.jpg"
    img = cv2.imread(str(image_path))
    img = cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite("resize.jpg", img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cv2.imwrite("gray.jpg", gray)

    blur = cv2.GaussianBlur(gray, (5,5), 0)
    cv2.imwrite("blur.jpg", blur)


    thresh = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 5
    )


    cv2.imwrite(str(temp_path), thresh)

    ocr = PaddleOCR(
        lang="korean",
        use_angle_cls=True,
        use_doc_unwarping=True,
        det_limit_side_len=3000,  #높은수일수록 이미지를 더 큰 해상도로 분석
        det_db_thresh=0.1,        #기본 0.3 -> 0.1로 낮춰서 더 민감하게 찾음
        det_db_box_thresh=0.2,    #박스 생성 문턱값을 낮춤
        det_db_unclip_ratio=2.0,  #글자가 뭉개지지 않게 unclip ratio 조정
        use_space_char=True,
        rec_char_type="korean",
        show_log=False,
    )

    result = ocr.ocr(str(temp_path), cls=True)

    for line in result[0]:
        bbox = line[0]
        pts = np.array(bbox, dtype=np.int32)
        cv2.polylines(img, [pts], True, (0,0,0), 2)

    if result and result[0]:
        receipt_data = build_receipt_json(result[0])
        print(receipt_data)
    else:
        print("No OCR text detected")

    cv2.imwrite(str(temp_path), img)
    print("receipt_result.png")



# ===============================
# ENTRY POINT
# ===============================
if __name__ == "__main__":
    #image_files = list(UPLOAD_DIR.glob("*.jpg")) + list(UPLOAD_DIR.glob("*.png"))
    image_files = list(UPLOAD_DIR.glob("receipt_10.jpg"))
    if not image_files:
        raise FileNotFoundError("No receipt image found in Uploaded_Images")

    for i, image_path in enumerate(image_files):

        normalize_receipt(image_path, i)

