from fastapi import FastAPI
from app.utils.proxy import router as gateway_router
from app.utils.fetch_openapi import load_backend_openapi_specs

app = FastAPI(
    title="Intelligence Gateway API",
    version="0.1.0",
    description="Gateway to manage and route requests to various backend services",
    openapi_version="3.0.0"
)

app.include_router(gateway_router)

@app.on_event("startup")
async def on_startup():
    """
    애플리케이션 시작 시 백엔드 서비스의 OpenAPI 사양을 로드.
    """
    await load_backend_openapi_specs(app)

@app.get("/openapi.json", include_in_schema=False)
async def get_openapi():
    """
    결합된 OpenAPI 사양 반환.
    """
    return app.openapi_schema

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
