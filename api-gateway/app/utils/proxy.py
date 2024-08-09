import httpx
from fastapi import APIRouter, Request, HTTPException, Response
from app.utils.servicelist import servicelist

router = APIRouter()

backend_urls = servicelist()

async def proxy_request(request: Request, backend_url: str) -> Response:
    """
    프록시 요청을 백엔드 서비스로 전달.
    """
    async with httpx.AsyncClient(timeout=300.0) as client:
        headers = dict(request.headers)
        method = request.method

        params = dict(request.query_params)

        try:
            if method == "POST":
                response = await client.post(backend_url, content=await request.body(), headers=headers, params=params)
            elif method == "GET":
                response = await client.get(backend_url, headers=headers, params=params)
            elif method == "PUT":
                response = await client.put(backend_url, content=await request.body(), headers=headers, params=params)
            elif method == "DELETE":
                response = await client.delete(backend_url, headers=headers, params=params)
            elif method == "PATCH":
                response = await client.patch(backend_url, content=await request.body(), headers=headers, params=params)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")

            return Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))
        except httpx.ConnectError as e:
            raise HTTPException(status_code=502, detail=f"Failed to connect to the backend service: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Backend service returned an error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"An error occurred while making the request: {str(e)}")

@router.api_route("/{service}/{path:path}", methods=["POST", "GET", "PUT", "DELETE", "PATCH"], include_in_schema=False)
async def gateway(service: str, path: str, request: Request):
    """
    요청을 해당 백엔드 서비스로 라우팅.
    """
    if service in backend_urls:
        backend_url = f"{backend_urls[service]}/{path}"
        return await proxy_request(request, backend_url)
    else:
        raise HTTPException(status_code=404, detail="Service not found")
