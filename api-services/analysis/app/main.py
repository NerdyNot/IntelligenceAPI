import httpx
from fastapi import FastAPI, Depends, Header, HTTPException
from typing_extensions import Annotated
from app.utils.config_llm import config_llm
from app.utils.react_agent import agent
from pydantic import BaseModel, Field
from enum import Enum
from typing import Any
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langserve import add_routes

AUTH_SERVICE_URL = "http://intelligenceapi-auth/verify"

async def verify_token(x_token: Annotated[str, Header()]) -> None:
    """
    인증 서비스로 토큰을 검증.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(AUTH_SERVICE_URL, headers={"Authorization": f"Bearer {x_token}"})
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="X-Token header invalid")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Auth service error: {str(e)}")

app = FastAPI(
    title="Intelligence Analysis API",
    description="This API analyzes the input content and provides results.",
    version="0.1.0",
    openapi_version="3.0.0",
    dependencies=[Depends(verify_token)]
)

def create_chain(template: str):
    """
    LLM 체인을 생성.
    """
    config_llm.initialize_llm_from_env()
    llm = config_llm.get_llm()
    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    return chain

add_routes(
    app,
    create_chain('''
                    Your Cloud Service Alert Analyzer.
                    Please create a brief report based on the analysis result of the input.: {input}
                    Analysis Result Report Language: {language}
    '''),
    path="/csp",
)

add_routes(
    app,
    create_chain('''
                    Your DevOps Alert Analyzer.
                    Please create a brief report based on the analysis result of the input.: {input}
                    Analysis Result Report Language: {language}
    '''),
    path="/devops",
)

class AnalysisTool(str, Enum):
    python_code_analysis = "Python Code Analysis"
    sql_analysis = "SQL Analysis"
    security_vulnerability_analysis = "Security Vulnerability Analysis"

class OutputFormat(str, Enum):
    detailed_report = "Detailed Report"
    simple_report = "Simple Report"
    json = "JSON"

class OutputLanguage(str, Enum):
    english = "English"
    korean = "Korean"

class AnalysisInput(BaseModel):
    input: str = Field(..., example="https://github.com/user/repository")
    analysis_tool: AnalysisTool = Field(..., example="Python Code Analysis")
    directory_path: str = Field("", example="src")
    pat: str = Field("", example="your-github-pat")
    branch: str = Field("main", example="main")
    output_format: OutputFormat = Field(..., example="Detailed Report")
    output_language: OutputLanguage = Field(..., example="English")

class Output(BaseModel):
    output: Any

agent_executor = agent()

add_routes(
    app,
    agent_executor.with_types(input_type=AnalysisInput, output_type=Output).with_config(
        {"run_name": "codeanalyzer_agent"}
    ),
    path="/code",
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
