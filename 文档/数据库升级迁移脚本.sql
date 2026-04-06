-- ============================================
-- SmartVocab 数据库升级迁移脚本
-- 用于在现有表基础上，升级为11张表完整结构（与 数据库建表脚本.sql 一致）
-- 执行前请先备份数据库！
-- ============================================

USE smartvocab;

-- --------------------------------------------
-- 1. 修改 users 表：新增学号、姓名、最后登录时间
-- 若某列已存在会报错，可忽略该条继续执行
-- --------------------------------------------
ALTER TABLE users ADD COLUMN student_no VARCHAR(30) DEFAULT NULL COMMENT '学号' AFTER id;
ALTER TABLE users ADD COLUMN real_name VARCHAR(50) DEFAULT NULL COMMENT '姓名' AFTER student_no;
ALTER TABLE users ADD COLUMN last_login_at DATETIME DEFAULT NULL COMMENT '最后登录时间' AFTER created_at;
-- ALTER TABLE users ADD INDEX idx_student_no (student_no);  -- 若已存在可注释

-- --------------------------------------------
-- 2. 修改 words 表：新增英文释义、例句、词库体系
-- --------------------------------------------
ALTER TABLE words ADD COLUMN definition_en TEXT DEFAULT NULL COMMENT '英文释义' AFTER translation;
ALTER TABLE words ADD COLUMN example_sentence TEXT DEFAULT NULL COMMENT '例句' AFTER pos;
ALTER TABLE words ADD COLUMN dataset_type VARCHAR(50) DEFAULT NULL COMMENT '词库体系' AFTER domain;
-- ALTER TABLE words ADD INDEX idx_dataset_type (dataset_type);  -- 若已存在可注释

