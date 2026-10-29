import asyncio
import aiohttp
import json

from app.core.config import settings
from app.core.logger import get_logger

import  base64

logger=get_logger("ollama")


class OllamaService:
    def __init__(self):
        self.base_url=settings.OLLAMA_BASE_URL.rstrip("/")
        self.chat_model=settings.OLLAMA_CHAT_MODEL

    async def generate(
            self,
            messages:list[dict],
            options:dict|None=None,
            ) -> str:
        timeout = aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(
            timeout=timeout,
            trust_env=False,
        ) as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.chat_model,
                    "messages": messages,
                    "stream": False,
                    "think": False,
                    "options": options or {},
                },
            ) as response:
                response.raise_for_status()
                result = await response.json()

                return result["message"]["content"]

    async def generate_with_image(
        self,
        question: str,
        image: bytes,            
    )->str:
        image_data = base64.b64encode(image).decode("ascii")

        return await self.generate([
            {
                "role": "system",
                "content": (
                    "请根据图片中可见的内容回答问题。"
                    "看不清的文字、品牌和型号请明确说明，不能猜测。"
                    "不要仅凭外观断定内部故障。"
                ),
            },
             {
                "role": "user",
                "content": question,
                "images": [image_data],
            },
        ])
    

    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],)->dict:
        timeout=aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(
            timeout=timeout,
            trust_env=False,
        ) as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.chat_model,
                    "messages": messages,
                    "tools": tools,
                    "stream": False,
                    "think": False,
                },
            ) as response:
                response.raise_for_status()
                result=await response.json()

                return result["message"]

    async def generate_with_tools_stream(
        self,
        messages: list[dict],
        tools: list[dict],    
    ):
        timeout=aiohttp.ClientTimeout(total=300)

        async with aiohttp.ClientSession(
            timeout=timeout,
            trust_env=False,
        ) as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.chat_model,
                    "messages": messages,
                    "tools": tools,
                    "stream": True,
                    "think": False,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.content:
                    if not line.strip():
                        continue
                    chunk = json.loads(line)

                    if chunk.get("error"):
                        raise RuntimeError(chunk["error"])

                    message = chunk.get("message")
                    if message:
                        yield message

                    if chunk.get("done"):
                        break

    async def generate_stream(self,messages:list[dict[str,str]]):
        timeout =aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(
            timeout=timeout,
            trust_env=False,
        ) as session:
            logger.info("开始流式请求，模型：%s", self.chat_model)
            async with session.post(
                f"{self.base_url}/api/chat",
                json={
                "model": self.chat_model,
                "messages": messages,
                "stream": True,
                "think": False,
            },
            ) as resopnse:
                resopnse.raise_for_status()

                async for line in resopnse.content:
                    if not line.strip():
                        continue
                    chunk=json.loads(line)
                    if chunk.get("error"):
                        raise RuntimeError(chunk["error"])

                    content = chunk.get("message", {}).get("content", "")

                    if content:
                        yield content
                    if chunk.get("done"):
                        logger.info("Ollama 流式生成完成")
                        break

async def main():
    service = OllamaService()

    answer = await service.generate([
        {"role": "user", "content": "你好，请用一句话介绍自己。"}
    ])

    print(answer)


if __name__ == "__main__":
    asyncio.run(main())