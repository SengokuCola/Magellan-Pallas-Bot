from openai import OpenAI
import asyncio
import random
from functools import partial
from .config import STORY_TYPES, DEFAULT_THEMES, STORY_MAX_LENGTH, STORY_MIN_LENGTH

# OpenAI客户端配置
client = OpenAI(
    api_key="sk-CArLoJQmawVkFIsnwJiqIzVBMFflZgGmWD762W57KtVhNMaO",
    base_url="https://api.chatanywhere.tech/v1"
)

async def generate_story(theme: str = None) -> str:
    """
    生成一个基于给定主题的故事
    
    Args:
        theme (str): 故事主题，如果为None则随机选择
        
    Returns:
        str: 生成的故事内容
    """
    try:
        # 如果没有指定主题，随机选择一个
        if not theme:
            theme = random.choice(DEFAULT_THEMES)
            
        # 根据权重随机选择故事类型
        story_types = list(STORY_TYPES.keys())
        weights = list(STORY_TYPES.values())
        story_type = random.choices(story_types, weights=weights)[0]
        
        # 构建提示
        prompt = f"""请以明日方舟的世界观为背景，写一个关于{theme}的{story_type}。要求：
1. 语言要生动有趣，富有感染力
2. 故事长度控制在{STORY_MIN_LENGTH}-{STORY_MAX_LENGTH}字
3. 可以适当加入一些对话
4. 要有代入感，让读者感同身受

请直接开始讲故事，不要加标题，不要有任何前缀说明，也不要有后缀结尾，你可以选择署名。"""

        # 调用API生成故事
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            partial(
                client.chat.completions.create,
                model="gpt-3.5-turbo-16k",
                messages=[
                    {"role": "system", "content": "你是一个擅长写明日方舟同人故事的作家，要用生动有趣的方式讲述故事。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.8,
                top_p=1.0,
                frequency_penalty=0.3,
                presence_penalty=0.3
            )
        )
        
        story = response.choices[0].message.content.strip()
        if not story:
            return None
        return story
        
    except Exception as e:
        error_type = type(e).__name__
        print(f"[提示] API返回: {error_type} - {str(e)}")
        
        # 如果是FinishedException，说明已经生成了内容，但API提前结束了
        # 这种情况我们不需要返回None，让上层继续处理已生成的内容
        if "FinishedException" in error_type and response and response.choices:
            return response.choices[0].message.content.strip()
            
        return None 