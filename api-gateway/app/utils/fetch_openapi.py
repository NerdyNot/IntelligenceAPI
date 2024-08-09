import httpx
import asyncio
from fastapi import FastAPI
from app.utils.servicelist import servicelist
import logging

logger = logging.getLogger(__name__)

backend_urls = servicelist()

async def fetch_openapi_spec(service_name: str, service_url: str):
    """
    백엔드 서비스에서 OpenAPI 사양을 가져옴.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{service_url}/openapi.json")
            response.raise_for_status()
            return service_name, response.json()
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Failed to fetch OpenAPI spec from {service_name} at {service_url}: {e}")
        return service_name, {}

async def load_backend_openapi_specs(app: FastAPI):
    """
    모든 백엔드 서비스에서 OpenAPI 사양을 로드하고 하나로 결합.
    """
    specs = await asyncio.gather(
        *[fetch_openapi_spec(name, url) for name, url in backend_urls.items()]
    )

    combined_spec = app.openapi()

    if "components" not in combined_spec:
        combined_spec["components"] = {}
    
    if "tags" not in combined_spec:
        combined_spec["tags"] = []

    for service_name, spec in specs:
        if not spec:
            logger.warning(f"Skipping service {service_name} due to missing or invalid OpenAPI spec.")
            continue
        
        for path, path_spec in spec.get("paths", {}).items():
            for method, operation in path_spec.items():
                if "tags" in operation:
                    operation["tags"] = [f"/{service_name}/{tag}" for tag in operation["tags"]]
                else:
                    operation["tags"] = [f"/{service_name}"]
            combined_spec["paths"][f"/{service_name}{path}"] = path_spec

        for component_name, component_spec in spec.get("components", {}).items():
            if component_name not in combined_spec["components"]:
                combined_spec["components"][component_name] = component_spec
            else:
                combined_spec["components"][component_name].update(component_spec)

    app.openapi_schema = combined_spec
