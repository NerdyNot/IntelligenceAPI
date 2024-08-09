import os
import httpx
import logging
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing_extensions import Annotated
from langchain_community.vectorstores import Redis
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from app.utils.config_llm import config_llm
from langserve import add_routes

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = "http://intelligenceapi-auth/verify"

async def verify_token(x_token: Annotated[str, Header()]) -> None:
    """
    인증 서비스를 사용하여 토큰을 검증합니다.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(AUTH_SERVICE_URL, headers={"Authorization": f"Bearer {x_token}"})
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="X-Token header invalid")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Auth service error: {str(e)}")

app = FastAPI(
    title="Intelligence Query API",
    description="This API service is designed to manage and route various intelligence-related queries to backend services. It serves as a gateway that aggregates multiple intelligence data sources, processes user inputs, and returns synthesized and actionable insights. Whether you are looking for simple responses, detailed analysis, translations, or specific data points, the Intelligence Query API seamlessly integrates with backend systems to provide accurate and efficient results.",
    version="0.1.0",
    openapi_version="3.0.0",
    dependencies=[Depends(verify_token)]
)

def initialize_llm_and_vectorstore(index_name):
    """
    주어진 인덱스 이름을 사용하여 LLM 및 Redis 벡터스토어를 초기화합니다.
    """
    config_llm.initialize_llm_from_env()
    config_llm.initialize_embedding_from_env()
    embedding = config_llm.get_embedding()
    llm = config_llm.get_llm()

    REDIS_URL = os.getenv("REDIS_URL")

    vectorstore = Redis(
        redis_url=REDIS_URL,
        index_name=index_name,
        embedding=embedding,
    )
    retriever = vectorstore.as_retriever()
    
    return llm, retriever

# 기본 벡터스토어 초기화
llm, retriever = initialize_llm_and_vectorstore(os.getenv("REDIS_INDEX_NAME", "default"))

# 도움말 벡터스토어 초기화
help_llm, help_retriever = initialize_llm_and_vectorstore("help")

def create_chain(template: str, use_chat_template=False, retriever=None):
    """
    주어진 프롬프트 템플릿과 선택적 retriever를 사용하여 체인을 생성합니다.
    """
    if use_chat_template:
        prompt = ChatPromptTemplate.from_template(template)
    else:
        prompt = PromptTemplate.from_template(template)

    if retriever:
        chain = (
            RunnableParallel({"context": retriever, "question": RunnablePassthrough()})
            | prompt
            | llm
            | StrOutputParser()
        )
    else:
        chain = prompt | llm | StrOutputParser()
    return chain

# 입력을 위한 타입 정의
class Question(BaseModel):
    __root__: str

docs_chain = create_chain(
    """Answer the question based only on the following context:
    {context}
    Question: {question}""",
    use_chat_template=True, retriever=retriever
).with_types(input_type=Question)

help_chain = create_chain(
    """Answer the how to use IntelligenceAPI question based only on the following context:
    {context}
    Question: {question}""",
    use_chat_template=True, retriever=help_retriever
).with_types(input_type=Question)

# Redis 쿼리를 위한 /docs 경로 추가
add_routes(
    app,
    docs_chain,
    path="/docs"
)

# 도움말 쿼리를 위한 /help 경로 추가
add_routes(
    app,
    help_chain,
    path="/help"
)

# 기존 체인 유지
add_routes(
    app,
    create_chain("Your IntelligenceAPI AI, Respond to user input based on facts.: {input}"),
    path="/llm"
)

add_routes(
    app,
    create_chain('''
                    You are a translator.
                    Translate the user's input according to the specified language.
                    Translation result only: user's input: {input}
                    target language: {language}
    '''),
    path="/translate"
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
