import random
import asyncio

from nonebot import on_message, require, get_bot, logger, get_driver
from nonebot.exception import ActionFailed
from nonebot.typing import T_State
from nonebot.rule import keyword, to_me, Rule
from nonebot.adapters import Bot, Event
from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.onebot.v11 import permission
from src.common.config import BotConfig, GroupConfig


async def is_drink_msg(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    return event.get_plaintext().strip() in ['麦麦喝酒', '麦麦干杯', '麦麦继续喝']

drink_msg = on_message(
    rule=Rule(is_drink_msg),
    priority=5,
    block=True,
    permission=permission.GROUP
)


@drink_msg.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    config = BotConfig(event.self_id, event.group_id, cooldown=3)
    if not config.is_cooldown('drink'):
        return
    config.refresh_cooldown('drink')

    drunk_duration = random.randint(60, 600)
    logger.info(
        'bot [{}] ready to drink in group [{}], sober up after {} sec'.format(
            event.self_id, event.group_id, drunk_duration))

    config.drink()
    drunkenness = config.drunkenness()
    go_to_sleep = random.random() < (
        0.02 if drunkenness <= 50
        else (drunkenness - 50 + 1) * 0.02)
    if go_to_sleep:
        # 35 是期望概率
        sleep_duration = (min(drunkenness, 35) + random.random()) * 800
        logger.info(
            'bot [{}] go to sleep in group [{}], wake up after {} sec'.format(
                event.self_id, event.group_id, sleep_duration))
        config.sleep(sleep_duration)

    try:
        if go_to_sleep:
            await drink_msg.send('嗝呜...博、博士，腾龙的惯性导航模块被替换成枫糖浆动力核心了？！明明校准了零下40°的极地参数...现在它居然在绕着我跳∞字热舞欸——')
            await asyncio.sleep(1)
            await drink_msg.send('Zzz……')
        else:
            await drink_msg.send('（信号溢出蜂蜜色噪点...）腾龙的导航协议被雪鸮拆解成华尔兹指令集了...哔——（＞▽＜）')
    except ActionFailed:
        pass

    await asyncio.sleep(drunk_duration)
    if config.sober_up() and not config.is_sleep():
        logger.info('bot [{}] sober up in group [{}]'.format(
            event.self_id, event.group_id))
        await drink_msg.finish('（通讯链路突然冻结三秒）博士...被精准捕获逻辑漏洞了呢(´•̥̥̥ω•̥̥̥`)')


update_sched = require('nonebot_plugin_apscheduler').scheduler


@update_sched.scheduled_job('cron', hour='4')
def update_data():
    BotConfig.fully_sober_up()
