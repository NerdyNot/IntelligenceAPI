# Intelligence API

**[한국어 버전](#한국어-버전)** | **[English Version](#english-version)**

---
## 한국어 버전

Intelligence API는 LLM(Large Language Model)과 LangChain, LangServe를 이용한 AI 통합 API입니다. 이 API는 Kubernetes 환경에서 쉽게 배포할 수 있도록 Helm 차트를 제공하며, Istio를 사용한 네트워크 관리가 용이합니다. 다양한 환경과 통합하여 사용할 수 있도록 Gateway API를 통해 여러 백엔드 서비스로 라우팅됩니다.

![Architecture](/Resources/architecture.png)

## 주요 기능

### Gateway API
- LangChain 기반의 실제 서비스들을 라우팅하는 API입니다.
- Istio Gateway 및 Virtual Service와 연동되어 외부와 직접적으로 연결됩니다.
- `Analysis`, `Query`, `Webhook` 등 다양한 서비스에 대한 라우팅을 제공합니다.
- OpenAPI 문서 페이지(`Docs`, `Redoc` 엔드포인트)를 통해 백엔드 서비스에 대한 상세 문서 접근이 가능합니다.

### Analysis API
- 입력된 값에 대한 분석 결과를 생성하는 API입니다.
  - `/csp`: 클라우드 환경 알림 메시지 분석
  - `/devops`: DevOps 플랫폼 알림 메시지 분석
  - `/code`: GitHub 원격 저장소 코드 분석 (ReAct Agent 기반)

### Query API
- 입력된 질문에 대한 응답을 생성하는 API입니다.
  - `/llm`: 단순 LLM 모델을 이용한 질문 응답 생성
  - `/translate`: LLM 모델을 이용한 번역 생성
  - `/docs`: 문서 RAG(Storage API)를 통해 임베딩 된 내용 사용

### Webhook API
- 웹훅 POST 요청을 처리하는 API입니다.
  - Azure, AWS, GCP 등의 Alert Notification Webhook 처리
  - Azure DevOps 등의 Alert Notification Webhook 처리
  - POST Body값을 받아서 Analysis API 등으로 내용을 전달 후 결과를 슬랙 등으로 전송

### Storage API
- Azure Storage Account, AWS S3를 사용하여 RAG 구현을 위한 임베딩 API입니다.
  - Cloud Storage와 연동된 파일 관리
  - 다양한 확장자(`md`, `txt`, `pdf`, `docx`, `xlsx`, `pptx` 등)의 임베딩 지원
  - Redis를 Vector Store로 활용하여 파일의 내용을 벡터화 후 저장

### Auth API
- GitHub OAuth 연동 인증 API입니다.
  - 사용자 가입 처리
  - 사용자 로그인 시 토큰 발급
  - 해당 토큰을 사용한 API 호출 인증 처리

## 설치 및 배포

### 사전 요구 사항
- Kubernetes 클러스터
- Helm 설치
- Istio 설치

### 설치 방법

1. **환경 변수 설정**: Intelligence API는 올바르게 동작하기 위해 필요한 환경 변수를 설정해야 합니다. 이 환경 변수들은 `values.yaml` 파일을 통해 설정할 수 있습니다. 아래는 예시입니다.

    ```yaml
    # Global settings section:
    # This section defines settings that are common across the entire application.
    global:
      namespace: ns-intelligenceapi  # Namespace where resources will be deployed.
      image:
        pullPolicy: IfNotPresent  # Image pull policy.
      service:
        type: ClusterIP  # Default service type.
        port: 80  # Default service port.
      llm:  # Language Model (LLM) service settings.
        provider: "Your LLM provider"  # LLM provider (e.g., OpenAI, Azure).
        apiKey: "Your LLM api key"  # API key for LLM provider.
        model: "Your LLM model"  # Specific LLM model to use.
        temperature: "0.5"  # Temperature setting for LLM.
        azureEndpoint: "Your Azure endpoint"  # Azure-specific LLM endpoint.
        azureApiVersion: "Your Azure API version"  # Azure API version.

      embedding:  # Embedding service settings.
        provider: "Your embedding provider"  # Embedding service provider.
        apiKey: "Your embedding api key"  # API key for embedding service.
        model: "Your embedding model"  # Specific embedding model to use.

      redis:  # Redis settings.
        url: "Your Redis URL"  # Redis connection URL.
        indexName: "Your Redis index name"  # Redis index name.
    ```

   `values.yaml` 파일에 환경 변수를 설정한 후, 다음 단계로 넘어갑니다.

2. Helm 차트를 이용하여 Intelligence API를 설치합니다.
    ```bash
    helm install intelligence-api ./helm/intelligence-api
    ```

3. Istio Gateway 및 Virtual Service를 설정하여

 외부 접근을 구성합니다.

4. 각 서비스의 엔드포인트를 설정하고 필요한 인증 정보(GitHub OAuth 등)를 구성합니다.

### 설정 파일
- `values.yaml` 파일을 통해 각 API의 설정 값을 변경할 수 있습니다.

## 사용법

### API 문서 확인
OpenAPI 문서는 `/docs` 또는 `/redoc` 엔드포인트를 통해 확인할 수 있습니다.

## 기여

Intelligence API에 기여하고자 하는 경우, 이 저장소를 포크하여 Pull Request를 보내주세요.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](./LICENSE) 파일을 참고하세요.

