import os
import httpx
import io
import logging
import json
import requests
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Depends, Header
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, CSVLoader, UnstructuredMarkdownLoader, JSONLoader, UnstructuredWordDocumentLoader, UnstructuredExcelLoader, UnstructuredPowerPointLoader
from langchain_community.vectorstores import Redis
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnableLambda
from app.utils.config_llm import config_llm
from app.utils.custom_loader import CustomDocumentLoader
from typing_extensions import Annotated

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = "http://intelligenceapi-auth/verify"

async def verify_token(x_token: Annotated[str | None, Header()] = None) -> None:
    if not x_token:
        raise HTTPException(status_code=401, detail="X-Token header missing")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(AUTH_SERVICE_URL, headers={"Authorization": f"Bearer {x_token}"})
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="X-Token header invalid")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Auth service error: {str(e)}")

app = FastAPI(
    title="IntelligenceAPI Storage API",
    description="Storage API for file management",
    version="0.1.0",
    openapi_version="3.0.0",
)

# 환경 변수 설정
STORAGE_PROVIDER = os.getenv("STORAGE_PROVIDER")

if STORAGE_PROVIDER == "s3":
    import boto3
    from botocore.exceptions import NoCredentialsError

    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )
    BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

    def list_files():
        try:
            response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
            return [content['Key'] for content in response.get('Contents', [])]
        except NoCredentialsError:
            return []

    def upload_file(file_obj, object_name):
        try:
            s3_client.upload_fileobj(file_obj, BUCKET_NAME, object_name)
            return True
        except NoCredentialsError:
            return False

    def download_file(object_name):
        try:
            file_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=object_name)['Body']
            return file_obj.read()
        except NoCredentialsError:
            return None

    def delete_file(object_name):
        try:
            s3_client.delete_object(Bucket=BUCKET_NAME, Key=object_name)
            return True
        except NoCredentialsError:
            return False

elif STORAGE_PROVIDER == "azureblob":
    from azure.storage.blob import BlobServiceClient

    azure_blob_service_client = BlobServiceClient.from_connection_string(os.getenv("AZURE_CONNECTION_STRING"))
    container_name = os.getenv("AZURE_CONTAINER_NAME")
    account_name = os.getenv("AZURE_ACCOUNT_NAME")

    def list_files():
        try:
            container_client = azure_blob_service_client.get_container_client(container_name)
            return [blob.name for blob in container_client.list_blobs()]
        except Exception as e:
            return []

    def upload_file(file_obj, blob_name):
        try:
            blob_client = azure_blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            blob_client.upload_blob(file_obj, overwrite=True)
            return True
        except Exception as e:
            return False

    def download_file(blob_name):
        try:
            blob_client = azure_blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            download_stream = blob_client.download_blob()
            return download_stream.readall()
        except Exception as e:
            return None

    def delete_file(blob_name):
        try:
            blob_client = azure_blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            blob_client.delete_blob()
            return True
        except Exception as e:
            return False

else:
    raise ValueError("Unsupported STORAGE_PROVIDER value. Use 's3' or 'azureblob'.")

