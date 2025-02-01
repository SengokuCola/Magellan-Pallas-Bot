import random
import asyncio
import re
import time
import threading

from nonebot import on_message, require, get_bot, logger, get_driver
from nonebot.exception import ActionFailed
from nonebot.typing import T_State
from nonebot.rule import keyword, to_me, Rule
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.onebot.v11 import permission, Message, MessageSegment
from nonebot.permission import Permission
from nonebot.permission import SUPERUSER
from src.common.config import BotConfig
from src.common.utils.media_cache import insert_image, get_image

from .model import Chat

any_msg = on_message(
    priority=15,
    block=False,
    permission=permission.GROUP  # | permission.PRIVATE_FRIEND
)


async def is_shutup(self_id: int, group_id: int) -> bool:
    info = await get_bot(str(self_id)).call_api('get_group_member_info', **{
        'user_id': self_id,
        'group_id': group_id
    })
    flag: bool = info['shut_up_timestamp'] > time.time()

    logger.info('bot [{}] in group [{}] is shutup: {}'.format(
        self_id, group_id, flag))

    return flag

message_id_lock = threading.Lock()
message_id_dict = {}


async def post_proc(message: Message, self_id: int, group_id: int) -> Message:
    new_msg = Message()
    for seg in message:
        if seg.type == 'at':
            try:
                info = await get_bot(str(self_id)).call_api('get_group_member_info', **{
                    'user_id': seg.data['qq'],
                    'group_id': group_id
                })
            except ActionFailed:    # 群员不存在
                continue
            nick_name = info['card'] if info['card'] else info['nickname']
            new_msg += '@{}'.format(nick_name)
        elif seg.type == 'image':
            cq_code = str(seg)
            base64_data = get_image(cq_code)
            if base64_data:
                new_msg += MessageSegment.image(file=base64_data)
            else:
                new_msg += seg
        else:
            new_msg += seg

    return new_msg


@any_msg.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    # 处理多账号登录时的消息去重
    to_learn = True
    # 使用锁来保证线程安全
    with message_id_lock:
        message_id = event.message_id
        group_id = event.group_id
        # 检查消息是否已经处理过
        if group_id in message_id_dict:
            if message_id in message_id_dict[group_id]:
                to_learn = False
        else:
            message_id_dict[group_id] = []

        # 记录消息ID并限制缓存大小
        group_message = message_id_dict[group_id]
        group_message.append(message_id)
        if len(group_message) > 100:
            group_message = group_message[:-10]

    # 创建聊天对象
    chat: Chat = Chat(event)

    # 检查是否可以回复消息
    answers = None
    config = BotConfig(event.self_id, event.group_id)
    if config.is_cooldown('repeat'):
        answers = chat.answer()

    # 学习新消息
    if to_learn:
        for seg in event.message:
            if seg.type == "image":
                await insert_image(seg)
                
        chat.learn()

    if not answers:
        return

    # 发送回复消息
    config.refresh_cooldown('repeat')
    delay = random.randint(1, 4)
    for item in answers:
        # 处理消息中的特殊内容(如@)
        msg = await post_proc(item, event.self_id, event.group_id)
        logger.info(
            'bot [{}] ready to send [{}] to group [{}]'.format(event.self_id, str(msg)[:30], event.group_id))

        # 随机延迟发送
        await asyncio.sleep(delay)
        config.refresh_cooldown('repeat')
        try:
            await any_msg.send(msg)  # 使用 any_msg 事件处理器发送消息到群聊
        except ActionFailed:
            # 消息发送失败的处理
            if not BotConfig(event.self_id).security():
                continue

            # 检查是否是因为bot被禁言导致的失败
            shutup = await is_shutup(event.self_id, event.group_id)
            if not shutup:  # 说明这条消息本身有问题
                logger.info('bot [{}] ready to ban [{}] in group [{}]'.format(
                    event.self_id, str(item), event.group_id))
                Chat.ban(event.group_id, event.self_id,
                         str(item), 'ActionFailed')
                break
        delay = random.randint(1, 3)


async def is_config_admin(event: GroupMessageEvent) -> bool:
    return BotConfig(event.self_id).is_admin_of_bot(event.user_id)

IsAdmin = permission.GROUP_OWNER | permission.GROUP_ADMIN | SUPERUSER | Permission(
    is_config_admin)


async def is_reply(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    return bool(event.reply)

ban_msg = on_message(
    rule=to_me() & keyword('不可以') & Rule(is_reply),
    priority=5,
    block=True,
    permission=IsAdmin
)


@ban_msg.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):

    if '[CQ:reply,' not in event.raw_message:
        return False

    raw_message = ''
    for item in event.reply.message:
        raw_reply = str(item)
        # 去掉图片消息中的 url, subType 等字段
        raw_message += re.sub(r'(\[CQ\:.+)(?:,url=*)(\])',
                              r'\1\2', raw_reply)

    logger.info('bot [{}] ready to ban [{}] in group [{}]'.format(
        event.self_id, raw_message, event.group_id))

    if Chat.ban(event.group_id, event.self_id, raw_message, str(event.user_id)):
        await ban_msg.finish('这对角可能会不小心撞倒些家具，我会尽量小心。')


speak_sched = require('nonebot_plugin_apscheduler').scheduler


async def message_is_ban(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    return event.get_plaintext().strip() == '不可以发这个'

ban_msg_latest = on_message(
    rule=to_me() & Rule(message_is_ban),
    priority=5,
    block=True,
    permission=IsAdmin
)


@ban_msg_latest.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    logger.info(
        'bot [{}] ready to ban latest reply in group [{}]'.format(
            event.self_id, event.group_id))

    if Chat.ban(event.group_id, event.self_id, '', str(event.user_id)):
        await ban_msg_latest.finish('这对角可能会不小心撞倒些家具，我会尽量小心。')


@speak_sched.scheduled_job('interval', seconds=60)
async def speak_up():
    """主动发言"""
    result = Chat.speak()
    if not result:
        return
    bot_id, group_id, messages = result
    
    # 确保消息是字符串或Message对象
    for msg in messages:
        try:
            # 如果是Message对象，转换为字典
            if isinstance(msg, Message):
                message = msg.dict()
            # 如果是字符串，直接使用
            elif isinstance(msg, str):
                message = msg
            else:
                print(f"[警告] 跳过不支持的消息类型: {type(msg)}")
                continue
                
            await get_bot(str(bot_id)).call_api('send_group_msg', **{
                'group_id': group_id,
                'message': message
            })
            
            # 每条消息之间稍微等待一下
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            print(f"[错误] 发送消息失败: {str(e)}")
            continue


update_sched = require('nonebot_plugin_apscheduler').scheduler


@update_sched.scheduled_job('cron', hour='4')
def update_data():
    Chat.sync()
    Chat.clearup_context()
