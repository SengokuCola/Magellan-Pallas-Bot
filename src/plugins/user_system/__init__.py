from nonebot import on_message
from nonebot.rule import Rule
from nonebot.typing import T_State
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11 import Message, MessageSegment, permission

from .user_manager import UserManager

# 监听所有消息
message_handler = on_message(
    priority=1,
    block=False,
    permission=permission.GROUP
)

@message_handler.handle()
async def handle_message(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 获取用户信息
    user_id = event.user_id
    group_id = event.group_id
    message = event.get_plaintext().strip()
    
    # 更新用户信息
    user_manager = UserManager()
    await user_manager.update_user_message(user_id, group_id, message)
    
    # 根据消息内容更新好感度
    if "麦麦" in message:
        if any(word in message for word in ["喜欢", "可爱", "厉害", "棒", "好", "爱"]):
            await user_manager.update_favorability(user_id, 2)  # 正面评价加2分
        elif any(word in message for word in ["讨厌", "笨", "蠢", "差", "废", "烦"]):
            await user_manager.update_favorability(user_id, -2)  # 负面评价减2分
        else:
            await user_manager.update_favorability(user_id, 0.5)  # 普通提及加0.5分 