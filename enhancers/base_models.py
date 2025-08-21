from abc import ABC, abstractmethod
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential
from parsers.base_models import DataItem
MAX_RETRIES = 3
WAIT_TIME = 4
WAIT_MAX_TIME = 15
MULTIPLIER = 1

class JsonResponseFormat(BaseModel):
    """JSON 响应格式"""
    description:str

class InformationEnhancer(ABC):
    """信息增强器基类"""
    def __init__(self, model_name: str, base_url: str, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.system_prompt = "You are a helpful assistant."

    @abstractmethod
    async def enhance(self, information: DataItem) -> DataItem:
        """增强信息"""
        pass

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=MULTIPLIER, min=WAIT_TIME, max=WAIT_MAX_TIME))
    async def get_structured_response(self, user_prompt: list[dict[str, Any]], response_format: JsonResponseFormat) -> str|None:
        """获取结构化响应"""
        response = await self.client.chat.completions.parse(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt} # type: ignore
            ],
            response_format=response_format # type: ignore
        )
        if response.choices[0].message.refusal:
            raise ValueError(f"模型拒绝了请求: {response.choices[0].message.refusal}")
        return response.choices[0].message.parsed
