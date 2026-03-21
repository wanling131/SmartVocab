"""
评测模块
等级测试：抽题组卷、自动计分
"""

import random
from datetime import datetime
from tools.words_crud import WordsCRUD
from tools.evaluation_papers_crud import EvaluationPapersCRUD
from tools.evaluation_paper_items_crud import EvaluationPaperItemsCRUD
from tools.evaluation_results_crud import EvaluationResultsCRUD
from core.vocabulary.vocabulary_learning_manager import VocabularyLearningManager
from config import LEARNING_PARAMS


# CEFR/水平到难度映射
LEVEL_TO_DIFFICULTY = {'A1': 1, 'A2': 1, 'B1': 2, 'B2': 3, 'C1': 4, 'C2': 5}


class EvaluationManager:
    """评测管理"""
    
    def __init__(self):
        self.words_crud = WordsCRUD()
        self.papers_crud = EvaluationPapersCRUD()
        self.items_crud = EvaluationPaperItemsCRUD()
        self.results_crud = EvaluationResultsCRUD()
        self.vocabulary_manager = VocabularyLearningManager()
    
    def start_level_test(self, user_id: int, question_count: int = 10,
                         difficulty_level: int = None, dataset_type: str = None) -> dict:
        """
        开始等级测试：抽题组卷
        """
        # 抽题：按难度从 words 获取
        if difficulty_level:
            words = self.words_crud.get_by_difficulty(difficulty_level, limit=question_count * 3)
        else:
            words = self.words_crud.list_all(limit=question_count * 5)
        
        if dataset_type:
            words = [w for w in words if w.get('dataset_type') == dataset_type]
        
        if len(words) < question_count:
            return {"success": False, "message": "词库数量不足，无法组卷"}
        
        selected = random.sample(words, min(question_count, len(words)))
        
        # 创建试卷
        paper_id = self.papers_crud.create(
            user_id=user_id,
            paper_type='level_test',
            question_count=len(selected)
        )
        if not paper_id:
            return {"success": False, "message": "创建试卷失败"}
        
        # 生成题目（复用 vocabulary 的题型逻辑）
        questions = []
        for i, w in enumerate(selected):
            word_info = self.words_crud.read(w['id'])
            if not word_info:
                continue
            q_type = random.choice(['choice', 'translation', 'spelling'])
            if q_type == 'choice':
                q = self.vocabulary_manager._generate_choice_question(word_info)
            elif q_type == 'spelling':
                q = self.vocabulary_manager._generate_spelling_question(word_info)
            else:
                q = self.vocabulary_manager._generate_translation_question(word_info)
                q['word'] = word_info.get('word')
                q['phonetic'] = word_info.get('phonetic')
            q['item_order'] = i + 1
            q['id'] = word_info['id']
            questions.append(q)
            self.items_crud.create(paper_id, w['id'], q.get('question_type', 'translation'), i + 1)
        
        return {
            "success": True,
            "paper_id": paper_id,
            "questions": questions,
            "total_count": len(questions)
        }
    
    def submit_level_test(self, user_id: int, paper_id: int, answers: list,
                          duration_seconds: int = 0) -> dict:
        """
        提交等级测试：answers = [{"word_id": int, "user_answer": str, "correct_answer": str}, ...]
        """
        paper = self.papers_crud.read(paper_id)
        if not paper:
            return {"success": False, "message": "试卷不存在"}
        if paper['user_id'] != user_id:
            return {"success": False, "message": "无权提交该试卷"}
        
        items = self.items_crud.get_by_paper(paper_id)
        answer_map = {a.get('word_id'): a for a in answers if a.get('word_id')}
        
        correct_count = 0
        for item in items:
            ans = answer_map.get(item['word_id'])
            if ans:
                is_correct = self._check_answer(
                    ans.get('user_answer', ''),
                    ans.get('correct_answer', item.get('translation', '')),
                    item.get('question_type', 'translation')
                )
                if is_correct:
                    correct_count += 1
        
        total = len(items)
        score = (correct_count / total * 100) if total > 0 else 0
        
        # 评估水平（简化：按正确率映射）
        if score >= 90:
            assessed_level = 'C1'
        elif score >= 80:
            assessed_level = 'B2'
        elif score >= 70:
            assessed_level = 'B1'
        elif score >= 60:
            assessed_level = 'A2'
        else:
            assessed_level = 'A1'
        
        self.results_crud.create(
            user_id=user_id,
            paper_id=paper_id,
            score=score,
            correct_count=correct_count,
            total_count=total,
            duration_seconds=duration_seconds,
            assessed_level=assessed_level
        )
        
        return {
            "success": True,
            "score": score,
            "correct_count": correct_count,
            "total_count": total,
            "assessed_level": assessed_level
        }
    
    def _check_answer(self, user_answer: str, correct_answer: str, question_type: str) -> bool:
        """检查答案"""
        u = (user_answer or '').strip().lower()
        c = (correct_answer or '').strip().lower()
        if question_type == 'choice':
            return u == c
        if question_type == 'spelling':
            return u == c
        # 翻译题：允许部分匹配
        return c in u or u in c or u == c
