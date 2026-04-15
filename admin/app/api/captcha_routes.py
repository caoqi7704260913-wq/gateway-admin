"""验证码路由"""
import base64
import io
import random
import string
from fastapi import APIRouter, HTTPException
from loguru import logger
from captcha.image import ImageCaptcha

router = APIRouter(prefix="/captcha", tags=["验证码"])

# 存储验证码（生产环境应使用 Redis）
captcha_store = {}


@router.get("/generate")
async def generate_captcha():
    """生成验证码图片"""
    # 生成4位随机验证码
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # 生成唯一ID
    captcha_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=32))
    
    # 生成验证码图片
    image = ImageCaptcha(width=120, height=40)
    data = image.generate(code)
    
    # 转换为 base64
    image_base64 = base64.b64encode(data.read()).decode('utf-8')
    
    # 存储验证码（5分钟过期）
    captcha_store[captcha_id] = {
        'code': code.lower(),
        'created_at': __import__('time').time()
    }
    
    # 清理过期验证码
    now = __import__('time').time()
    expired_keys = [k for k, v in captcha_store.items() if now - v['created_at'] > 300]
    for key in expired_keys:
        del captcha_store[key]
    
    logger.info(f"生成验证码: ID={captcha_id[:8]}..., Code={code}")
    
    return {
        'captcha_id': captcha_id,
        'image': f'data:image/png;base64,{image_base64}'
    }


@router.post("/verify")
async def verify_captcha(captcha_id: str, code: str):
    """验证验证码"""
    if captcha_id not in captcha_store:
        raise HTTPException(status_code=400, detail="验证码已过期或不存在")
    
    stored = captcha_store[captcha_id]
    
    # 验证后删除（一次性使用）
    del captcha_store[captcha_id]
    
    if stored['code'] != code.lower():
        raise HTTPException(status_code=400, detail="验证码错误")
    
    return {'valid': True}
