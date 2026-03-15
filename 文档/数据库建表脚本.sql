-- ============================================
-- SmartVocab 智能词汇学习系统 - 数据库建表脚本
-- 对应论文 第4章 系统数据库设计
-- 共11张核心表：users, words, user_learning_records, learning_sessions,
--   recommendations, evaluation_papers, evaluation_paper_items, 
--   evaluation_results, level_gates, user_level_progress, user_learning_plans
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS smartvocab DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smartvocab;

-- --------------------------------------------
-- 表4-1 用户表 (users)
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
    student_no VARCHAR(30) DEFAULT NULL COMMENT '学号',
    real_name VARCHAR(50) DEFAULT NULL COMMENT '姓名',
    username VARCHAR(50) NOT NULL COMMENT '用户名',
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    model_filename VARCHAR(255) DEFAULT NULL COMMENT '用户专属深度学习模型文件名',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    last_login_at DATETIME DEFAULT NULL COMMENT '最后登录时间',
    UNIQUE KEY uk_username (username),
    KEY idx_student_no (student_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- --------------------------------------------
-- 表4-2 词汇表 (words)
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS words (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '词汇ID',
    word VARCHAR(100) NOT NULL COMMENT '单词',
    translation TEXT NOT NULL COMMENT '中文释义',
    definition_en TEXT DEFAULT NULL COMMENT '英文释义',
    phonetic VARCHAR(100) DEFAULT NULL COMMENT '音标',
    pos VARCHAR(20) DEFAULT NULL COMMENT '词性',
    example_sentence TEXT DEFAULT NULL COMMENT '例句',
    tag VARCHAR(200) DEFAULT NULL COMMENT '标签(CET4/CET6等)',
    frequency_rank INT DEFAULT NULL COMMENT '词频排名',
    cefr_standard CHAR(10) DEFAULT NULL COMMENT 'CEFR等级(A1-C2)',
    difficulty_level TINYINT NOT NULL DEFAULT 3 COMMENT '难度等级1-6',
    domain JSON DEFAULT NULL COMMENT '领域分布(口语/学术等)',
    dataset_type VARCHAR(50) DEFAULT NULL COMMENT '词库体系(cet4/toefl/ielts等)',
    KEY idx_difficulty (difficulty_level),
    KEY idx_cefr (cefr_standard),
    KEY idx_word (word),
    KEY idx_dataset_type (dataset_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='词汇表';

-- --------------------------------------------
-- 表4-9 闯关关卡表 (level_gates) - 需先创建，供 user_learning_records 引用
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
-- 表4-3 用户学习记录表 (user_learning_records)
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS user_learning_records (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    user_id INT NOT NULL COMMENT '用户ID',
    word_id INT NOT NULL COMMENT '词汇ID',
    level_gate_id INT DEFAULT NULL COMMENT '关卡ID(闯关模式)',
    first_learned_at DATETIME NOT NULL COMMENT '首次学习时间(如3月9日记忆的)',
    last_reviewed_at DATETIME NOT NULL COMMENT '最后复习时间',
    next_review_at DATETIME DEFAULT NULL COMMENT '下次复习时间(由记忆曲线计算,到期则入复习表)',
    mastery_level FLOAT NOT NULL DEFAULT 0.0 COMMENT '掌握程度(0.0-1.0)',
    review_count INT NOT NULL DEFAULT 0 COMMENT '复习次数(第几次复习)',
    is_mastered TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已掌握',
    KEY idx_user (user_id),
    UNIQUE KEY uk_user_word (user_id, word_id),
    KEY idx_last_reviewed (last_reviewed_at),
    KEY idx_next_review (next_review_at),
    KEY idx_level_gate (level_gate_id),
    CONSTRAINT fk_ulr_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_ulr_word FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE,
    CONSTRAINT fk_ulr_gate FOREIGN KEY (level_gate_id) REFERENCES level_gates(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户学习记录表';

-- --------------------------------------------
-- 表4-4 学习会话表 (learning_sessions)
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS learning_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '会话ID',
    user_id INT NOT NULL COMMENT '用户ID',
    session_type VARCHAR(20) NOT NULL COMMENT '会话类型(learning/review/evaluation)',
    session_data JSON NOT NULL COMMENT '会话数据',
    current_word_index INT NOT NULL DEFAULT 0 COMMENT '当前单词索引',
    total_words INT NOT NULL DEFAULT 0 COMMENT '总单词数',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_active TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否活跃',
    KEY idx_user_session (user_id, session_type, is_active),
    CONSTRAINT fk_ls_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学习会话表';

-- --------------------------------------------
-- 表4-5 推荐记录表 (recommendations)
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    user_id INT NOT NULL COMMENT '用户ID',
    word_id INT NOT NULL COMMENT '词汇ID',
    recommendation_score FLOAT NOT NULL DEFAULT 0.5 COMMENT '推荐分数',
    recommendation_type VARCHAR(50) NOT NULL DEFAULT 'mixed' COMMENT '推荐算法类型',
    reason VARCHAR(500) DEFAULT NULL COMMENT '推荐理由',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_user (user_id),
    CONSTRAINT fk_rec_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_rec_word FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推荐记录表';

-- --------------------------------------------
-- 表4-6 评测试卷表 (evaluation_papers)
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS evaluation_papers (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '试卷ID',
    user_id INT NOT NULL COMMENT '用户ID',
    paper_type VARCHAR(30) NOT NULL COMMENT '试卷类型(level_test/review_test等)',
    question_count INT NOT NULL COMMENT '题目数量',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_user (user_id),
    CONSTRAINT fk_ep_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评测试卷表';

-- --------------------------------------------
-- 表4-7 试卷题目表 (evaluation_paper_items)
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS evaluation_paper_items (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    paper_id INT NOT NULL COMMENT '试卷ID',
    word_id INT NOT NULL COMMENT '词汇ID',
    question_type VARCHAR(30) NOT NULL COMMENT '题型(choice/translation/spelling)',
    item_order INT NOT NULL COMMENT '题目序号',
    KEY idx_paper (paper_id),
    CONSTRAINT fk_epi_paper FOREIGN KEY (paper_id) REFERENCES evaluation_papers(id) ON DELETE CASCADE,
    CONSTRAINT fk_epi_word FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='试卷题目表';

-- --------------------------------------------
-- 表4-8 评测结果表 (evaluation_results)
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
-- 表4-10 用户关卡进度表 (user_level_progress)
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
-- 表4-11 用户学习计划表 (user_learning_plans)
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
    CONSTRAINT fk_ulp_user_plan FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户学习计划表(计划词库/每日单词数等)';
