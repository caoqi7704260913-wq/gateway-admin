"""
服务注册到 Gateway
"""
import asyncio
from loguru import logger
from config import settings
from app.utils.http_client import http_client


class RegisterService:
    
    def __init__(self):
        self.gateway_url = settings.GATEWAY_URL
        self.service_info = {
            "name": settings.SERVICE_NAME,
            "host": settings.HOST,
            "ip": settings.SERVICE_IP,
            "port": settings.PORT,
            "url": f"http://{settings.SERVICE_IP}:{settings.PORT}",
            "weight": settings.SERVICE_WEIGHT,
            "metadata": {
                "tags": settings.SERVICE_TAGS.split(","),
                "description": settings.SERVICE_DESCRIPTION
            }
        }
        self._registered = False
    
    async def register(self) -> bool:
        """注册到 Gateway"""
        try:
            response = await http_client.post(
                f"{self.gateway_url}/api/services/register",
                json=self.service_info,
                timeout=5.0
            )
            if response.status_code == 200:
                result = response.json()
                self.service_info["id"] = result.get("service_id")
                self._registered = True
                logger.info(f"Admin service registered: {result}")
                return True
            else:
                logger.error(f"Failed to register: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to register to Gateway: {e}")
            return False
    
    async def unregister(self) -> bool:
        """从 Gateway 注销"""
        if not self._registered:
            return True
        try:
            response = await http_client.delete(
                f"{self.gateway_url}/api/services/{settings.SERVICE_NAME}",
                timeout=5.0
            )
            self._registered = False
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to unregister from Gateway: {e}")
            return False
    
    async def heartbeat(self):
        """心跳保活"""
        while True:
            await asyncio.sleep(25)
            try:
                logger.debug("Admin service heartbeat")
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")


register_service = RegisterService()
