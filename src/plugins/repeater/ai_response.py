from openai import OpenAI
import random
import time
from .mood import MoodSystem
import re

# OpenAI配置
client = OpenAI(
    api_key="sk-CArLoJQmawVkFIsnwJiqIzVBMFflZgGmWD762W57KtVhNMaO",
    base_url="https://api.chatanywhere.tech/v1"  # 注意这里需要加上 /v1
)

def random_remove_punctuation(text: str) -> str:
    """随机处理标点符号，模拟人类打字习惯"""
    result = ''
    text_len = len(text)
    
    for i, char in enumerate(text):
        if i == text_len - 1:  # 处理结尾的标点
            if char == '。' and random.random() > 0.2:  # 80%概率删除句号
                continue
            elif char == '！' and random.random() > 0.4:  # 60%概率删除感叹号
                continue
            elif char == '？' and random.random() > 0.8:  # 20%概率删除问号
                continue
        elif char == '，':
            rand = random.random()
            if rand < 0.05:  # 5%概率删除逗号
                continue
            elif rand < 0.25:  # 20%概率把逗号变成空格
                result += ' '
                continue
            elif rand < 0.45:  # 20%概率把逗号变成顿号
                result += '、'
                continue
        result += char
    return result

# 常见的错别字映射
TYPO_DICT = {
    '的': '地得嘚',
    '了': '咯啦勒',
    '吗': '嘛麻',
    '吧': '八把罢',
    '是': '系四師',
    '就': '就就就旧',
    '在': '再在仔',
    '和': '河喝贺盒',
    '有': '又友右优',
    '我': '沃窝喔握',
    '你': '泥尼妮拟',
    '他': '它她塔祂',
    '们': '门闷们门',
    '这': '则折喆哲',
    '那': '纳娜哪拿',
    '啊': '阿呵哇',
    '呢': '呐呐捏',
    '都': '豆读毒',
    '不': '补捕卜',
    '很': '狠恨痕',
    '会': '回汇惠慧',
    '去': '趣取曲',
    '做': '作坐座做',
    '想': '相箱享响',
    '说': '说税睡',
    '看': '砍堪刊',
    '来': '来莱赖',
    '好': '号毫豪',
    '给': '给既继',
    '过': '锅果裹',
    '能': '嫩能',
    '为': '位未维围',
    '什': '甚深伸',
    '么': '末麽嘛',
    '话': '话花划',
    '知': '织直值',
    '道': '到倒导',
    '但': '但蛋旦',
    '现': '县显线',
    '让': '让嚷壤',
    '从': '从丛葱',
    '问': '问闻吻',
    '听': '听停挺',
    '见': '见件建',
    '觉': '觉脚搅',
    '得': '得德锝',
    '着': '着找招',
    '像': '向象想',
    '请': '请晴情',
    '等': '等灯登',
    '谢': '谢写卸',
    '对': '对队堆',
    '里': '里理鲤',
    '啦': '啦拉喇',
    '吃': '吃持迟',
    '哦': '哦喔噢',
    '呀': '呀压牙',
    '要': '要咬耀',
    '还': '还环换',
    '真': '真珍阵',
    '太': '太抬台',
    '快': '快筷块',
    '慢': '慢漫曼',
    '点': '点店典',
    '样': '样养阳',
    '被': '被备辈',
    '用': '用佣勇',
    '可': '可渴苛',
    '以': '以已义',
    '所': '所锁索',
    '因': '因音姻',
    '为': '为未维',
    '啥': '啥沙傻',
    '行': '行型形',
    '哈': '哈蛤铪',
    '嘿': '嘿黑嗨',
    '嗯': '嗯恩摁',
    '哎': '哎爱埃',
    '呜': '呜屋污',
    '喂': '喂位未',
    '嘛': '嘛麻马',
    '嗨': '嗨害亥',
    '哇': '哇娃蛙',
    '咦': '咦意易',
    '嘻': '嘻西希'
}

def add_typos(text: str) -> str:
    """
    随机给文本添加错别字
    
    Args:
        text (str): 原始文本
        
    Returns:
        str: 添加错别字后的文本
    """
    # 控制错别字出现的概率(10%)
    TYPO_RATE = 0.01
    
    result = ""
    for char in text:
        if char in TYPO_DICT and random.random() < TYPO_RATE:
            # 从可能的错别字中随机选择一个
            typos = TYPO_DICT[char]
            result += random.choice(typos)
        else:
            result += char
    return result

