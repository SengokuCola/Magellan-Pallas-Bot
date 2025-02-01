import random
from nonebot import on_message
from nonebot.rule import Rule
from nonebot.typing import T_State
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11 import Message, MessageSegment, permission
from src.common.config import BotConfig
from .story_generator import generate_story

def random_remove_punctuation(text: str) -> str:
    """随机处理标点符号，模拟人类打字习惯"""
    result = ''
    text_len = len(text)
    
    for i, char in enumerate(text):
        if char == '。' and i == text_len - 1:  # 结尾的句号
            if random.random() > 0.2:  # 80%概率删除结尾句号
                continue
        elif char == '，':
            rand = random.random()
            if rand < 0.05:  # 5%概率删除逗号
                continue
            elif rand < 0.25:  # 20%概率把逗号变成空格
                result += ' '
                continue
        result += char
    return result

async def is_story_msg(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    msg = event.get_plaintext().strip()
    return msg.startswith(('麦麦讲故事', '麦麦写故事', '麦麦说故事'))

story = on_message(
    rule=Rule(is_story_msg),
    priority=5,
    block=True,
    permission=permission.GROUP
)

@story.handle()
async def handle_story(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 检查冷却时间
    config = BotConfig(event.self_id, event.group_id)
    if not config.is_cooldown('story'):
        return
    config.refresh_cooldown('story')
    
    # 获取用户输入的主题
    msg = event.get_plaintext().strip()
    theme = msg.split(' ', 1)[1] if ' ' in msg else None
    
    try:
        # 生成故事
        story_text = await generate_story(theme)
        if not story_text:
            await story.finish(random_remove_punctuation("抱歉，我现在编不出什么好故事..."))
            return
            
        # 直接发送完整故事
        await story.finish(Message(story_text.strip()))
                
    except Exception as e:
        print(f"[错误] 故事生成失败: {str(e)}")
        await story.finish(random_remove_punctuation("抱歉，我现在编不出什么好故事...")) 