-- --------------------------------------------
-- 3. 创建 level_gates 表（需先于 user_learning_records 引用）
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS level_gates (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '关卡ID',
    gate_order INT NOT NULL COMMENT '关卡序号',
    gate_name VARCHAR(100) NOT NULL COMMENT '关卡名称',
    difficulty_level TINYINT NOT NULL COMMENT '难度等级1-6',
    word_count INT NOT NULL COMMENT '词汇数量',
    KEY idx_gate_order (gate_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='闯关关卡表';

-- --------------------------------------------
-- 4. 修改 user_learning_records 表：新增关卡ID
-- --------------------------------------------
ALTER TABLE user_learning_records ADD COLUMN level_gate_id INT DEFAULT NULL COMMENT '关卡ID' AFTER word_id;
-- 添加外键（若已存在 fk_ulr_gate 可注释）
-- ALTER TABLE user_learning_records ADD CONSTRAINT fk_ulr_gate 
--     FOREIGN KEY (level_gate_id) REFERENCES level_gates(id) ON DELETE SET NULL;

-- --------------------------------------------
-- 4b. 修改 user_learning_records 表：新增首次学习时间、下次复习时间（记忆曲线与复习表）
-- --------------------------------------------
ALTER TABLE user_learning_records ADD COLUMN first_learned_at DATETIME NULL COMMENT '首次学习时间' AFTER level_gate_id;
ALTER TABLE user_learning_records ADD COLUMN next_review_at DATETIME NULL COMMENT '下次复习时间(记忆曲线计算)' AFTER last_reviewed_at;
-- 已有数据：将首次学习时间设为最后复习时间
UPDATE user_learning_records SET first_learned_at = last_reviewed_at WHERE first_learned_at IS NULL;
ALTER TABLE user_learning_records MODIFY COLUMN first_learned_at DATETIME NOT NULL COMMENT '首次学习时间';
ALTER TABLE user_learning_records ADD INDEX idx_next_review (next_review_at);

-- --------------------------------------------
-- 5. 创建 evaluation_papers 表
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS evaluation_papers (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '试卷ID',
    user_id INT NOT NULL COMMENT '用户ID',
    paper_type VARCHAR(30) NOT NULL COMMENT '试卷类型',
    question_count INT NOT NULL COMMENT '题目数量',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_user (user_id),
    CONSTRAINT fk_ep_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评测试卷表';

-- --------------------------------------------
-- 6. 创建 evaluation_paper_items 表
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS evaluation_paper_items (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    paper_id INT NOT NULL COMMENT '试卷ID',
    word_id INT NOT NULL COMMENT '词汇ID',
    question_type VARCHAR(30) NOT NULL COMMENT '题型',
    item_order INT NOT NULL COMMENT '题目序号',
    KEY idx_paper (paper_id),
    CONSTRAINT fk_epi_paper FOREIGN KEY (paper_id) REFERENCES evaluation_papers(id) ON DELETE CASCADE,
    CONSTRAINT fk_epi_word FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='试卷题目表';

-- --------------------------------------------
-- 7. 创建 evaluation_results 表
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS evaluation_results (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    user_id INT NOT NULL COMMENT '用户ID',
    paper_id INT NOT NULL COMMENT '试卷ID',
    score FLOAT NOT NULL COMMENT '得分',
    correct_count INT NOT NULL COMMENT '正确题数',
    total_count INT NOT NULL COMMENT '总题数',
    duration_seconds INT DEFAULT NULL COMMENT '答题耗时(秒)',
    assessed_level VARCHAR(20) DEFAULT NULL COMMENT '评测水平',
    submitted_at DATETIME NOT NULL COMMENT '提交时间',
    KEY idx_user (user_id),
    CONSTRAINT fk_er_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_er_paper FOREIGN KEY (paper_id) REFERENCES evaluation_papers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评测结果表';

-- --------------------------------------------
-- 8. 创建 user_level_progress 表
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS user_level_progress (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    user_id INT NOT NULL COMMENT '用户ID',
    level_gate_id INT NOT NULL COMMENT '关卡ID',
    mastered_count INT NOT NULL DEFAULT 0 COMMENT '已掌握数',
    is_unlocked TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否解锁',
    is_completed TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否完成',
    completed_at DATETIME DEFAULT NULL COMMENT '完成时间',
    UNIQUE KEY uk_user_gate (user_id, level_gate_id),
    CONSTRAINT fk_ulp_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_ulp_gate FOREIGN KEY (level_gate_id) REFERENCES level_gates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户关卡进度表';

-- --------------------------------------------
-- 9. 创建 user_learning_plans 表（用户学习计划表）
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS user_learning_plans (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '计划ID',
    user_id INT NOT NULL COMMENT '用户ID',
    plan_name VARCHAR(100) DEFAULT NULL COMMENT '计划名称',
    dataset_type VARCHAR(50) NOT NULL COMMENT '计划词库(cet4/cet6/toefl/ielts等)',
    daily_new_count INT NOT NULL DEFAULT 20 COMMENT '每日新学单词数',
    daily_review_count INT NOT NULL DEFAULT 20 COMMENT '每日复习单词数',
    start_date DATE DEFAULT NULL COMMENT '计划开始日期',
    end_date DATE DEFAULT NULL COMMENT '计划结束日期',
    is_active TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否生效',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    KEY idx_user (user_id),
    KEY idx_user_active (user_id, is_active),
    CONSTRAINT fk_ulplan_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户学习计划表(计划词库/每日单词数等)';

-- --------------------------------------------
-- 10. 创建 user_favorite_words 表（用户收藏单词）
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS user_favorite_words (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '收藏ID',
    user_id INT NOT NULL COMMENT '用户ID',
    word_id INT NOT NULL COMMENT '词汇ID',
    note VARCHAR(500) DEFAULT NULL COMMENT '收藏备注',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '收藏时间',
    updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_user_word (user_id, word_id),
    KEY idx_user (user_id),
    KEY idx_created (created_at),
    CONSTRAINT fk_fav_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_fav_word FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户收藏单词表';
