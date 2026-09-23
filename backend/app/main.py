from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .llm import llm_client
from .routers import auth, reports, tests


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    if llm_client.mock:
        print("[提示] 未配置 LLM_API_KEY，当前运行在模拟模式（内置题库+模板报告）。")
        print("       在 backend/.env 中配置智谱 API Key 后重启，即可启用真实 AI。")
    else:
        print(f"[启动] 已接入大模型：{settings.llm_model} @ {settings.llm_base_url}")
    yield


app = FastAPI(title="AI 动态 MBTI 测试系统", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(tests.router, prefix="/api/tests", tags=["测试"])
app.include_router(reports.router, prefix="/api/reports", tags=["报告"])


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm_mode": "mock" if llm_client.mock else "real",
        "model": settings.llm_model,
    }
