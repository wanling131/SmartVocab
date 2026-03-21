"""
词汇学习核心模块
负责词汇学习、测试、练习等核心功能
"""

import logging
import random
from datetime import datetime

from tools.words_crud import WordsCRUD
from tools.learning_records_crud import LearningRecordsCRUD
from tools.learning_sessions_crud import LearningSessionsCRUD
from core.learning.learning_record_manager import LearningRecordManager
from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager
from core.recommendation.recommendation_engine import RecommendationEngine
from config import LEARNING_PARAMS

logger = logging.getLogger(__name__)

class VocabularyLearningManager:
    """
    词汇学习管理类
    负责词汇学习的核心功能：学习、测试、练习、记忆等
    """
    
    def __init__(self):
        """
        初始化词汇学习管理器
        """
        self.words_crud = WordsCRUD()
        self.learning_records_crud = LearningRecordsCRUD()
        self.learning_sessions_crud = LearningSessionsCRUD()
        self.learning_record_manager = LearningRecordManager()
        self.forgetting_curve_manager = ForgettingCurveManager()
        self.recommendation_engine = RecommendationEngine()
    
    def start_learning_session(self, user_id, difficulty_level=None, word_count=LEARNING_PARAMS["default_word_count"], question_type='mixed'):
        """
        开始学习会话
        
        Args:
            user_id (int): 用户ID
            difficulty_level (int): 难度等级 (1-6)，如果为None则自动选择
            word_count (int): 学习单词数量
            question_type (str): 题型设置 ('mixed', 'choice', 'translation')
            
        Returns:
            dict: 学习会话信息
        """
        # 获取推荐单词
        if difficulty_level:
            recommendations = self._get_words_by_difficulty(difficulty_level, word_count)
        else:
            recommendations = self.recommendation_engine.get_recommendations(user_id, word_count)
        
        # 创建学习会话
        session_info = {
            "user_id": user_id,
            "words": recommendations,
            "current_word_index": 0,
            "correct_count": 0,
            "total_count": len(recommendations),
            "start_time": datetime.now(),
            "session_type": "learning",
            "question_type": question_type,  # 添加题型设置
            "learning_stage": "choice" if question_type in ['mixed', 'choice'] else "translation",  # 根据题型设置初始阶段
            "word_stages": {}  # 记录每个单词的学习阶段
        }
        
        # 保存会话到数据库
        session_id = self.learning_sessions_crud.create(user_id, session_info, "learning")
        if session_id:
            session_info["session_id"] = session_id
            logger.debug("学习会话已保存，ID=%s", session_id)
        else:
            logger.warning("学习会话保存失败")
        
        return {
            "success": True,
            "message": "学习会话开始",
            "session_info": session_info
        }
        
    def get_active_session(self, user_id, session_type="learning"):
        """
        获取用户的活跃学习会话
        
        Args:
            user_id (int): 用户ID
            session_type (str): 会话类型
            
        Returns:
            dict: 活跃会话信息，如果没有则返回None
        """
        logger.debug("获取活跃会话 - user_id=%s, session_type=%s", user_id, session_type)
        
        session_record = self.learning_sessions_crud.get_active_session(user_id, session_type)
        
        if session_record:
            session_info = session_record['session_data']
            session_info['session_id'] = session_record['id']
            logger.debug("找到活跃会话，ID=%s", session_record['id'])
            return {
                "success": True,
                "message": "找到活跃会话",
                "session_info": session_info
            }
        else:
            logger.debug("未找到活跃会话")
            return {
                "success": False,
                "message": "没有活跃的学习会话"
            }
    
    def finish_session(self, session_id):
        """
        完成学习会话
        
        Args:
            session_id (int): 会话ID
            
        Returns:
            bool: 操作是否成功
        """
        logger.debug("完成学习会话 - session_id=%s", session_id)
        
        success = self.learning_sessions_crud.deactivate_session(session_id)
        if success:
            logger.debug("会话已停用，ID=%s", session_id)
        else:
            logger.warning("会话停用失败，ID=%s", session_id)
        
        return success
    
    def get_current_word(self, session_info):
        """
        获取当前学习的单词
        
        Args:
            session_info (dict): 学习会话信息
            
        Returns:
            dict: 当前单词信息
        """
        if session_info["current_word_index"] >= len(session_info["words"]):
            return None
        
        word_data = session_info["words"][session_info["current_word_index"]]
        word_id = word_data["id"]
        
        # 获取单词详细信息
        word_info = self.words_crud.read(word_id)
        
        # 获取会话的题型设置
        session_question_type = session_info.get("question_type", "mixed")
        
        # 获取当前单词的学习阶段
        word_stages = session_info.get("word_stages", {})
        current_stage = word_stages.get(str(word_id), "choice")
        
        # 根据题型设置决定题目类型
        if session_question_type == "choice":
            # 仅选择题模式
            return self._generate_choice_question(word_info)
        elif session_question_type == "spelling":
            # 仅拼写题模式
            return self._generate_spelling_question(word_info)
        elif session_question_type == "translation":
            # 仅翻译题模式
            return {
                "word_id": word_info["id"],
                "word": word_info["word"],
                "translation": word_info["translation"],
                "phonetic": word_info["phonetic"],
                "pos": word_info["pos"],
                "difficulty_level": word_info["difficulty_level"],
                "cefr_standard": word_info["cefr_standard"],
                "question_type": "translation",
                "learning_stage": "translation"
            }
        else:
            # 混合模式：根据当前阶段决定
            if current_stage == "choice":
                return self._generate_choice_question(word_info)
            elif current_stage == "spelling":
                return self._generate_spelling_question(word_info)
            else:
                return {
                    "word_id": word_info["id"],
                    "word": word_info["word"],
                    "translation": word_info["translation"],
                    "phonetic": word_info["phonetic"],
                    "pos": word_info["pos"],
                    "difficulty_level": word_info["difficulty_level"],
                    "cefr_standard": word_info["cefr_standard"],
                    "question_type": "translation",
                    "learning_stage": "translation"
                }
    
    def submit_answer(self, user_id, word_id, user_answer, correct_answer, response_time, question_type="translation", mastery_override=None, session_info=None):
        """
        提交答案
        
        Args:
            user_id (int): 用户ID
            word_id (int): 单词ID
            user_answer (str): 用户答案
            correct_answer (str): 正确答案
            response_time (float): 响应时间（秒）
            question_type (str): 题目类型
            mastery_override (float): 强制设置掌握程度
            session_info (dict): 学习会话信息
            
        Returns:
            dict: 答题结果
        """
        try:
            logger.debug(
                "提交答案 - user_id=%s, word_id=%s, user_answer=%r, correct_answer=%r, question_type=%s",
                user_id, word_id, user_answer, correct_answer, question_type)
            
            # 判断答案是否正确
            is_correct = self._check_answer(user_answer, correct_answer, question_type)
            logger.debug("答案检查结果 - is_correct=%s", is_correct)
            
            # 获取或创建学习记录
            existing_record = self.learning_record_manager.get_word_learning_record(user_id, word_id)
            logger.debug("现有记录 - %s", existing_record)
            
            if existing_record:
                # 更新现有记录
                result = self.learning_record_manager.update_mastery_level(
                    existing_record["id"], 
                    existing_record["mastery_level"], 
                    is_correct,
                    question_type
                )
                logger.debug("更新记录结果 - %s", result)
            else:
                # 创建新记录
                if mastery_override is not None:
                    mastery_level = mastery_override  # 优先使用指定值
                else:
                    # 根据题目类型设置初始掌握程度
                    if is_correct:
                        if question_type == "choice":
                            mastery_level = 0.2
                        elif question_type == "translation":
                            mastery_level = 0.3
                        elif question_type == "spelling":
                            mastery_level = 0.4
                        else:
                            mastery_level = 0.2  # 默认值
                    else:
                        mastery_level = 0.0
                result = self.learning_record_manager.create_learning_record(
                    user_id=user_id,
                    word_id=word_id,
                    mastery_level=mastery_level,
                    last_reviewed_at=datetime.now(),
                    review_count=1,
                    is_mastered=mastery_level >= 0.8
                )
                logger.debug("创建学习记录结果: %s", result)
            
            # 生成反馈消息
            if question_type == "choice":
                message = "选择正确！" if is_correct else f"选择错误，正确答案是：{correct_answer}"
            elif question_type == "spelling":
                message = "拼写正确！" if is_correct else f"拼写错误，正确答案是：{correct_answer}"
            else:
                message = "翻译正确！" if is_correct else f"翻译错误，正确答案是：{correct_answer}"
            
            # 处理学习阶段切换（仅在混合模式下）
            updated_session_info = None
            if session_info and question_type == "choice" and session_info.get("question_type") == "mixed":
                # 混合模式下，选择题完成后切换到翻译题阶段
                word_stages = session_info.get("word_stages", {})
                word_stages[str(word_id)] = "translation"
                session_info["word_stages"] = word_stages
                updated_session_info = session_info
                logger.debug("学习阶段切换 - word_id=%s, stage=translation", word_id)
                
                # 更新数据库中的会话信息
                session_id = session_info.get("session_id")
                if session_id:
                    success = self.learning_sessions_crud.update(session_id, session_data=session_info)
                    if success:
                        logger.debug("会话信息已更新到数据库，session_id=%s", session_id)
                    else:
                        logger.warning("会话信息更新失败，session_id=%s", session_id)
            
            return {
                "success": True,
                "is_correct": is_correct,
                "correct_answer": correct_answer,
                "mastery_level": result.get("new_mastery_level", 0.0),
                "is_mastered": result.get("is_mastered", False),
                "message": message,
                "question_type": question_type,
                "session_info": updated_session_info
            }
        except Exception as e:
            logger.exception("提交答案异常: %s", e)
            return {
                "success": False,
                "message": f"提交答案失败: {str(e)}"
            }
    
    def generate_test_questions(self, user_id, word_count=LEARNING_PARAMS["default_test_word_count"], question_types=None):
        """
        生成测试题目
        
        Args:
            user_id (int): 用户ID
            word_count (int): 题目数量
            question_types (list): 题目类型列表
            
        Returns:
            list: 测试题目列表
        """
        if question_types is None:
            question_types = ["translation", "multiple_choice", "spelling"]
        
        # 获取需要测试的单词
        words = self.recommendation_engine.get_recommendations(user_id, word_count)
        
        questions = []
        for word_data in words:
            word_info = self.words_crud.read(word_data["id"])
            question_type = random.choice(question_types)
            
            if question_type == "translation":
                question = self._generate_translation_question(word_info)
            elif question_type == "multiple_choice":
                question = self._generate_multiple_choice_question(word_info)
            elif question_type == "spelling":
                question = self._generate_spelling_question(word_info)
            else:
                question = self._generate_translation_question(word_info)
            
            questions.append(question)
        
        return questions
    
    def get_review_words(self, user_id, limit=LEARNING_PARAMS["default_review_limit"], offset=0):
        """
        获取需要复习的单词（支持轮播）
        
        Args:
            user_id (int): 用户ID
            limit (int): 单词数量限制，默认20个
            offset (int): 偏移量，用于轮播
            
        Returns:
            list: 需要复习的单词列表
        """
        return self.forgetting_curve_manager.get_review_words(user_id, limit, offset)
    
    def start_review_session(self, user_id, word_count=LEARNING_PARAMS["default_word_count"]):
        """
        开始复习会话
        
        Args:
            user_id (int): 用户ID
            word_count (int): 单词数量
            
        Returns:
            dict: 复习会话结果
        """
        try:
            # 获取复习单词
            review_words = self.get_review_words(user_id, word_count)
            
            logger.debug(
                "获取复习单词: user_id=%s, count=%s",
                user_id,
                len(review_words),
            )
            
            if not review_words:
                # 如果没有需要复习的单词，获取最近学习但未完全掌握的单词
                logger.debug("没有需要复习的单词，获取最近学习的单词")
                all_records = self.learning_record_manager.get_user_learning_records(user_id, limit=1000)
                
                # 筛选未完全掌握的单词
                learning_records = [r for r in all_records if r['mastery_level'] < 1.0]
                
                if learning_records:
                    # 按最后复习时间排序，最近学习的优先
                    learning_records.sort(key=lambda x: x['last_reviewed_at'] or datetime.min, reverse=True)
                    review_words = learning_records[:word_count]
                    logger.debug("获取最近学习的单词 - 找到%s个", len(review_words))
                else:
                    logger.debug("没有找到任何学习记录")
                    return {
                        "success": False,
                        "message": "暂无学习记录，请先学习一些单词"
                    }
            
            # 获取单词详细信息
            word_details = []
            for record in review_words:
                word_info = self.words_crud.read(record["word_id"])
                if word_info:
                    word_details.append({
                        "id": word_info["id"],
                        "word": word_info["word"],
                        "translation": word_info["translation"],
                        "phonetic": word_info["phonetic"],
                        "pos": word_info["pos"],
                        "difficulty_level": word_info["difficulty_level"],
                        "cefr_standard": word_info["cefr_standard"],
                        "mastery_level": record["mastery_level"],
                        "last_reviewed": record["last_reviewed_at"]
                    })
            
            if not word_details:
                return {
                    "success": False,
                    "message": "暂无需要复习的单词"
                }
            
            # 创建复习会话信息
            session_info = {
                "user_id": user_id,
                "words": word_details,
                "current_word_index": 0,
                "total_count": len(word_details),
                "start_time": datetime.now(),
                "session_type": "review",
                "learning_stage": "translation"  # 复习模式直接使用翻译题
            }
            
            logger.debug("创建复习会话 - 单词数量: %s", len(word_details))
            
            return {
                "success": True,
                "message": "复习会话开始",
                "session_info": session_info
            }
            
        except Exception as e:
            logger.exception("开始复习会话失败: %s", e)
            return {
                "success": False,
                "message": f"开始复习会话失败: {str(e)}"
            }
    
    def get_learning_progress(self, user_id):
        """
        获取学习进度
        
        Args:
            user_id (int): 用户ID
            
        Returns:
            dict: 学习进度信息
        """
        return self.learning_record_manager.get_learning_progress(user_id)
    
    def get_learning_statistics(self, user_id, days=7):
        """
        获取学习统计
        
        Args:
            user_id (int): 用户ID
            days (int): 统计天数
            
        Returns:
            dict: 学习统计数据
        """
        return self.learning_record_manager.get_learning_statistics(user_id, days)
    
    def _get_words_by_difficulty(self, difficulty_level, word_count):
        """
        根据难度等级获取单词
        
        Args:
            difficulty_level (int): 难度等级
            word_count (int): 单词数量
            
        Returns:
            list: 单词列表
        """
        words = self.words_crud.get_by_difficulty(difficulty_level)
        if not words:
            return []
        return random.sample(words, min(word_count, len(words)))
    
    def _generate_choice_question(self, word_info):
        """
        生成选择题
        
        Args:
            word_info (dict): 单词信息
            
        Returns:
            dict: 选择题信息
        """
        # 获取正确答案（简化版，带词性）
        correct_translation = self._simplify_translation(word_info["translation"], word_info["pos"])
        
        # 生成3个错误选项（从数据库随机获取）
        wrong_options = self._generate_wrong_options(correct_translation, word_info["id"])
        
        # 合并所有选项并打乱顺序
        all_options = [correct_translation] + wrong_options
        random.shuffle(all_options)
        
        return {
            "word_id": word_info["id"],
            "word": word_info["word"],
            "phonetic": word_info["phonetic"],
            "pos": word_info["pos"],
            "difficulty_level": word_info["difficulty_level"],
            "cefr_standard": word_info["cefr_standard"],
            "question_type": "choice",
            "learning_stage": "choice",
            "question": f"请选择单词 '{word_info['word']}' 的正确中文释义：",
            "options": all_options,
            "correct_answer": correct_translation,
            "correct_index": all_options.index(correct_translation)
        }
    
    def _simplify_translation(self, translation, pos=None):
        """
        简化翻译，提取主要意思并添加词性
        
        Args:
            translation (str): 原始翻译
            pos (str): 词性
            
        Returns:
            str: 简化后的翻译（带词性）
        """
        if not translation:
            return ""
        
        # 提取第一个主要意思
        lines = translation.split('\n')
        if lines:
            first_line = lines[0].strip()
            # 提取第一个逗号前的内容
            if ',' in first_line:
                main_translation = first_line.split(',')[0].strip()
            else:
                main_translation = first_line
        else:
            main_translation = translation.strip()
        
        # 添加词性前缀
        if pos and not main_translation.startswith(pos + '.'):
            return f"{pos}. {main_translation}"
        
        return main_translation
    
    def _generate_wrong_options(self, correct_translation, current_word_id):
        """
        生成错误选项（从数据库随机获取）
        
        Args:
            correct_translation (str): 正确答案
            current_word_id (int): 当前单词ID
            
        Returns:
            list: 错误选项列表
        """
        try:
            # 从数据库获取随机单词作为错误选项
            all_words = self.words_crud.list_all(limit=500)  # 获取更多单词用于随机选择
            wrong_options = []
            
            # 随机选择3个不同的单词
            while len(wrong_options) < 3:
                random_word = random.choice(all_words)
                if random_word["id"] != current_word_id:  # 确保不是当前单词
                    # 简化翻译并添加词性
                    wrong_translation = self._simplify_translation(
                        random_word["translation"], 
                        random_word["pos"]
                    )
                    
                    # 确保不与正确答案重复，且不重复
                    if (wrong_translation != correct_translation and 
                        wrong_translation not in wrong_options and
                        wrong_translation.strip()):  # 确保不为空
                        wrong_options.append(wrong_translation)
            
            return wrong_options
            
        except Exception as e:
            logger.warning("生成错误选项失败: %s", e)
            # 备用方案：使用预定义选项
            return self._get_fallback_wrong_options(correct_translation)
    
    def _get_fallback_wrong_options(self, correct_translation):
        """
        备用错误选项生成方法
        
        Args:
            correct_translation (str): 正确答案
            
        Returns:
            list: 错误选项列表
        """
        fallback_options = [
            "n. 时间", "n. 地点", "n. 人物", "n. 事件", 
            "v. 开始", "v. 结束", "v. 过程", "v. 方法",
            "adj. 颜色", "adj. 形状", "adj. 大小", "adj. 数量"
        ]
        
        wrong_options = []
        while len(wrong_options) < 3:
            option = random.choice(fallback_options)
            if option != correct_translation and option not in wrong_options:
                wrong_options.append(option)
        
        return wrong_options
    
    def _check_answer(self, user_answer, correct_answer, question_type="translation"):
        """
        检查答案是否正确
        
        Args:
            user_answer (str): 用户答案
            correct_answer (str): 正确答案
            question_type (str): 题目类型
            
        Returns:
            bool: 是否正确
        """
        if question_type == "choice":
            # 选择题：直接比较选项
            return user_answer.strip() == correct_answer.strip()
        elif question_type == "spelling":
            # 拼写题：不区分大小写精确匹配
            return user_answer.strip().lower() == correct_answer.strip().lower()
        else:
            # 翻译题：智能匹配
            return self._smart_translation_match(user_answer, correct_answer)
    
    def _smart_translation_match(self, user_answer, correct_answer):
        """
        智能翻译匹配
        
        Args:
            user_answer (str): 用户答案
            correct_answer (str): 正确答案
            
        Returns:
            bool: 是否匹配
        """
        if not user_answer or not correct_answer:
            return False
        
        user_answer = user_answer.strip()
        correct_answer = correct_answer.strip()
        
        # 1. 完全匹配
        if user_answer == correct_answer:
            return True
        
        # 2. 提取主要意思进行匹配
        simplified_correct = self._simplify_translation(correct_answer)
        if user_answer == simplified_correct:
            return True
        
        # 3. 检查用户答案是否包含在正确答案中
        if user_answer in correct_answer:
            return True
        
        # 4. 检查正确答案的主要部分是否在用户答案中
        if simplified_correct in user_answer:
            return True
        
        return False
    
    def _generate_translation_question(self, word_info):
        """
        生成翻译题目
        
        Args:
            word_info (dict): 单词信息
            
        Returns:
            dict: 题目信息
        """
        return {
            "question_id": f"trans_{word_info['id']}",
            "word_id": word_info["id"],
            "question_type": "translation",
            "question": f"请翻译以下单词：{word_info['word']}",
            "correct_answer": word_info["translation"],
            "hint": f"音标：{word_info['phonetic']}",
            "difficulty": word_info["difficulty_level"]
        }
    
    def _generate_multiple_choice_question(self, word_info):
        """
        生成选择题
        
        Args:
            word_info (dict): 单词信息
            
        Returns:
            dict: 题目信息
        """
        # 获取其他单词作为干扰项
        other_words = self.words_crud.list_all(limit=10)
        other_words = [w for w in other_words if w["id"] != word_info["id"]]
        
        # 随机选择3个干扰项
        distractors = random.sample(other_words, min(3, len(other_words)))
        options = [word_info["translation"]] + [w["translation"] for w in distractors]
        random.shuffle(options)
        
        return {
            "question_id": f"choice_{word_info['id']}",
            "word_id": word_info["id"],
            "question_type": "multiple_choice",
            "question": f"以下哪个是单词 '{word_info['word']}' 的正确翻译？",
            "options": options,
            "correct_answer": word_info["translation"],
            "hint": f"音标：{word_info['phonetic']}",
            "difficulty": word_info["difficulty_level"]
        }
    
    def _generate_spelling_question(self, word_info):
        """
        生成拼写题目
        
        Args:
            word_info (dict): 单词信息
            
        Returns:
            dict: 题目信息
        """
        return {
            "question_id": f"spell_{word_info['id']}",
            "word_id": word_info["id"],
            "word": word_info["word"],
            "translation": word_info["translation"],
            "phonetic": word_info["phonetic"],
            "question_type": "spelling",
            "question": f"以下释义对应的英文单词是：{word_info['translation']}",
            "correct_answer": word_info["word"],
            "hint": f"音标：{word_info['phonetic']}",
            "difficulty_level": word_info["difficulty_level"]
        }
    
    def close(self):
        """
        关闭数据库连接（使用连接池时无需手动关闭）
        """
        # 连接池会自动管理连接，无需手动关闭
        pass

def main():
    """
    测试函数
    """
    from config import configure_logging
    configure_logging()
    vlm = VocabularyLearningManager()
    
    logger.info("=== 词汇学习管理测试 ===")
    
    # 测试开始学习会话
    logger.info("1. 测试开始学习会话:")
    session_result = vlm.start_learning_session(1, difficulty_level=2, word_count=5)
    logger.info("学习会话结果: %s", session_result['success'])
    
    if session_result["success"]:
        session_info = session_result["session_info"]
        logger.info("学习单词数量: %s", session_info['total_count'])
        
        # 测试获取当前单词
        logger.info("2. 测试获取当前单词:")
        current_word = vlm.get_current_word(session_info)
        if current_word:
            logger.info("当前单词: %s - %s", current_word.get('word'), current_word.get('translation'))
        
        # 测试生成测试题目
        logger.info("3. 测试生成测试题目:")
        questions = vlm.generate_test_questions(1, word_count=3)
        logger.info("生成了 %s 道题目", len(questions))
        for i, q in enumerate(questions[:2]):  # 只显示前2道题
            logger.info("  题目%s: %s", i + 1, q['question'])
    
    vlm.close()

if __name__ == "__main__":
    main()
