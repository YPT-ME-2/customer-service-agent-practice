from app.services.ollama_service import OllamaService

class LLMFactory:
    @staticmethod
    def create_chat_service():
        return OllamaService()
    