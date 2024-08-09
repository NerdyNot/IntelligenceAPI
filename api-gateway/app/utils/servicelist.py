def servicelist():
    """
    게이트웨이에서 연결 할 백엔드 서비스 경로 설정.
    """
    return {
        "query": "http://intelligenceapi-query",
        "analysis": "http://intelligenceapi-analysis",
        "auth": "http://intelligenceapi-auth",
        "webhook": "http://intelligenceapi-webhook",
        "storage": "http://intelligenceapi-storage"
    }