---

## English Version

Intelligence API is an integrated AI API utilizing Large Language Models (LLM) with LangChain and LangServe. The API is designed for easy deployment in Kubernetes environments, offering Helm charts for streamlined setup and Istio for effective network management. It provides routing to various backend services through Gateway API, enabling integration with diverse environments.

![Architecture](/Resources/architecture.png)

## Key Features

### Gateway API
- An API that routes to actual services based on LangChain.
- Integrated with Istio Gateway and Virtual Service for direct external connections.
- Provides routing to services like `Analysis`, `Query`, and `Webhook`.
- Access detailed documentation of backend services through OpenAPI documentation pages (`Docs`, `Redoc` endpoints).

### Analysis API
- An API that generates analysis results based on input values.
  - `/csp`: Analyze cloud environment alert messages.
  - `/devops`: Analyze DevOps platform alert messages.
  - `/code`: Analyze GitHub remote repository code (based on ReAct Agent).

### Query API
- An API that generates responses to input questions.
  - `/llm`: Generate responses using a simple LLM model.
  - `/translate`: Generate translations using an LLM model.
  - `/docs`: Use embedded content from documents via the RAG (Storage API).

### Webhook API
- An API that processes webhook POST requests.
  - Handle Alert Notification Webhooks from Azure, AWS, GCP, etc.
  - Handle Alert Notification Webhooks from Azure DevOps, etc.
  - Receive POST body values, pass content to the Analysis API, and send results to Slack or other platforms.

### Storage API
- An embedding API implemented using Azure Storage Account or AWS S3.
  - Manage files connected to Cloud Storage.
  - Support embedding of various file types (`md`, `txt`, `pdf`, `docx`, `xlsx`, `pptx`, etc.).
  - Use Redis as a Vector Store to vectorize and store the content of files.

### Auth API
- An authentication API integrated with GitHub OAuth.
  - Handle user registration.
  - Issue tokens upon user login.
  - Authenticate API calls using the issued token.

## Installation and Deployment

### Prerequisites
- Kubernetes cluster
- Helm installed
- Istio installed

### Installation Steps

1. **Set Environment Variables**: Configure the required environment variables for Intelligence API to function correctly. These variables can be set via the `values.yaml` file. Below is an example:

    ```yaml
    # Global settings section:
    global:
      namespace: ns-intelligenceapi  # Namespace where resources will be deployed.
      image:
        pullPolicy: IfNotPresent  # Image pull policy.
      service:
        type: ClusterIP  # Default service type.
        port: 80  # Default service port.
      llm:  # Language Model (LLM) service settings.
        provider: "Your LLM provider"  # LLM provider (e.g., OpenAI, Azure).
        apiKey: "Your LLM api key"  # API key for LLM provider.
        model: "Your LLM model"  # Specific LLM model to use.
        temperature: "0.5"  # Temperature setting for LLM.
        azureEndpoint: "Your Azure endpoint"  # Azure-specific LLM endpoint.
        azureApiVersion: "Your Azure API version"  # Azure API version.

      embedding:  # Embedding service settings.
        provider: "Your embedding provider"  # Embedding service provider.
        apiKey: "Your embedding api key"  # API key for embedding service.
        model: "Your embedding model"  # Specific embedding model to use.

      redis:  # Redis settings.
        url: "Your Redis URL"  # Redis connection URL.
        indexName: "Your Redis index name"  # Redis index name.
    ```

   After setting the environment variables in the `values.yaml` file, proceed to the next step.

2. Install the Intelligence API using Helm charts:
    ```bash
    helm install intelligence-api ./helm/intelligence-api
    ```

3. Configure Istio Gateway and Virtual Service to set up external access.

4. Set up each service's endpoints and configure the necessary authentication information (e.g., GitHub OAuth).

### Configuration Files
- You can modify the configuration values for each API via the `values.yaml` file.

## Usage

### API Documentation
You can access the OpenAPI documentation through the `/docs` or `/redoc` endpoints.

## Contributing

If you'd like to contribute to Intelligence API, please fork this repository and submit a Pull Request.

## License

This project is licensed under the MIT License. For more details, see the [LICENSE](./LICENSE) file.