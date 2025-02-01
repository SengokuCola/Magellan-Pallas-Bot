import time
import pymongo
from typing import Optional, Dict, List

class UserManager:
    def __init__(self):
        # 连接MongoDB
        self.client = pymongo.MongoClient('127.0.0.1', 27017)
        self.db = self.client['PallasBot']
        
        # 用户集合
        self.users = self.db['users']
        
        # 创建索引
        self.users.create_index([('user_id', pymongo.ASCENDING)], unique=True)
        self.users.create_index([('last_active', pymongo.DESCENDING)])
        self.users.create_index([('favorability', pymongo.DESCENDING)])
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """获取用户信息"""
        return self.users.find_one({'user_id': user_id})
    
    async def update_user_message(self, user_id: int, group_id: int, message: str) -> None:
        """更新用户消息记录"""
        current_time = int(time.time())
        
        # 更新用户信息
        self.users.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'last_active': current_time,
                    'last_group': group_id,
                    'last_message': message
                },
                '$push': {
                    'message_history': {
                        'time': current_time,
                        'group_id': group_id,
                        'message': message
                    }
                },
                '$setOnInsert': {
                    'join_time': current_time,
                    'favorability': 0,
                    'title': '陌生人',  # 默认称号
                }
            },
            upsert=True
        )
        
        # 限制消息历史记录数量
        self.users.update_one(
            {'user_id': user_id},
            {'$push': {'message_history': {'$each': [], '$slice': -100}}}  # 只保留最近100条
        )
    
    async def update_favorability(self, user_id: int, change: float) -> None:
        """更新好感度"""
        # 获取当前好感度
        user = await self.get_user(user_id)
        current_favor = user.get('favorability', 0) if user else 0
        new_favor = current_favor + change
        
        # 更新好感度和称号
        title = self._get_title(new_favor)
        self.users.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'favorability': new_favor,
                    'title': title
                }
            },
            upsert=True
        )
    
    def _get_title(self, favorability: float) -> str:
        """根据好感度返回称号"""
        if favorability >= 100:
            return "挚友"
        elif favorability >= 80:
            return "密友"
        elif favorability >= 60:
            return "好友"
        elif favorability >= 40:
            return "朋友"
        elif favorability >= 20:
            return "熟人"
        elif favorability >= 0:
            return "陌生人"
        else:
            return "讨厌鬼"
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """获取用户统计信息"""
        user = await self.get_user(user_id)
        if not user:
            return None
            
        message_count = len(user.get('message_history', []))
        active_days = (int(time.time()) - user['join_time']) // (24 * 3600)
        
        return {
            'user_id': user_id,
            'title': user.get('title', '陌生人'),
            'favorability': user.get('favorability', 0),
            'message_count': message_count,
            'active_days': active_days,
            'join_time': user['join_time'],
            'last_active': user.get('last_active', 0)
        }
    
    async def get_top_users(self, limit: int = 10) -> List[Dict]:
        """获取好感度排行榜"""
        return list(self.users.find(
            {},
            {'user_id': 1, 'favorability': 1, 'title': 1}
        ).sort('favorability', pymongo.DESCENDING).limit(limit)) 