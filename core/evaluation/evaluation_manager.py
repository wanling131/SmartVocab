"""
评测模块
等级测试：抽题组卷、自动计分
"""

import logging
import random
from datetime import datetime
from typing import Dict, Optional
from tools.words_crud import WordsCRUD
from tools.evaluation_papers_crud import EvaluationPapersCRUD
from tools.evaluation_paper_items_crud import EvaluationPaperItemsCRUD
from tools.evaluation_results_crud import EvaluationResultsCRUD
from core.vocabulary.vocabulary_learning_manager import VocabularyLearningManager
from config import LEARNING_PARAMS

logger = logging.getLogger(__name__)

# CEFR/水平到难度映射
LEVEL_TO_DIFFICULTY = {'A1': 1, 'A2': 1, 'B1': 2, 'B2': 3, 'C1': 4, 'C2': 5}


def _normalize_word_id(value) -> Optional[int]:
    """将 word_id 规范为 int，避免 JSON/str 与 DB/int 键不一致导致漏判。"""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
        # item_order 仅在成功入卷时递增，避免某词读取失败时出现 1,2,4,5 断层
        questions = []
        item_order = 0
        for w in selected:
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
            item_order += 1
            q['item_order'] = item_order
            q['id'] = word_info['id']
            questions.append(q)
            self.items_crud.create(
                paper_id, w['id'], q.get('question_type', 'translation'), item_order
            )
        
        # 与 evaluation_paper_items 实际行数一致（若有词在组卷时读失败，避免 question_count 虚高）
        actual = len(questions)
        if actual != len(selected):
            if not self.papers_crud.update_question_count(paper_id, actual):
                logger.error(
                    "同步试卷题数失败 paper_id=%s expected_count=%s（与抽题数 %s 不一致），将回滚本次组卷",
                    paper_id,
                    actual,
                    len(selected),
                )
                # 题项已逐条 autocommit 提交；若 UPDATE 失败则删除整张试卷，避免卷表 question_count 与题表行数永久不一致
                if not self.papers_crud.delete(paper_id):
                    logger.error(
                        "回滚失败：无法删除不完整试卷 paper_id=%s，请人工检查 evaluation_papers / evaluation_paper_items",
                        paper_id,
                    )
                return {
                    "success": False,
                    "message": "同步试卷题数失败，本次组卷已取消；请重试；若反复出现请检查数据库与外键/权限",
                }
        
        return {
            "success": True,
            "paper_id": paper_id,
            "questions": questions,
            "total_count": actual
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
        answer_map: Dict[int, dict] = {}
        for a in answers or []:
            wid = _normalize_word_id(a.get("word_id"))
            if wid is not None:
                answer_map[wid] = a
        
        # 分母仅使用 evaluation_paper_items 行数，与循环范围一致，保证：
        # total_count == correct_count + wrong_count，且循环内统计可解释整张试卷。
        # 若 paper.question_count 与题表不一致（历史脏数据或同步失败），以题表为准并打日志。
        n_items = len(items)
        paper_qc = int(paper.get("question_count") or 0)
        if paper_qc != n_items:
            logger.warning(
                "试卷 question_count 与题表行数不一致 paper_id=%s question_count=%s item_rows=%s，计分以题表为准",
                paper_id,
                paper_qc,
                n_items,
            )
        total = n_items
        if total <= 0:
            return {"success": False, "message": "试卷无有效题目"}
        
        correct_count = 0
        unanswered_count = 0
        answered_wrong_count = 0
        for item in items:
            wid = _normalize_word_id(item.get("word_id"))
            if wid is None:
                # 无效/缺失 word_id：无法匹配答卷，仍占分母一席，计入未作答统计以免与 total 脱节
                unanswered_count += 1
                continue
            ans = answer_map.get(wid)
            if ans is None:
                # 未提供该题答案：按错误处理（不计入正确）
                unanswered_count += 1
                continue
            is_correct = self._check_answer(
                ans.get("user_answer", ""),
                ans.get("correct_answer", item.get("translation", "")),
                item.get("question_type", "translation"),
            )
            if is_correct:
                correct_count += 1
            else:
                answered_wrong_count += 1
        
        wrong_count = total - correct_count
        # 不变量：每题恰属「答对 / 答错 / 未答(含无效 word_id)」之一
        # correct_count + answered_wrong_count + unanswered_count == total
        # wrong_count == answered_wrong_count + unanswered_count == total - correct_count
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
            "wrong_count": wrong_count,
            "answered_wrong_count": answered_wrong_count,
            "unanswered_count": unanswered_count,
            "assessed_level": assessed_level,
        }
    
    def _check_answer(self, user_answer: str, correct_answer: str, question_type: str) -> bool:
        """检查答案"""
        u = (user_answer or '').strip().lower()
        c = (correct_answer or '').strip().lower()

        # 空答案直接返回False
        if not u or not c:
            return False

        if question_type == 'choice':
            return u == c
        if question_type == 'spelling':
            return u == c
        # 翻译题：允许部分匹配
        return c in u or u in c or u == c
