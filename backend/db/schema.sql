-- db/schema.sql
-- MySQL 8.x 기준 스키마 (ERD 기반)
-- docker-compose.yml 의 MYSQL_DATABASE 값(app_db)과 일치하도록 작성

CREATE DATABASE IF NOT EXISTS app_db
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE app_db;

-- 1) member
CREATE TABLE IF NOT EXISTS member (
  member_id        INT AUTO_INCREMENT PRIMARY KEY,
  email            VARCHAR(255) NOT NULL,
  password         VARCHAR(255) NOT NULL,
  nickname         VARCHAR(50)  NOT NULL,
  gender           VARCHAR(10)  NULL,
  country          VARCHAR(50)  NULL,
  create_member    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  modify_member    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_member_email (email)
) ENGINE=InnoDB;

-- 2) restriction_category
CREATE TABLE IF NOT EXISTS restriction_category (
  category_id      INT AUTO_INCREMENT PRIMARY KEY,
  category_label   VARCHAR(50) NOT NULL,
  category_code    VARCHAR(50) NOT NULL,
  UNIQUE KEY uq_category_code (category_code)
) ENGINE=InnoDB;

-- 3) restriction_items
CREATE TABLE IF NOT EXISTS restriction_items (
  item_id          INT AUTO_INCREMENT PRIMARY KEY,
  item_label_ko       VARCHAR(100) NOT NULL,
  item_label_en        VARCHAR(100) NOT NULL,
  category_id      INT NOT NULL,
  UNIQUE KEY uq_item_label_en (item_label_en),
  KEY idx_items_category_id (category_id),
  CONSTRAINT fk_items_category
    FOREIGN KEY (category_id)
    REFERENCES restriction_category(category_id)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
) ENGINE=InnoDB;

-- 4) member_restrictions (member <-> restriction_items)
CREATE TABLE IF NOT EXISTS member_restrictions (
  member_restrictions_id INT AUTO_INCREMENT PRIMARY KEY,
  item_id                INT NOT NULL,
  member_id              INT NOT NULL,
  UNIQUE KEY uq_member_item (member_id, item_id),
  KEY idx_mr_item_id (item_id),
  KEY idx_mr_member_id (member_id),
  CONSTRAINT fk_mr_item
    FOREIGN KEY (item_id)
    REFERENCES restriction_items(item_id)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT fk_mr_member
    FOREIGN KEY (member_id)
    REFERENCES member(member_id)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB;

-- 5) review
CREATE TABLE IF NOT EXISTS review (
  review_id        INT AUTO_INCREMENT PRIMARY KEY,
  review_title     TEXT NOT NULL,
  review_content   TEXT NOT NULL,
  rating           INT NULL,
  location         VARCHAR(100) NULL,
  create_review    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  member_id        INT NOT NULL,
  KEY idx_review_member_id (member_id),
  CONSTRAINT fk_review_member
    FOREIGN KEY (member_id)
    REFERENCES member(member_id)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB;

-- 6) community
CREATE TABLE IF NOT EXISTS community (
  community_id     INT AUTO_INCREMENT PRIMARY KEY,
  field            TEXT NULL,
  member_id        INT NOT NULL,
  KEY idx_community_member_id (member_id),
  CONSTRAINT fk_community_member
    FOREIGN KEY (member_id)
    REFERENCES member(member_id)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB;

-- (선택) rating 범위 체크: MySQL 8에서는 동작하나, 환경에 따라 앱 레벨 검증도 권장
-- ALTER TABLE review
--   ADD CONSTRAINT chk_review_rating CHECK (rating IS NULL OR (rating BETWEEN 1 AND 5));
