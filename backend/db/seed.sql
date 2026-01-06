-- backend/db/seed.sql
-- 초기 데이터(샘플). 필요에 맞게 수정/확장하세요.
-- idempotent하게 동작하도록 UNIQUE KEY 기반 ON DUPLICATE KEY UPDATE 사용

-- (중요) 세션 문자셋/콜레이션을 확실히 고정
SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- (중요) docker-compose.yml의 MYSQL_DATABASE(app_db)와 반드시 일치
USE app_db;

-- 카테고리(예시)
INSERT INTO restriction_category (category_label, category_code)
VALUES
  ('알레르겐', 'ALLERGEN'),
  ('식이제한', 'DIET')
ON DUPLICATE KEY UPDATE
  category_label = VALUES(category_label);

-- category_id 조회를 위해 변수로 담기
SET @CAT_ALLERGEN := (SELECT category_id FROM restriction_category WHERE category_code='ALLERGEN' LIMIT 1);
SET @CAT_DIET     := (SELECT category_id FROM restriction_category WHERE category_code='DIET' LIMIT 1);

-- 알레르겐 아이템(예시: EU14 일부 + 흔한 항목)
INSERT INTO restriction_items (item_label_ko, item_label_en, category_id)
VALUES
  ('우유(우유)',                         'ALG_MILK',            @CAT_ALLERGEN),
  ('달걀(계란)',                         'ALG_EGGS',            @CAT_ALLERGEN),
  ('대두(콩)',                           'ALG_SOY',             @CAT_ALLERGEN),
  ('땅콩(땅콩)',                         'ALG_PEANUTS',         @CAT_ALLERGEN),
  ('견과류(아몬드, 호두, 캐슈넛)',        'ALG_TREE_NUTS',       @CAT_ALLERGEN),
  ('밀/글루텐(밀, 보리, 호밀)',           'ALG_CEREALS_GLUTEN',  @CAT_ALLERGEN),
  ('생선(고등어, 갈치, 꽁치)',            'ALG_FISH',            @CAT_ALLERGEN),
  ('갑각류(새우, 게, 랍스터)',            'ALG_CRUSTACEANS',     @CAT_ALLERGEN),
  ('연체동물(오징어, 문어, 조개)',         'ALG_MOLLUSCS',        @CAT_ALLERGEN),
  ('참깨(참깨)',                         'ALG_SESAME',          @CAT_ALLERGEN),
  ('겨자(머스터드)',                      'ALG_MUSTARD',         @CAT_ALLERGEN),
  ('셀러리(셀러리)',                      'ALG_CELERY',          @CAT_ALLERGEN),
  ('아황산염(와인, 건과일, 식초)',         'ALG_SULPHITES',       @CAT_ALLERGEN),
  ('루핀(루핀콩)',                        'ALG_LUPIN',           @CAT_ALLERGEN)
ON DUPLICATE KEY UPDATE
  item_label_ko = VALUES(item_label_ko),
  category_id   = VALUES(category_id);

-- 식이제한 아이템(예시)
INSERT INTO restriction_items (item_label_ko, item_label_en, category_id)
VALUES
  ('비건',        'DIET_VEGAN',       @CAT_DIET),
  ('베지테리언',  'DIET_VEGETARIAN',  @CAT_DIET),
  ('할랄',        'DIET_HALAL',       @CAT_DIET)
ON DUPLICATE KEY UPDATE
  item_label_ko = VALUES(item_label_ko),
  category_id = VALUES(category_id);
