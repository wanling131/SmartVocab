-- ============================================
-- SmartVocab 错题本表 - 数据库升级迁移脚本
-- ============================================

USE smartvocab;

-- --------------------------------------------
-- 错题本表 (mistake_book)
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS mistake_book (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    user_id INT NOT NULL COMMENT '用户ID',
    word_id INT NOT NULL COMMENT '词汇ID',
    user_answer TEXT DEFAULT NULL COMMENT '用户的错误答案',
    correct_answer TEXT DEFAULT NULL COMMENT '正确答案',
    mistake_count INT NOT NULL DEFAULT 1 COMMENT '错误次数',
    first_mistake_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次错误时间',
    last_mistake_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近错误时间',
    mastered TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已掌握(纠正后标记)',
    KEY idx_user (user_id),
    KEY idx_user_word (user_id, word_id),
    KEY idx_mistake_count (mistake_count),
    CONSTRAINT fk_mb_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_mb_word FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_word (user_id, word_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='错题本表';