-- 成就系统表
CREATE TABLE IF NOT EXISTS achievements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    achievement_key VARCHAR(50) NOT NULL UNIQUE COMMENT '成就唯一标识',
    achievement_name VARCHAR(100) NOT NULL COMMENT '成就名称',
    description VARCHAR(500) DEFAULT NULL COMMENT '成就描述',
    icon VARCHAR(50) DEFAULT 'trophy' COMMENT '图标',
    category VARCHAR(30) DEFAULT 'learning' COMMENT '分类: learning/streak/score/special',
    threshold INT DEFAULT 1 COMMENT '达成阈值',
    points INT DEFAULT 10 COMMENT '成就积分',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成就定义表';

-- 用户成就记录表
CREATE TABLE IF NOT EXISTS user_achievements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用户ID',
    achievement_id INT NOT NULL COMMENT '成就ID',
    achieved_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '达成时间',
    progress INT DEFAULT 1 COMMENT '进度(用于追踪部分完成)',
    UNIQUE KEY uk_user_achievement (user_id, achievement_id),
    CONSTRAINT fk_ua_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_ua_achievement FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户成就记录表';

-- 插入默认成就
INSERT IGNORE INTO achievements (achievement_key, achievement_name, description, icon, category, threshold, points) VALUES
-- 学习数量成就
('first_word', '初学者', '学习第一个单词', 'seed', 'learning', 1, 10),
('words_10', '起步者', '学习10个单词', 'sprout', 'learning', 10, 20),
('words_50', '入门者', '学习50个单词', 'leaf', 'learning', 50, 50),
('words_100', '进阶者', '学习100个单词', 'tree', 'learning', 100, 100),
('words_500', '达人', '学习500个单词', 'forest', 'learning', 500, 200),
('words_1000', '词汇大师', '学习1000个单词', 'crown', 'learning', 1000, 500),

-- 连续学习成就
('streak_3', '坚持3天', '连续学习3天', 'fire', 'streak', 3, 30),
('streak_7', '坚持一周', '连续学习7天', 'flame', 'streak', 7, 50),
('streak_30', '坚持一月', '连续学习30天', 'inferno', 'streak', 30, 200),
('streak_100', '百日坚持', '连续学习100天', 'phoenix', 'streak', 100, 500),

-- 正确率成就
('accuracy_80', '精准学习者', '单次正确率达80%', 'target', 'score', 80, 30),
('accuracy_90', '高准确率', '单次正确率达90%', 'bullseye', 'score', 90, 50),
('accuracy_100', '完美表现', '单次正确率达100%', 'star', 'score', 100, 100),

-- 特殊成就
('first_review', '温故知新', '完成第一次复习', 'refresh', 'special', 1, 20),
('first_test', '初试锋芒', '完成第一次等级测试', 'clipboard', 'special', 1, 20),
('first_plan', '规划者', '创建第一个学习计划', 'calendar', 'special', 1, 20),
('level_complete', '闯关达人', '完成一个关卡', 'flag', 'special', 1, 30),
('night_owl', '夜猫子', '在深夜学习(23:00-5:00)', 'moon', 'special', 1, 30),
('early_bird', '早起鸟', '在早晨学习(5:00-7:00)', 'sun', 'special', 1, 30);
