import os
import logging
from langchain_openai import ChatOpenAI, OpenAIEmbeddings, AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_google_vertexai import VertexAIModelGarden
from langchain_google_vertexai.embeddings import VertexAIEmbeddings
from langchain_anthropic import ChatAnthropic

class ConfigLLM:
    def __init__(self):
        self.llm = None
        self.embedding = None

    def initialize_llm_from_env(self):
        """
        환경 변수에서 언어 모델을 초기화합니다.
        LLM 제공자, API 키, 모델 이름, 온도 설정을 환경 변수에서 가져와 적절한 언어 모델을 초기화합니다.
        """
        provider = os.getenv("LLM_PROVIDER")
        api_key = os.getenv("LLM_API_KEY")
        model = os.getenv("LLM_MODEL")
        temperature = float(os.getenv("LLM_TEMPERATURE", 0.5))
        
        if not provider or not api_key or not model:
            logging.error("LLM provider, API key, or model is not set in environment variables")
            return

        if provider == 'openai':
            os.environ["OPENAI_API_KEY"] = api_key
            self.llm = ChatOpenAI(model=model, temperature=temperature)
        elif provider == 'azure':
            endpoint = os.getenv('AZURE_ENDPOINT')
            api_version = os.getenv('AZURE_API_VERSION')
            deployment_name = model
            os.environ["AZURE_OPENAI_API_KEY"] = api_key
            if not endpoint or not deployment_name:
                logging.error("Azure endpoint or deployment name is not set")
                return
            self.llm = AzureChatOpenAI(
                azure_deployment=deployment_name,
                openai_api_version=api_version,
                temperature=temperature,
                azure_endpoint=endpoint
            )
        elif provider == 'gemini':
            os.environ["GOOGLE_API_KEY"] = api_key
            self.llm = ChatGoogleGenerativeAI(model=model, temperature=temperature)
        elif provider == 'vertexai':
            os.environ["GOOGLE_API_KEY"] = api_key
            self.llm = VertexAIModelGarden(model=model, temperature=temperature)
        elif provider == 'anthropic':
            os.environ["ANTHROPIC_API_KEY"] = api_key
            self.llm = ChatAnthropic(model=model, temperature=temperature)
        else:
            logging.warning(f"Unsupported LLM provider: {provider}")
            return
        logging.info("LLM initialized successfully")

    def initialize_embedding_from_env(self):
        """
        환경 변수에서 임베딩 모델을 초기화합니다.
        임베딩 제공자, API 키, 모델 이름을 환경 변수에서 가져와 적절한 임베딩 모델을 초기화합니다.
        """
        provider = os.getenv("EMBEDDING_PROVIDER")
        api_key = os.getenv("EMBEDDING_API_KEY")
        model = os.getenv("EMBEDDING_MODEL")

        if not provider or not api_key or not model:
            logging.error("Embedding provider, API key, or model is not set in environment variables")
            return

        if provider == 'openai':
            os.environ["OPENAI_API_KEY"] = api_key
            self.embedding = OpenAIEmbeddings(model=model)
        elif provider == 'azure':
            endpoint = os.getenv('AZURE_ENDPOINT')
            api_version = os.getenv('AZURE_API_VERSION', '2024-05-01-preview')
            deployment_name = model
            os.environ["AZURE_OPENAI_API_KEY"] = api_key
            if not endpoint or not deployment_name:
                logging.error("Azure endpoint or deployment name is not set")
                return
            self.embedding = AzureOpenAIEmbeddings(
                azure_deployment=deployment_name,
                openai_api_version=api_version,
                azure_endpoint=endpoint
            )
        elif provider == 'gemini':
            os.environ["GOOGLE_API_KEY"] = api_key
            self.embedding = GoogleGenerativeAIEmbeddings(model=model)
        elif provider == 'vertexai':
            os.environ["GOOGLE_API_KEY"] = api_key
            self.embedding = VertexAIEmbeddings(model=model)
        else:
            logging.warning(f"Unsupported embedding provider: {provider}")
            return
        logging.info("Embedding model initialized successfully")

    def get_llm(self):
        """
        초기화된 언어 모델을 가져옵니다.
        언어 모델이 초기화되지 않은 경우 오류를 로그로 기록합니다.
        """
        if self.llm is None:
            logging.error("LLM is not initialized")
        return self.llm

    def get_embedding(self):
        """
        초기화된 임베딩 모델을 가져옵니다.
        임베딩 모델이 초기화되지 않은 경우 오류를 로그로 기록합니다.
        """
        if self.embedding is None:
            logging.error("Embedding is not initialized")
        return self.embedding

config_llm = ConfigLLM()
