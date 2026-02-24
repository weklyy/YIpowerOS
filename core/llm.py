# core/llm.py
import os
from openai import OpenAI
from google import genai
from google.genai import types
from dotenv import load_dotenv

from .protocol import get_system_prompt

load_dotenv()

# ==========================================
# 算子基类
# ==========================================
class BaseNode:
    def __init__(self):
        self.system_instruction = get_system_prompt()

    def chat(self, messages: list[dict], tools: list = None) -> iter:
        """流式输出，必须由子类实现"""
        raise NotImplementedError

# ==========================================
# 重型通道：Google Node (Gemini)
# ==========================================
class GoogleNode(BaseNode):
    def __init__(self, model_name="gemini-2.5-pro"):
        super().__init__()
        self.model_name = model_name
        # 使用 google-genai 最新版 SDK
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    def _convert_messages(self, messages: list[dict]) -> list:
        # 简单转换格式至 SDK 接受的形式
        formatted = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            formatted.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))])
            )
        return formatted

    def chat(self, messages: list[dict], tools: list = None) -> iter:
        # Gemini 路由暂简化：直接合并指令作为上下文，因 SDK system_instruction 定义方式可能差异
        contents = self._convert_messages(messages)
        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            temperature=0.3, # 冷峻理性
        )
        
        # TODO: 后续可接入 tools
        response_stream = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=config,
        )
        
        for chunk in response_stream:
            yield chunk.text

# ==========================================
# 轻型通道：OpenRouter Node (兼容 OpenAI)
# ==========================================
class OpenRouterNode(BaseNode):
    def __init__(self, model_name="deepseek/deepseek-chat"):
        super().__init__()
        self.model_name = model_name
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    def chat(self, messages: list[dict], tools: list = None) -> iter:
        # 强制在顶部注入夺舍协议
        payload_messages = [{"role": "system", "content": self.system_instruction}] + messages
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=payload_messages,
            stream=True,
            temperature=0.3,
            # tools=tools # 需要时挂载
        )
        
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# ==========================================
# The Chimera Router (重型轻型调度网关)
# ==========================================
def get_llm_node(router_name: str):
    """
    根据前端指令提供具体的底层物理节点
    """
    if router_name == "Google":
        return GoogleNode("gemini-2.5-pro")
    else:
        return OpenRouterNode("deepseek/deepseek-chat")
