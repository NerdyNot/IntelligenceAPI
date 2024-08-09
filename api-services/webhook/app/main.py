import httpx
import os
import json
from fastapi import FastAPI, Depends, Header, Request, HTTPException, Query
from typing import Optional

AUTH_SERVICE_URL = "http://intelligenceapi-auth/verify"
ANALYSIS_CSP_URL = "http://intelligenceapi-analysis/csp/invoke"
ANALYSIS_DEVOPS_URL = "http://intelligenceapi-analysis/devops/invoke"
SLACK_WEBHOOK_URL_CSP = os.getenv("SLACK_WEBHOOK_URL_CSP")
SLACK_WEBHOOK_URL_DEVOPS = os.getenv("SLACK_WEBHOOK_URL_DEVOPS")
MESSAGE_LANGUAGE = os.getenv("MESSAGE_LANGUAGE")

async def verify_token(token: str) -> None:
    """
    인증 서비스를 사용하여 토큰을 검증합니다.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(AUTH_SERVICE_URL, headers={"Authorization": f"Bearer {token}"})
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Token is invalid")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Auth service error: {str(e)}")

app = FastAPI(
    title="Intelligence Webhook API",
    description="This API provides IntelligenceAPI in the form of a Webhook.",
    version="0.1.0",
    openapi_version="3.0.0"
)

async def send_slack_message(message: str, webhook_url: str):
    """
    Slack 메시지를 전송하는 함수입니다.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            webhook_url,
            json={"text": message}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to send Slack message")

async def process_analysis(request: Request, token: str, analysis_url: str, slack_webhook_url: str):
    """
    분석 요청을 처리하고, 결과를 Slack 메시지로 전송합니다.
    """
    await verify_token(token)

    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid request body")

    payload_str = json.dumps(payload)

    analysis_payload = {
        "input": {
            "input": payload_str,
            "language": MESSAGE_LANGUAGE
        },
        "config": {},
        "kwargs": {}
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            analysis_url,
            json=analysis_payload,
            headers={"x-token": token}
        )
        if response.status_code != 200:
            detail = response.json()
            print("Error detail:", detail)
            raise HTTPException(status_code=response.status_code, detail=f"Failed to forward request: {detail}")

        result = response.json()

    output_message = result.get("output", "No output found")
    await send_slack_message(output_message, slack_webhook_url)

    return {"message": "Message sent successfully", "result": result}

@app.post("/csp-analysis", response_model=dict)
async def csp_analysis_endpoint(request: Request, x_token: Optional[str] = Header(None), token: Optional[str] = Query(None)):
    """
    CSP 분석 요청을 처리하는 엔드포인트입니다.
    """
    token = x_token or token
    if not token:
        raise HTTPException(status_code=401, detail="X-Token header or token query parameter required")
    return await process_analysis(request, token, ANALYSIS_CSP_URL, SLACK_WEBHOOK_URL_CSP)

@app.post("/devops-analysis", response_model=dict)
async def devops_analysis_endpoint(request: Request, x_token: Optional[str] = Header(None), token: Optional[str] = Query(None)):
    """
    DevOps 분석 요청을 처리하는 엔드포인트입니다.
    """
    token = x_token or token
    if not token:
        raise HTTPException(status_code=401, detail="X-Token header or token query parameter required")
    return await process_analysis(request, token, ANALYSIS_DEVOPS_URL, SLACK_WEBHOOK_URL_DEVOPS)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