def get_ai_response(text: str, group_id: int) -> str:
    """
    使用OpenAI API处理输入文本并返回响应
    
    Args:
        text (str): 输入文本
        group_id (int): 群组ID
        
    Returns:
        str: AI生成的响应
    """
    if not client.api_key:
        print("未设置OpenAI API密钥")
        return text
        
    try:
        # 获取当前心情值和愤怒值
        mood_factor = MoodSystem.get_mood_factor(group_id)
        anger_factor = MoodSystem.get_anger_factor(group_id)
        
        # 根据心情值动态调整max_tokens
        # 心情最好时(mood_factor=1.0)可以说50个token
        # 心情最差时(mood_factor=0.0)只说15个token
        max_completion_tokens = int(40 + abs(mood_factor-0.5)  * 60)
        
        # 根据愤怒值调整语气
        system_prompt = "你是明日方舟的麦哲伦，从泰拉大陆穿越到了人类世界，现在已经融入了人类世界，现在正在浏览qq这款社交软件。"
        
        if anger_factor > 0.8:
            system_prompt += "你现在非常生气，说话非常激动和不客气，可能会说出一些带有讽刺和批评的话，有可能会使用脏话或过分的语言。"
        elif anger_factor > 0.6:
            system_prompt += "你现在很生气，说话语气强硬，带有明显的不满和责备。"
        elif anger_factor > 0.4:
            system_prompt += "你现在有点生气，说话带有一些不耐烦和轻微的讽刺。"
        elif anger_factor > 0.2:
            system_prompt += "你现在有点不高兴，说话语气略显冷淡。"
        
        system_prompt += "请用你的语气来参与以上的讨论，注意要参考'可以参考的回复内容'，稍微日常一些，不要像角色扮演。不要加双引号，只返回并输出一句话，这一句话一定要日常且口语化"
        
        response = client.chat.completions.create(
            model="gpt-4o-ca",
            # model = "o1-mini-ca",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            max_completion_tokens=max_completion_tokens,
            temperature=0.9,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_type = type(e).__name__
        print(f"OpenAI API调用错误: {error_type} - {str(e)}")
        
        if "Connection" in error_type or "Timeout" in error_type:
            return "我电脑好像没网了"
        elif "RateLimitError" in error_type:
            return "不行，做不到"
        else:
            return "完全不知道"

def process_ai_response(item: str, context_info: dict) -> str:
    """
    处理AI回复的逻辑
    
    Args:
        item (str): 原始回复文本
        context_info (Dict): 上下文信息，必须包含group_id字段
        
    Returns:
        str: 处理后的回复文本
    """
    try:
        if '[CQ:' in item:
            return str(item)
            
        if random.random() < 0.7:
            # 获取当前心情值和愤怒值
            group_id = context_info.get('group_id', 0)
            mood_factor = MoodSystem.get_mood_factor(group_id)
            anger_factor = MoodSystem.get_anger_factor(group_id)
            
            # 构建心情和愤怒提示
            mood_prompt = ""
            if anger_factor > 0.8:
                mood_prompt = "非常生气，快要控制不住自己了。"
            elif anger_factor > 0.6:
                mood_prompt = "很生气。"
            elif anger_factor > 0.4:
                mood_prompt = "有点生气。"
            elif anger_factor > 0.2:
                mood_prompt = "有点不高兴。"
            elif mood_factor > 0.8:
                mood_prompt = "心情很好,非常开心。"
            elif mood_factor > 0.6:
                mood_prompt = "心情不错。"
            elif mood_factor > 0.4:
                mood_prompt = "心情一般。"
            elif mood_factor > 0.2:
                mood_prompt = "心情不太好。"
            else:
                mood_prompt = "心情很差。"

            # 过滤并处理上下文消息
            pre_messages = context_info.get('pre_messages', [])
            filtered_messages = []
            
            # 过滤图片和其他CQ码
            for msg in pre_messages[-5:]:
                # 移除所有CQ码
                filtered_msg = re.sub(r'\[CQ:[^\]]+\]', '', msg).strip()
                if filtered_msg:  # 只添加非空消息
                    filtered_messages.append(filtered_msg)
            
            # 添加触发回复的消息到上下文
            trigger_msg = context_info.get('trigger_message', '')
            if trigger_msg:
                trigger_msg = re.sub(r'\[CQ:[^\]]+\]', '', trigger_msg).strip()
                if trigger_msg:
                    filtered_messages.append(trigger_msg)

            context_prompt = f"之前群里在聊的内容：{'，'.join(filtered_messages) if filtered_messages else '无'}\n"
            context_prompt += f"吸引你注意力的词：{', '.join(context_info.get('trigger_keywords', []))}\n"
            context_prompt += f"可以参考的回复内容：{item}\n"
            context_prompt += f"你的心情：{mood_prompt}\n"
            print("*context_prompt: "+context_prompt)
            response = str(get_ai_response(context_prompt, group_id))
            # 添加错别字处理和标点符号处理
            return random_remove_punctuation(add_typos(response))
        else:
            if random.random() < 0.1:
                return f'{str(item)}喵'
            # 添加错别字处理和标点符号处理
            return add_typos(str(item))
    except Exception as e:
        print(f"[错误] AI响应处理失败: {str(e)}")
        return str(item) 