@app.get("/dashboard")
async def dashboard(request: Request):
    files = list_files()
    file_list_html = "".join(f"""
        <tr>
            <td>{file}</td>
            <td><button onclick="downloadFile('{file}')">Download</button></td>
            <td><button onclick="deleteFile('{file}')">Delete</button></td>
        </tr>
    """ for file in files)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>File Management Dashboard</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                margin-top: 50px;
            }}
            .container {{
                text-align: center;
                background: white;
                padding: 2em;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            }}
            input[type="file"], input[type="text"] {{
                margin: 1em 0;
            }}
            button {{
                padding: 0.5em 1em;
                margin: 0.5em;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 1em 0;
            }}
            th, td {{
                padding: 1em;
                border: 1px solid #ddd;
            }}
            th {{
                background-color: #f4f4f4;
            }}
            #tokenPopup {{
                display: none;
                position: fixed;
                left: 50%;
                top: 50%;
                transform: translate(-50%, -50%);
                background: white;
                padding: 2em;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                z-index: 1000;
            }}
            #overlay {{
                display: none;
                position: fixed;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                z-index: 999;
            }}
        </style>
    </head>
    <body>
        <div id="overlay"></div>
        <div id="tokenPopup">
            <h1>Enter Your Token</h1>
            <input type="text" id="tokenInput" placeholder="Enter your token">
            <button onclick="saveToken()">Save Token</button>
            <p id="popupMessage"></p>
        </div>
        <div class="container">
            <h1>File Management Dashboard</h1>
            <p>Welcome!</p>
            <input type="file" id="fileInput">
            <button onclick="uploadFile()">Upload File</button>
            <button onclick="embedAllFiles()">Embed All Files to MongoDB</button>
            <h2>Uploaded Files</h2>
            <table>
                <thead>
                    <tr>
                        <th>Filename</th>
                        <th>Download</th>
                        <th>Delete</th>
                    </tr>
                </thead>
                <tbody>
                    {file_list_html}
                </tbody>
            </table>
            <p id="message"></p>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', (event) => {{
                const token = localStorage.getItem('token');
                if (!token) {{
                    showTokenPopup();
                }}
            }});

            function showTokenPopup() {{
                document.getElementById('overlay').style.display = 'block';
                document.getElementById('tokenPopup').style.display = 'block';
            }}

            function hideTokenPopup() {{
                document.getElementById('overlay').style.display = 'none';
                document.getElementById('tokenPopup').style.display = 'none';
            }}

            function saveToken() {{
                const token = document.getElementById('tokenInput').value;
                if (token) {{
                    localStorage.setItem('token', token);
                    hideTokenPopup();
                    document.getElementById('message').textContent = 'Token saved!';
                }} else {{
                    document.getElementById('popupMessage').textContent = 'Token is required!';
                }}
            }}

            async function uploadFile() {{
                const fileInput = document.getElementById('fileInput');
                const file = fileInput.files[0];
                const formData = new FormData();
                formData.append('file', file);

                const token = localStorage.getItem('token');
                if (!token) {{
                    document.getElementById('message').textContent = 'Token is required!';
                    showTokenPopup();
                    return;
                }}

                const response = await fetch('/storage/upload/', {{
                    method: 'POST',
                    body: formData,
                    headers: {{
                        'x-token': token
                    }}
                }});

                const result = await response.json();
                document.getElementById('message').textContent = result.message || result.detail;
                if (response.ok) {{
                    location.reload();
                }}
            }}

            async function downloadFile(filename) {{
                const token = localStorage.getItem('token');
                if (!token) {{
                    document.getElementById('message').textContent = 'Token is required!';
                    showTokenPopup();
                    return;
                }}

                const response = await fetch(`/storage/download/${{filename}}`, {{
                    method: 'GET',
                    headers: {{
                        'x-token': token
                    }}
                }});

                if (response.ok) {{
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                }} else {{
                    const result = await response.json();
                    document.getElementById('message').textContent = result.detail;
                }}
            }}

            async function deleteFile(filename) {{
                const token = localStorage.getItem('token');
                if (!token) {{
                    document.getElementById('message').textContent = 'Token is required!';
                    showTokenPopup();
                    return;
                }}

                const response = await fetch(`/storage/delete/${{filename}}`, {{
                    method: 'DELETE',
                    headers: {{
                        'x-token': token
                    }}
                }});

                const result = await response.json();
                document.getElementById('message').textContent = result.message || result.detail;
                if (response.ok) {{
                    location.reload();
                }}
            }}

            async function embedAllFiles() {{
                const token = localStorage.getItem('token');
                if (!token) {{
                    document.getElementById('message').textContent = 'Token is required!';
                    showTokenPopup();
                    return;
                }}

                const response = await fetch('/storage/embed_all/', {{
                    method: 'POST',
                    headers: {{
                        'x-token': token
                    }}
                }});

                const result = await response.json();
                document.getElementById('message').textContent = result.message || result.detail;
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# 파일 업로드 엔드포인트
@app.post("/upload/", dependencies=[Depends(verify_token)])
async def upload_file_endpoint(file: UploadFile = File(...)):
    if upload_file(file.file, file.filename):
        return {"message": "File uploaded successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to upload file")

# 파일 다운로드 엔드포인트
@app.get("/download/{filename}", dependencies=[Depends(verify_token)])
async def download_file_endpoint(filename: str):
    file_content = download_file(filename)
    if file_content:
        return StreamingResponse(io.BytesIO(file_content), media_type="application/octet-stream")
    else:
        raise HTTPException(status_code=404, detail="File not found")

# 파일 삭제 엔드포인트
@app.delete("/delete/{filename}", dependencies=[Depends(verify_token)])
async def delete_file_endpoint(filename: str):
    if delete_file(filename):
        return {"message": "File deleted successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to delete file")

# Redis 임베딩 설정
REDIS_URL = os.getenv("REDIS_URL")
INDEX_NAME = os.getenv("REDIS_INDEX_NAME", "default")
OPENAPI_INDEX_NAME = "help"
INDEX_SCHEMA = {
    "text_embedding": "VECTOR",
    "metadata": "JSON",
}

config_llm.initialize_llm_from_env()
config_llm.initialize_embedding_from_env()
embedding = config_llm.get_embedding()

def _ingest(file_path: str, index_name: str = INDEX_NAME) -> dict:
    # 파일 타입에 맞는 로더 선택
    if file_path.endswith('.pdf'):
        loader = PyPDFLoader(file_path)
    elif file_path.endswith('.csv'):
        loader = CSVLoader(file_path)
    elif file_path.endswith('.md'):
        loader = UnstructuredMarkdownLoader(file_path)
    elif file_path.endswith('.json'):
        loader = JSONLoader(file_path, jq_schema='.', text_content=False)
    elif file_path.endswith('.txt'):
        loader = CustomDocumentLoader(file_path)
    elif file_path.endswith('.docx'):
        loader = UnstructuredWordDocumentLoader(file_path)
    elif file_path.endswith('.xlsx'):
        loader = UnstructuredExcelLoader(file_path, mode="elements")
    elif file_path.endswith('.pptx'):
        loader = UnstructuredPowerPointLoader(file_path)
    else:
        raise ValueError("Unsupported file type")

    data = loader.load()

    # 문서 분할
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=100, add_start_index=True)
    docs = text_splitter.split_documents(data)

    # Redis에 문서 삽입
    _ = Redis.from_texts(
        texts=[doc.page_content for doc in docs],
        metadatas=[doc.metadata for doc in docs],
        embedding=embedding,
        index_name=index_name,
        index_schema=INDEX_SCHEMA,
        redis_url=REDIS_URL,
    )
    return {}

ingest = RunnableLambda(_ingest)

def _ingest_all_files():
    if STORAGE_PROVIDER == "s3":
        files = list_files()
        for file in files:
            file_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=file)['Body']
            file_content = file_obj.read()
            file_path = f"/tmp/{file}"
            with open(file_path, 'wb') as f:
                f.write(file_content)
            _ingest(file_path)
    elif STORAGE_PROVIDER == "azureblob":
        files = list_files()
        for file in files:
            blob_client = azure_blob_service_client.get_blob_client(container=container_name, blob=file)
            download_stream = blob_client.download_blob()
            file_content = download_stream.readall()
            file_path = f"/tmp/{file}"
            with open(file_path, 'wb') as f:
                f.write(file_content)
            _ingest(file_path)
    else:
        raise ValueError("Unsupported STORAGE_PROVIDER value.")

    return {"message": "All files ingested successfully"}

@app.post("/embed_all/", dependencies=[Depends(verify_token)])
async def embed_all_files():
    try:
        result = _ingest_all_files()
        return result
    except Exception as e:
        logger.error(f"Error embedding all files: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.on_event("startup")
async def startup_event():
    try:
        response = requests.get("http://intelligenceapi-gatewayapi/openapi.json")
        if response.status_code != 200:
            raise Exception("Failed to fetch openapi.json")

        openapi_data = response.json()
        file_path = "/tmp/openapi.json"
        with open(file_path, 'w') as f:
            json.dump(openapi_data, f)

        _ingest(file_path, index_name=OPENAPI_INDEX_NAME)
    except Exception as e:
        logger.error(f"Error ingesting OpenAPI JSON on startup: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)