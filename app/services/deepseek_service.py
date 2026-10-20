import aiohttp
from app.core.config import settings

class DeepseekService:
    def __init__(self):
        self.base_url = settings.DEEPSEEK_BASE_URL.rstrip("/")
        self.model = settings.DEEPSEEK_MODEL
        self.api_key = settings.DEEPSEEK_API_KEY

        if not self.api_key:
            raise ValueError("使用 DeepSeek 时必须配置 DEEPSEEK_API_KEY")

    async def generate(self,messages:list[dict[str,str]])->str:
        timeout = aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                },
            ) as response:
                response.raise_for_status()
                result=await response.json()
                return result["choices"][0]["message"]["content"]

