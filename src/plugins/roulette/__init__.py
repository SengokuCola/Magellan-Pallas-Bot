from collections import defaultdict
from nonebot import on_message, require, get_bot, logger, get_driver
from nonebot.typing import T_State
from nonebot.rule import keyword, to_me, Rule
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.onebot.v11 import MessageSegment, Message, permission, GroupMessageEvent
from nonebot.permission import Permission
from src.common.config import BotConfig

import random
import time
# from .pseudorandom import roulette_randomizer


roulette_type = defaultdict(int)    # 0 踢人 1 禁言
roulette_status = defaultdict(int)  # 0 关闭 1 开启
roulette_time = defaultdict(int)
roulette_count = defaultdict(int)
timeout = 300
roulette_player = defaultdict(list)
role_cache = defaultdict(lambda: defaultdict(str))


async def am_I_admin(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    info = await get_bot(str(event.self_id)).call_api('get_group_member_info', **{
        'user_id': event.self_id,
        'group_id': event.group_id
    })
    role = info['role']
    role_cache[event.self_id][event.group_id] = role
    return role == 'admin' or role == 'owner'


async def am_I_admin_by_cache(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    role = role_cache[event.self_id][event.group_id]
    return role == 'admin' or role == 'owner'


def can_roulette_start(group_id: int) -> bool:
    if roulette_status[group_id] == 0 or time.time() - roulette_time[group_id] > timeout:
        return True

    return False


async def participate_in_roulette(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    '''
    牛牛自己是否参与轮盘
    '''
    if BotConfig(event.self_id, event.group_id).drunkenness() <= 0:
        return False

    if roulette_type[event.group_id] == 1:
        # 没法禁言自己
        return False

    # 群主退不了群（除非解散），所以群主牛牛不参与游戏
    return role_cache[event.self_id][event.group_id] != 'owner'


async def roulette(messagae_handle, bot: Bot, event: GroupMessageEvent, state: T_State):
    rand = random.randint(1, 6)
    logger.info('Roulette rand: {}'.format(rand))
    roulette_status[event.group_id] = rand
    roulette_count[event.group_id] = 0
    roulette_time[event.group_id] = time.time()
    roulette_player[event.group_id] = [event.user_id, ]
    partin = await participate_in_roulette(bot, event, state)
    if partin:
        roulette_player[event.group_id].append(event.self_id)

    if roulette_type[event.group_id] == 0:
        type_msg = '踢出群聊'
    elif roulette_type[event.group_id] == 1:
        type_msg = '禁言'
    await messagae_handle.finish(
        f'这是一把充满荣耀与死亡的左轮手枪，六个弹槽只有一颗子弹，中弹的那个人将会被{type_msg}。勇敢的战士们啊，扣动你们的扳机吧！')


async def is_roulette_type_msg(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    if event.raw_message in ['牛牛轮盘踢人', '牛牛轮盘禁言', '牛牛踢人轮盘', '牛牛禁言轮盘']:
        return can_roulette_start(event.group_id)
    return False


async def is_config_admin(event: GroupMessageEvent) -> bool:
    return BotConfig(event.self_id).is_admin(event.user_id)

IsAdmin = permission.GROUP_OWNER | permission.GROUP_ADMIN | Permission(
    is_config_admin)


roulette_type_msg = on_message(
    priority=5,
    block=True,
    rule=Rule(is_roulette_type_msg) & Rule(am_I_admin),
    permission=IsAdmin
)


@roulette_type_msg.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    if '踢人' in event.raw_message:
        roulette_type[event.group_id] = 0
    elif '禁言' in event.raw_message:
        roulette_type[event.group_id] = 1

    await roulette(roulette_type_msg, bot, event, state)


async def is_roulette_msg(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    if event.raw_message in ['牛牛轮盘']:
        return can_roulette_start(event.group_id)

    return False


roulette_msg = on_message(
    priority=5,
    block=True,
    rule=Rule(is_roulette_msg) & Rule(am_I_admin),
    permission=permission.GROUP
)


@roulette_msg.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    await roulette(roulette_msg, bot, event, state)


async def is_shot_msg(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    return event.raw_message == '牛牛开枪' and roulette_status[event.group_id] != 0


async def is_can_kick(self_id: int, user_id: int, group_id: int) -> bool:
    if self_id == user_id:
        return True
    user_info = await get_bot(str(self_id)).call_api('get_group_member_info', **{
        'user_id': user_id,
        'group_id': group_id
    })
    if user_info['role'] == 'owner':
        return False
    elif user_info['role'] == 'admin':
        role = role_cache[self_id][group_id]
        if role != 'owner':
            return False

    return True


async def kick(self_id: int, user_id: int, group_id: int):
    if self_id == user_id:
        await get_bot(str(self_id)).call_api('set_group_leave', **{
            'group_id': group_id
        })
        return

    await get_bot(str(self_id)).call_api('set_group_kick', **{
        'user_id': user_id,
        'group_id': group_id
    })


async def shutup(self_id: int, user_id: int, group_id: int):
    await get_bot(str(self_id)).call_api('set_group_ban', **{
        'user_id': user_id,
        'group_id': group_id,
        'duration': random.randint(5, 20) * 60
    })

shot_msg = on_message(
    priority=5,
    block=True,
    rule=Rule(is_shot_msg) & Rule(am_I_admin_by_cache),
    permission=permission.GROUP
)

shot_text = [
    '无需退路。( 1 / 6 )',
    '英雄们啊，为这最强大的信念，请站在我们这边。( 2 / 6 )',
    '颤抖吧，在真正的勇敢面前。( 3 / 6 )',
    '哭嚎吧，为你们不堪一击的信念。( 4 / 6 )',
    '现在可没有后悔的余地了。( 5 / 6 )']


@shot_msg.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    roulette_status[event.group_id] -= 1
    can_kick = False
    roulette_count[event.group_id] += 1
    count = roulette_count[event.group_id]
    roulette_time[event.group_id] = time.time()
    roulette_player[event.group_id].append(event.user_id)

    if count == 6 and random.random() < 0.125:
        roulette_status[event.group_id] = 0
        roulette_player[event.group_id] = []
        reply_msg = '我的手中的这把武器，找了无数工匠都难以修缮如新。不......不该如此......'

    elif roulette_status[event.group_id] <= 0:
        roulette_status[event.group_id] = 0
        if BotConfig(event.self_id, event.group_id).drunkenness() > 0:
            shot_user = random.choice(roulette_player[event.group_id])
        else:
            shot_user = event.user_id
        can_kick = await is_can_kick(event.self_id, shot_user, event.group_id)
        if can_kick:
            reply_msg = MessageSegment.text('米诺斯英雄们的故事......有喜剧，便也会有悲剧。舍弃了荣耀，') + MessageSegment.at(
                shot_user) + MessageSegment.text('选择回归平凡......')
        else:
            reply_msg = '听啊，悲鸣停止了。这是幸福的和平到来前的宁静。'

        roulette_player[event.group_id] = []

    else:
        reply_msg = shot_text[count - 1]

    await roulette_msg.send(reply_msg)
    if can_kick:
        if roulette_type[event.group_id] == 0:
            await kick(event.self_id, shot_user, event.group_id)
        elif roulette_type[event.group_id] == 1:
            await shutup(event.self_id, shot_user, event.group_id)


async def is_drunk(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    return BotConfig(event.self_id, event.group_id).drunkenness() > 0 and roulette_status[event.group_id] != 0


player_msg = on_message(
    priority=4,  # 这里的优先级比“牛牛开枪”高，也就是说发送“牛牛开枪”的人会在数组中会出现两次，增加概率
    block=False,
    rule=Rule(is_drunk) & Rule(am_I_admin_by_cache),
    permission=permission.GROUP
)


@player_msg.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    roulette_player[event.group_id].append(event.user_id)
