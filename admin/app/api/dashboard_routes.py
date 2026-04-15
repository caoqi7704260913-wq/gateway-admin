"""仪表盘路由"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.utils.database_pool import get_db_async
from app.models.schemas import Admin, Token

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])


@router.get("/stats")
async def get_dashboard_stats(session: AsyncSession = Depends(get_db_async)):
    """获取仪表盘统计数据"""
    # 用户总数
    result = await session.execute(select(func.count()).select_from(Admin))
    total_users = result.scalar() or 0
    
    # 今日访问（今天登录过的用户数）
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.count(func.distinct(Token.admin_id)))
        .where(Token.created_at >= today_start)
    )
    today_visits = result.scalar() or 0
    
    # 在线用户（30分钟内有活动的Token）
    active_time = datetime.now() - timedelta(minutes=30)
    result = await session.execute(
        select(func.count(func.distinct(Token.admin_id)))
        .where(Token.expires_at > datetime.now())
        .where(Token.created_at >= active_time)
    )
    online_users = result.scalar() or 0
    
    # 系统消息（暂时返回固定值）
    system_messages = 12
    
    return {
        'total_users': total_users,
        'today_visits': today_visits,
        'online_users': online_users,
        'system_messages': system_messages
    }
