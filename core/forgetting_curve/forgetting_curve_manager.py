"""
遗忘曲线模块
基于艾宾浩斯遗忘曲线的学习时间安排
"""

# 导入配置常量
from config import LEARNING_PARAMS

from tools.learning_records_crud import LearningRecordsCRUD
from datetime import datetime, timedelta
import math

class ForgettingCurveManager:
    """遗忘曲线管理类"""
    
    def __init__(self):
        self.learning_records_crud = LearningRecordsCRUD()
        self.forgetting_rate = 0.84
        self.base_interval = 0.5
        self.mastery_coefficient = 3.0
    
    def calculate_next_review_time(self, user_id, word_id, mastery_level, review_count):
        """
        计算下次复习时间
        
        基于艾宾浩斯遗忘曲线和掌握程度计算复习间隔
        
        Args:
            user_id (int): 用户ID
            word_id (int): 单词ID
            mastery_level (float): 掌握程度 (0.0-1.0)
            review_count (int): 复习次数
            
        Returns:
            datetime: 下次复习时间
        """
        # 获取当前时间
        now = datetime.now()
        
        # 计算复习间隔（小时）
        interval_hours = self._calculate_review_interval(mastery_level, review_count)
        
        # 计算下次复习时间
        next_review_time = now + timedelta(hours=interval_hours)
        
        return next_review_time
    
    def _calculate_review_interval(self, mastery_level, review_count):
        """
        计算复习间隔
        
        Args:
            mastery_level (float): 掌握程度
            review_count (int): 复习次数
            
        Returns:
            float: 复习间隔（小时）
        """
        # 基础间隔
        base_interval = self.base_interval
        
        # 根据掌握程度调整间隔
        # 掌握程度越高，间隔越长
        mastery_factor = 1 + (mastery_level * self.mastery_coefficient)
        
        # 根据复习次数调整间隔
        # 复习次数越多，间隔越长（指数增长）
        review_factor = math.pow(2, min(review_count, LEARNING_PARAMS["max_review_count"]))  # 限制最大增长倍数
        
        # 计算最终间隔
        interval = base_interval * mastery_factor * review_factor
        
        # 限制间隔范围（1小时到30天）
        min_interval = 1  # 1小时
        max_interval = 24 * 30  # 30天
        
        return max(min_interval, min(interval, max_interval))
    
    def get_review_words(self, user_id, limit=LEARNING_PARAMS["default_review_limit"], offset=0):
        """
        获取需要复习的单词
        
        Args:
            user_id (int): 用户ID
            limit (int): 限制数量，默认20个
            offset (int): 偏移量，用于轮播
            
        Returns:
            list: 需要复习的单词记录列表
        """
        # 获取用户所有学习记录
        all_records = self.learning_records_crud.get_by_user(user_id)
        
        # 筛选需要复习的记录
        review_records = []
        now = datetime.now()
        
        for record in all_records:
            # 只要掌握程度小于1.0就需要复习
            if record['mastery_level'] < 1.0:
                # 计算应该复习的时间
                next_review_time = self.calculate_next_review_time(
                    user_id, 
                    record['word_id'], 
                    record['mastery_level'], 
                    record['review_count']
                )
                
                # 如果当前时间已经超过应该复习的时间，或者刚学习完（掌握程度较低）
                if now >= next_review_time or record['mastery_level'] < 0.6:
                    # 计算复习紧急程度
                    if record['mastery_level'] < 0.6:
                        # 刚学习完的单词，紧急程度设为最高
                        urgency = 1000
                    else:
                        # 时间越久越紧急
                        urgency = (now - next_review_time).total_seconds() / 3600
                    
                    record['urgency'] = urgency
                    review_records.append(record)
        
        # 按紧急程度排序，最紧急的优先
        review_records.sort(key=lambda x: x['urgency'], reverse=True)
        
        # 支持轮播：从offset开始取limit个
        start_idx = offset % len(review_records) if review_records else 0
        end_idx = start_idx + limit
        
        if end_idx <= len(review_records):
            # 正常情况
            return review_records[start_idx:end_idx]
        else:
            # 需要循环取数据
            result = review_records[start_idx:]
            remaining = limit - len(result)
            if remaining > 0:
                result.extend(review_records[:remaining])
            return result
    
    def update_review_result(self, record_id, is_correct, response_time):
        """
        更新复习结果
        
        Args:
            record_id (int): 记录ID
            is_correct (bool): 是否正确
            response_time (float): 响应时间（秒）
            
        Returns:
            dict: 更新结果
        """
        # 获取当前记录
        record = self.learning_records_crud.read(record_id)
        if not record:
            return {"success": False, "message": "学习记录不存在"}
        
        # 计算新的掌握程度
        new_mastery = self._calculate_new_mastery_level(
            record['mastery_level'], 
            is_correct, 
            response_time
        )
        
        # 更新复习次数
        new_review_count = record['review_count'] + 1
        
        # 判断是否已学会
        new_is_learned = new_mastery >= 0.9
        
        # 更新记录
        affected_rows = self.learning_records_crud.update(
            record_id,
            mastery_level=new_mastery,
            review_count=new_review_count,
            last_reviewed_at=datetime.now(),
            is_mastered=new_is_learned
        )
        
        # 计算下次复习时间
        next_review_time = self.calculate_next_review_time(
            record['user_id'],
            record['word_id'],
            new_mastery,
            new_review_count
        )
        
        return {
            "success": affected_rows > 0,
            "message": "复习结果更新成功" if affected_rows > 0 else "更新失败",
            "new_mastery_level": new_mastery,
            "is_mastered": new_is_learned,
            "next_review_time": next_review_time
        }
    
    def _calculate_new_mastery_level(self, current_mastery, is_correct, response_time):
        """
        计算新的掌握程度
        
        Args:
            current_mastery (float): 当前掌握程度
            is_correct (bool): 是否正确
            response_time (float): 响应时间（秒）
            
        Returns:
            float: 新的掌握程度
        """
        if is_correct:
            # 答对了，掌握程度增加
            # 响应时间越短，增加越多
            time_bonus = max(0, 1 - response_time / LEARNING_PARAMS["response_time_bonus"])  # 10秒内完成有奖励
            increase = 0.15 + (time_bonus * 0.1)  # 基础增加0.15，时间奖励最多0.1
            new_mastery = min(1.0, current_mastery + increase)
        else:
            # 答错了，掌握程度减少
            # 响应时间越长，减少越少（可能是思考时间）
            time_penalty = min(0.5, response_time / LEARNING_PARAMS["response_time_penalty"])  # 思考时间可以减少惩罚
            decrease = 0.2 - (time_penalty * 0.1)  # 基础减少0.2，思考时间最多减少0.1
            new_mastery = max(0.0, current_mastery - decrease)
        
        return new_mastery
    
    def get_forgetting_curve_data(self, user_id, days=7):
        """
        获取遗忘曲线数据 - 未来复习计划
        
        Args:
            user_id (int): 用户ID
            days (int): 未来天数，默认7天
            
        Returns:
            list: 未来每天需要复习的单词数量
        """
        # 获取用户学习记录
        records = self.learning_records_crud.get_by_user(user_id)
        
        if not records:
            return []
        
        # 按单词分组，获取每个单词的最新记录
        word_latest_records = {}
        for record in records:
            word_id = record['word_id']
            if word_id not in word_latest_records:
                word_latest_records[word_id] = record
            else:
                # 保留最新的记录
                current_latest = word_latest_records[word_id]
                if record['last_reviewed_at'] > current_latest['last_reviewed_at']:
                    word_latest_records[word_id] = record
        
        # 生成未来7天的复习计划
        review_plan = []
        current_time = datetime.now()
        
        for day_offset in range(1, days + 1):
            target_date = current_time + timedelta(days=day_offset)
            words_to_review = 0
            
            for word_id, record in word_latest_records.items():
                # 计算下次复习时间
                next_review_time = self.calculate_next_review_time(
                    record['user_id'],
                    record['word_id'],
                    record['mastery_level'],
                    record['review_count']
                )
                
                # 检查是否需要在目标日期复习
                if isinstance(next_review_time, str):
                    next_review_time = datetime.fromisoformat(next_review_time.replace('Z', '+00:00'))
                
                # 如果下次复习时间在目标日期（允许±1天的误差）
                if abs((next_review_time - target_date).days) <= 1:
                    words_to_review += 1
            
            review_plan.append({
                'day': day_offset,
                'date': target_date.strftime('%Y-%m-%d'),
                'words_to_review': words_to_review
            })
        
        return review_plan
    
    def predict_retention_rate(self, mastery_level, hours_since_review):
        """
        预测记忆保持率
        
        Args:
            mastery_level (float): 掌握程度
            hours_since_review (float): 距离上次复习的小时数
            
        Returns:
            float: 预测的记忆保持率
        """
        # 基于艾宾浩斯遗忘曲线的记忆保持率公式
        # R = e^(-t/S)，其中R是保持率，t是时间，S是强度
        # 强度S与掌握程度相关
        strength = 1 + mastery_level * LEARNING_PARAMS["strength_multiplier"]  # 掌握程度越高，强度越大
        
        # 计算保持率
        retention_rate = math.exp(-hours_since_review / strength)
        
        return max(0, min(1, retention_rate))
    
    def close(self):
        """
        关闭数据库连接（使用连接池时无需手动关闭）
        """
        # 连接池会自动管理连接，无需手动关闭
        pass
