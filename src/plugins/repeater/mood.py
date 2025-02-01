import time
from openai import OpenAI

class MoodSystem:
    # 心情系统参数
    MOOD_MAX = 100                 # 最大心情值
    MOOD_MIN = 0                   # 最小心情值
    MOOD_DEFAULT = 50              # 默认心情值
    MOOD_DECAY = 0.1               # 心情衰减率(每分钟)
    
    # 愤怒系统参数
    ANGER_MAX = 100                # 最大愤怒值
    ANGER_MIN = 0                  # 最小愤怒值
    ANGER_DEFAULT = 0              # 默认愤怒值
    ANGER_DECAY = 2              # 愤怒衰减率(每分钟，衰减比心情快)
    
    # 群组心情状态字典
    _group_states = {}  # 格式: {group_id: {'mood': value, 'anger': value, 'last_update': timestamp}}

    # OpenAI客户端
    _client = OpenAI(
        api_key="sk-CArLoJQmawVkFIsnwJiqIzVBMFflZgGmWD762W57KtVhNMaO",
        base_url="https://api.chatanywhere.tech/v1"
    )

    @classmethod
    def _ensure_group_state(cls, group_id: int) -> None:
        """确保群组状态存在"""
        if group_id not in cls._group_states:
            cls._group_states[group_id] = {
                'mood': cls.MOOD_DEFAULT,
                'anger': cls.ANGER_DEFAULT,
                'last_update': time.time()
            }

    @classmethod
    def analyze_sentiment(cls, context_messages: list, current_text: str, is_to_me: bool) -> tuple:
        """
        使用API分析聊天内容的情感倾向,返回心情分数和愤怒分数
        
        Returns:
            tuple: (心情分数变化值(-10到+10), 愤怒分数变化值(-10到+10))
        """
        try:
            prompt = "请分析以下聊天记录中对机器人(麦哲伦)，也就是你，的评价程度。分别返回两个数字：心情分数和愤怒分数，用逗号分隔。\n"
            prompt += "心情分数(-10到+10)：\n"
            prompt += "-10分: 极度负面评价或严重贬低\n"
            prompt += "-5分: 明显的负面评价\n"
            prompt += "-3分: 轻微的负面评价\n"
            prompt += "0分: 中性或无关评价\n"
            prompt += "+3分: 轻微的正面评价\n"
            prompt += "+5分: 明显的正面评价\n"
            prompt += "+10分: 极度正面评价或高度赞扬\n\n"
            prompt += "愤怒分数(-10到+10)：\n"
            prompt += "-10分: 极度安抚或表达歉意\n"
            prompt += "-5分: 明显的安抚或友好\n"
            prompt += "-3分: 轻微的安抚或关心\n"
            prompt += "0分: 中性内容\n"
            prompt += "+3分: 轻微的挑衅或不敬\n"
            prompt += "+5分: 明显的嘲讽或侮辱\n"
            prompt += "+7分: 严重的人身攻击\n"
            prompt += "+10分: 极度过分的侮辱或威胁\n\n"
            
            prompt += "最近的聊天记录:\n"
            for msg in context_messages[-5:]:
                prompt += f"- {msg}\n"
            prompt += f"\n当前消息: {current_text}"
            
            if is_to_me:
                prompt += "\n(这条消息是直接对机器人说的)"

            response = cls._client.chat.completions.create(
                model="gpt-4o-ca",
                messages=[
                    {"role": "system", "content": "你是一个情感分析助手，专门分析聊天内容中对机器人的评价。只返回两个数字，用逗号分隔，分别表示心情分数和愤怒分数。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            try:
                scores = response.choices[0].message.content.strip().split(',')
                mood_score = float(scores[0])
                anger_score = float(scores[1])
                
                # 确保分数在合理范围内
                mood_score = max(-10, min(10, mood_score))
                anger_score = max(-10, min(10, anger_score))
                
                # 如果是直接对话，增加权重
                if is_to_me:
                    if mood_score > 0:
                        mood_score += 2
                    elif mood_score < 0:
                        mood_score -= 2
                    if anger_score > 0:
                        anger_score *= 1.5
                    elif anger_score < 0:
                        anger_score *= 2  # 直接安抚效果更好
                
                # 转换为心情值和愤怒值变化
                if mood_score > 0:
                    mood_delta = mood_score * 5
                else:
                    mood_delta = mood_score * 3
                
                # 愤怒值变化比例
                if anger_score > 0:
                    anger_delta = anger_score * 1  # 激怒效果
                else:
                    anger_delta = anger_score * 3  # 安抚效果更强
                    
                if abs(mood_delta) > 0.1 or abs(anger_delta) > 0.1:
                    print(f"[情感分析] 心情评分: {mood_score:+.1f}, 愤怒评分: {anger_score:+.1f}, 触发文本: {current_text}")
                return mood_delta, anger_delta
                
            except (ValueError, IndexError):
                print(f"[情感分析] 无法解析分数: {response.choices[0].message.content}")
                return 0, 0
                
        except Exception as e:
            print(f"[情感分析] 分析失败: {str(e)}")
            return 0, 0

    @classmethod
    def get_current_mood(cls, group_id: int) -> float:
        """获取指定群组的当前心情值,同时计算衰减"""
        cls._ensure_group_state(group_id)
        state = cls._group_states[group_id]
        
        current_time = time.time()
        time_passed = (current_time - state['last_update']) / 60  # 转换为分钟
        
        # 计算心情衰减
        decay = cls.MOOD_DECAY * time_passed
        state['mood'] = max(cls.MOOD_MIN, 
                          min(cls.MOOD_MAX, 
                              state['mood'] - decay))
        
        state['last_update'] = current_time
        return state['mood']

    @classmethod
    def update_mood(cls, group_id: int, delta: float) -> None:
        """更新指定群组的心情值"""
        cls._ensure_group_state(group_id)
        state = cls._group_states[group_id]
        
        state['mood'] = max(cls.MOOD_MIN, 
                          min(cls.MOOD_MAX, 
                              state['mood'] + delta))
        state['last_update'] = time.time()

    @classmethod
    def get_current_anger(cls, group_id: int) -> float:
        """获取指定群组的当前愤怒值,同时计算衰减"""
        cls._ensure_group_state(group_id)
        state = cls._group_states[group_id]
        
        current_time = time.time()
        time_passed = (current_time - state['last_update']) / 60
        
        # 计算愤怒衰减
        decay = cls.ANGER_DECAY * time_passed
        state['anger'] = max(cls.ANGER_MIN, 
                           min(cls.ANGER_MAX, 
                               state['anger'] - decay))
        return state['anger']

    @classmethod
    def update_anger(cls, group_id: int, delta: float) -> None:
        """更新指定群组的愤怒值"""
        cls._ensure_group_state(group_id)
        state = cls._group_states[group_id]
        
        state['anger'] = max(cls.ANGER_MIN, 
                           min(cls.ANGER_MAX, 
                               state['anger'] + delta))

    @classmethod
    def process_text(cls, group_id: int, text: str, context_messages: list, is_to_me: bool = False) -> None:
        """处理文本并更新指定群组的心情和愤怒值"""
        # 使用API分析情感得分
        mood_delta, anger_delta = cls.analyze_sentiment(context_messages, text, is_to_me)
            
        # 更新心情值和愤怒值
        if mood_delta != 0 or anger_delta != 0:
            cls.update_mood(group_id, mood_delta)
            cls.update_anger(group_id, anger_delta)
            current_mood = cls.get_current_mood(group_id)
            current_anger = cls.get_current_anger(group_id)
            print(f"[心情系统] 群{group_id} - 当前心情值: {current_mood:.2f}, 愤怒值: {current_anger:.2f}, 变化: 心情{mood_delta:+.2f}/愤怒{anger_delta:+.2f}, 触发文本: {text}")

    @classmethod
    def get_mood_factor(cls, group_id: int) -> float:
        """获取指定群组的当前心情因子(0-1之间)"""
        return cls.get_current_mood(group_id) / cls.MOOD_MAX 

    @classmethod
    def get_anger_factor(cls, group_id: int) -> float:
        """获取指定群组的当前愤怒因子(0-1之间)"""
        return cls.get_current_anger(group_id) / cls.ANGER_MAX 