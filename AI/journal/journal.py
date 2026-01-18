import json
from google import genai
from google.genai import types
from io import BytesIO
from PIL import Image
import base64
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

client = genai.Client(
    api_key=API_KEY
)

def build_prompt(user_profile, reviews):

    # 2. Format the Review Data
    reviews_str = json.dumps(reviews, ensure_ascii=False, indent=2)

    # 3. Construct the Final Prompt
    full_prompt = f"""You are a professional travel food journal writer creating a visual food diary page
for foreign visitors traveling in South Korea.

TARGET USER:
- Has food allergies and dietary restrictions
- Relies on this app to eat safely in Korea
- Wants both emotional reassurance and practical guidance

USER DIETARY PROFILE:
{user_profile}

SOURCE REVIEWS (REAL EXPERIENCES):
{reviews}
TASK:
Create a SINGLE illustrated food journal page with:

TEXT REQUIREMENTS:
- 3 short paragraphs (one per review)
- Writing style:
  - Light humor + sincerity
  - Encouraging and honest
  - Written for international travelers
- Clearly mention:
  - Allergy awareness
  - Staff attitude
  - How the app helped ensure safety

TRUST SCORE:
- Evaluate how helpful this journal would be for OTHER users with egg allergies
- Score from 0 (not helpful) to 10 (extremely helpful)
- Display the score at the TOP RIGHT of the page

IMAGE REQUIREMENTS:
- Journal-style aesthetic
- Warm, friendly, travel diary look
- Include:
  - Korean food illustrations
  - Restaurant / street food atmosphere
  - Notebook or scrapbook layout
- Avoid text-heavy visuals (text should be readable but minimal)

OUTPUT:
- Generate ONE complete food journal image page
- Include the trust score visually on the image"""

    return full_prompt


def generate_food_journal(prompt):
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"]
        )
    )

    # 1. 응답에 후보(candidates)가 있고, 내용(content)이 있는지 먼저 확인
    if not response.candidates or not response.candidates[0].content:
        # 안전 필터 등으로 인해 차단된 경우
        print("경고: 모델이 이미지를 생성하지 못했습니다. (안전 필터 혹은 정책 위반 가능성)")

        # 차단 이유 확인 (디버깅용)
        if response.candidates and response.candidates[0].finish_reason:
            print(f"중단 이유: {response.candidates[0].finish_reason}")

        return None  # 에러 대신 None을 반환하여 프로그램이 멈추지 않게 함

    # 2. 내용이 있을 때만 parts에 접근
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return part.inline_data.data

    return None

if __name__ == "__main__":
    user_data = {
        "Allergy": ["egg"],
        "Other": ["spicy food"]
    }

    review_data = {
        "member_id": 12,
        "reviews": [
            {
                "review_id": 301,
                "rating": 5,
                "content": "I have an egg allergy and this app guided me very well. I enjoyed galbi jjim safely."
            },
            {
                "review_id": 302,
                "rating": 1,
                "content": "Staff reacted badly when I mentioned my allergy. I do not recommend this place."
            },
            {
                "review_id": 303,
                "rating": 5,
                "content": "Street food in Korea is amazing. This app helped me eat chicken skewers safely."
            }
        ]
    }

    prompt = build_prompt(user_data, review_data)
    image_bytes = generate_food_journal(prompt)

    # Save in the same directory
    output_filename = "food_journal_test1.png"
    with open(output_filename, "wb") as f:
        f.write(image_bytes)

    print(f"✅ Food journal image saved as: {output_filename}")
