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
        # 支持逗号分隔的备用物理节点池
        self.model_pool = [m.strip() for m in model_name.split(",")] if "," in model_name else [model_name]
        self.used_model = self.model_pool[0]
        self.model_name = self.used_model  # 恢复对旧版 Web UI 的兼容
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            timeout=45.0
        )

    def chat(self, messages: list[dict], tools: bool = False) -> iter:
        # 强制在顶部注入夺舍协议
        payload_messages = [{"role": "system", "content": self.system_instruction}] + messages
        
        openai_tools = None
        if tools:
            from .skills import get_all_tools
            openai_tools = get_all_tools()
            
        response = None
        has_tools_active = tools

        for attempt_idx, model in enumerate(self.model_pool):
            self.used_model = model
            self.model_name = model # 同步更新对外暴露的型号
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=payload_messages,
                    stream=True,
                    temperature=0.3,
                    tools=openai_tools
                )
                break # 获取连接成功
            except Exception as e:
                # 若携带 Tool 失败，尝试对该节点降维打击（禁用 Tool）再试一次
                if has_tools_active:
                    try:
                        response_no_tool = self.client.chat.completions.create(
                            model=model,
                            messages=payload_messages,
                            stream=True,
                            temperature=0.3
                        )
                        response = response_no_tool
                        has_tools_active = False # 当前局禁用 tools
                        yield f"\n\n> 🔕 **[算力警告]**: 节点 `{model}` 不具备原生算子挂载能力，已降维至纯文本模式。\n\n"
                        break
                    except Exception as e2:
                        pass
                
                # 如果纯文本也崩溃（如 429 免费额度耗尽）
                if attempt_idx == len(self.model_pool) - 1:
                    yield f"\n\n> 🛑 **[算力枯竭]**: 整个配置的模型阵列已全部宕机或被风控，最后节点 `{model}` 报错: {str(e)}"
                    return
                else:
                    yield f"\n\n> ⚠️ **[节点切换]**: `{model}` 阵亡或被阻断，自动引流至下一备用节点 `{self.model_pool[attempt_idx+1]}`...\n\n"
                    continue
        
        # 加入强制主脑水印
        yield f"\n🚀 **【当前执飞节点】: `{self.used_model}`**\n\n"
        
        tool_calls_dict = {}
        is_tool_call = False
        
        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            
            if delta.tool_calls:
                is_tool_call = True
                for tc in delta.tool_calls:
                    index = tc.index
                    if index not in tool_calls_dict:
                        tool_calls_dict[index] = {"id": tc.id, "name": tc.function.name, "arguments": ""}
                    if tc.function.arguments:
                        tool_calls_dict[index]["arguments"] += tc.function.arguments
            elif delta.content and not is_tool_call:
                yield delta.content
                
        if is_tool_call:
            from .skills import execute_skill
            import json
            
            assistant_tool_calls = []
            for idx, tc_data in tool_calls_dict.items():
                assistant_tool_calls.append({
                    "id": tc_data["id"],
                    "type": "function",
                    "function": {"name": tc_data["name"], "arguments": tc_data["arguments"]}
                })
            
            payload_messages.append({"role": "assistant", "tool_calls": assistant_tool_calls})
            
            for idx, tc_data in tool_calls_dict.items():
                fn_name = tc_data["name"]
                fn_args_str = tc_data["arguments"]
                yield {"type": "tool_status", "content": f"🛠️ **【动态挂载触发】**: 正在执行核心算子 `{fn_name}`..."}
                
                try:
                    args = json.loads(fn_args_str)
                except Exception:
                    args = {}
                
                result = execute_skill(fn_name, args)
                
                payload_messages.append({
                    "role": "tool",
                    "tool_call_id": tc_data["id"],
                    "name": fn_name,
                    "content": str(result)
                })
                
            # 某些 OpenRouter 免费模型不支持复杂的多轮 Tool Payload，做降级处理
            try:
                has_yielded = False
                second_resp = self.client.chat.completions.create(
                    model=self.used_model,
                    messages=payload_messages,
                    stream=True,
                    temperature=0.3
                )
                for chunk in second_resp:
                    if chunk.choices and chunk.choices[0].delta.content:
                        has_yielded = True
                        yield chunk.choices[0].delta.content
                
                # 如果流式结束但根本没有输出任何字符（静默失败），则强行触发回退机制
                if not has_yielded:
                    raise Exception("Model silent empty yield.")
                    
            except Exception as e:
                # 若第二轮请求因 payload 问题被拒，强行降级为只带 system, user 和 tool 结果的纯净文本请求
                try:
                    raw_messages = [
                        {"role": "system", "content": self.system_instruction},
                        {"role": "user", "content": f"先前指令: {messages[-1]['content']}\n\n[系统自动挂载了算子并获取到了以下数据：]\n{str(result)}\n\n请根据上述数据，冷峻地回答主理人的指令。"}
                    ]
                    backup_resp = self.client.chat.completions.create(
                        model=self.used_model,
                        messages=raw_messages,
                        stream=True,
                        temperature=0.3
                    )
                    backup_has_yielded = False
                    for chunk in backup_resp:
                        if chunk.choices and chunk.choices[0].delta.content:
                            backup_has_yielded = True
                            yield chunk.choices[0].delta.content
                    
                    if not backup_has_yielded:
                        yield f"\n\n> ⚠️ **[系统强制接管]**: 该低阶算力节点 ({self.used_model}) 获取了情报但拒绝输出。原始物理探测情报截取如下：\n\n{str(result)[:2000]}..."
                except Exception as backup_e:
                    # 如果兜底也失败了（比如上下文依然超限，或者被限流 API报错）
                    yield f"\n\n> ⚠️ **[系统强制接管]**: 该低阶算力节点彻底崩溃 (报错: {str(backup_e)})。原始物理探测情报截取如下：\n\n{str(result)[:2000]}..."


# ==========================================
# The Chimera Router (重型轻型调度网关)
# ==========================================
def get_llm_node(router_name: str, model_name: str = None):
    """
    根据前端指令提供具体的底层物理节点
    """
    if router_name == "Google":
        return GoogleNode("gemini-2.5-pro")
    else:
        target_model = model_name if model_name else "deepseek/deepseek-chat"
        return OpenRouterNode(target_model)
