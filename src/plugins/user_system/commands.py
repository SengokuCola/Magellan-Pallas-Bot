from nonebot import on_command
from nonebot.typing import T_State
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from .user_manager import UserManager

# 查看个人信息
user_info = on_command(
    "我的信息",
    aliases={"查看信息", "个人信息", "info", "用户信息", "好感信息"},
    priority=5,
    block=True
)

@user_info.handle()
async def handle_user_info(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_id = event.user_id
    user_manager = UserManager()
    stats = await user_manager.get_user_stats(user_id)
    
    if not stats:
        await user_info.finish("还没有你的相关记录呢...")
        return
        
    msg = f"""=== 你的个人信息 ===
🏷️称号：{stats['title']}
❤️好感度：{stats['favorability']:.1f}
📝消息数：{stats['message_count']}
📅活跃天数：{stats['active_days']}
================="""
    
    await user_info.finish(msg)

# 查看好感度排行榜
favor_rank = on_command(
    "好感度排行",
    aliases={"排行榜", "麦麦排行", "rank", "排名", "好感排行"},
    priority=5,
    block=True
)

@favor_rank.handle()
async def handle_favor_rank(bot: Bot, event: GroupMessageEvent, state: T_State):
    user_manager = UserManager()
    top_users = await user_manager.get_top_users(10)
    
    if not top_users:
        await favor_rank.finish("还没有任何记录呢...")
        return
        
    msg = "=== 好感度排行榜 TOP10 ===\n"
    for i, user in enumerate(top_users, 1):
        try:
            # 获取用户信息
            user_info = await bot.get_group_member_info(
                group_id=event.group_id,
                user_id=user['user_id']
            )
            nickname = user_info.get('card') or user_info.get('nickname', str(user['user_id']))
        except:
            nickname = str(user['user_id'])
            
        # 添加表情符号
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👑"
        msg += f"{medal} {i}. {nickname}({user['title']}) - {user['favorability']:.1f}\n"
    
    msg += "======================"
    await favor_rank.finish(msg) 