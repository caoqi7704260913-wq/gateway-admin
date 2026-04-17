###
# 用户服务
##
from fastapi import FastAPI,Response
from config.settings import settings, BASE_DIR
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from loguru import logger

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
)





if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
          "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.is_debug,
    )
    # log.info(f"{settings.APP_NAME} started at {settings.HOST}:{settings.PORT}")


