import random
from nonebot import on_message
from nonebot.rule import Rule
from nonebot.typing import T_State
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11 import Message, MessageSegment, permission
from .travel import get_random_location, get_map_url

async def is_travel_msg(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    msg = event.get_plaintext().strip()
    return msg in ['麦麦旅游', '麦麦去哪玩', '麦麦去哪里玩']

travel = on_message(
    rule=Rule(is_travel_msg),
    priority=5,
    block=True,
    permission=permission.GROUP
)

@travel.handle()
async def handle_travel(bot: Bot, event: GroupMessageEvent, state: T_State):
    text_msg, map_url = get_random_location()
    # 先发送文本消息
    await travel.send(Message(text_msg))
    # 如果有地图，再发送地图
    if map_url:
        await travel.send(MessageSegment.image(map_url)) 