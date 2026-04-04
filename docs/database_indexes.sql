-- SmartVocab 性能优化 - 数据库索引建议
-- 执行以下 SQL 语句来创建推荐的索引

-- 1. 用户学习记录表索引
-- 用于快速查询用户的学习记录
CREATE INDEX idx_user_learning_records_user_id ON user_learning_records(user_id);
CREATE INDEX idx_user_learning_records_user_word ON user_learning_records(user_id, word_id);
CREATE INDEX idx_user_learning_records_next_review ON user_learning_records(user_id, next_review_at);
CREATE INDEX idx_user_learning_records_last_reviewed ON user_learning_records(last_reviewed_at);

-- 2. 单词表索引
-- 用于按难度和词库类型快速筛选
CREATE INDEX idx_words_difficulty ON words(difficulty_level);
CREATE INDEX idx_words_dataset ON words(dataset_type);
CREATE INDEX idx_words_diff_dataset ON words(difficulty_level, dataset_type);
CREATE INDEX idx_words_frequency ON words(frequency_rank);

-- 3. 学习会话表索引
-- 用于快速查询用户的活跃会话
CREATE INDEX idx_learning_sessions_user ON learning_sessions(user_id);
CREATE INDEX idx_learning_sessions_active ON learning_sessions(user_id, is_active, session_type);
CREATE INDEX idx_learning_sessions_created ON learning_sessions(created_at);

-- 4. 推荐记录表索引
-- 用于快速查询用户的推荐历史
CREATE INDEX idx_recommendations_user ON recommendations(user_id);
CREATE INDEX idx_recommendations_user_created ON recommendations(user_id, created_at);

-- 5. 评测结果表索引
-- 用于快速查询用户的评测历史
CREATE INDEX idx_evaluation_results_user ON evaluation_results(user_id);
CREATE INDEX idx_evaluation_results_created ON evaluation_results(created_at);

-- 6. 用户等级进度表索引
CREATE INDEX idx_user_level_progress_user ON user_level_progress(user_id);
CREATE INDEX idx_user_level_progress_gate ON user_level_progress(user_id, level_gate_id);

-- 7. 每日学习统计表索引（如果存在）
CREATE INDEX idx_learning_reports_user_date ON learning_reports(user_id, report_date);

-- 8. 成就记录表索引
CREATE INDEX idx_user_achievements_user ON user_achievements(user_id);
CREATE INDEX idx_user_achievements_type ON user_achievements(user_id, achievement_type);

-- 查看现有索引
-- SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = 'smartvocab';

-- 分析表统计信息（优化查询计划）
ANALYZE TABLE user_learning_records;
ANALYZE TABLE words;
ANALYZE TABLE learning_sessions;
ANALYZE TABLE recommendations;
ANALYZE TABLE evaluation_results;
ANALYZE TABLE user_level_progress;
