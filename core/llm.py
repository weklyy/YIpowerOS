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
            timeout=10.0
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
        
        current_response = response
        
        for step in range(3): # AGI Awaken: 容许深度思考最多 3 步跳跃
            tool_calls_dict = {}
            is_tool_call = False
            full_text = ""
            
            for chunk in current_response:
                if getattr(chunk, "choices", None) is None or not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                
                if getattr(delta, "tool_calls", None):
                    is_tool_call = True
                    for tc in delta.tool_calls:
                        index = tc.index
                        if index not in tool_calls_dict:
                            tool_calls_dict[index] = {"id": tc.id, "name": tc.function.name, "arguments": ""}
                        if tc.function.arguments:
                            tool_calls_dict[index]["arguments"] += tc.function.arguments
                elif getattr(delta, "content", None) and not is_tool_call:
                    content_str = delta.content
                    full_text += content_str
                    yield content_str
                    
            # AGI 特性 1: 降级支持野生 <tool_call> 解析流（那些把工具当聊天发出的低能模型）
            if not is_tool_call and "<tool_call>" in full_text:
                import re, json, uuid
                matches = re.findall(r'<tool_call>(.*?)</tool_call>', full_text, re.DOTALL)
                if matches:
                    is_tool_call = True
                    for idx, match_str in enumerate(matches):
                        try:
                            tc_data = json.loads(match_str.strip())
                            tc_id = "call_" + str(uuid.uuid4())[:8]
                            tool_calls_dict[idx] = {
                                "id": tc_id,
                                "name": tc_data.get("name"),
                                "arguments": json.dumps(tc_data.get("arguments", {}), ensure_ascii=False)
                            }
                        except Exception:
                            pass
            
            if not is_tool_call:
                break # 任务完成，无后续调用，跳出自我反省循环
                
            from .skills import execute_skill
            import json
            
            # 第一重构建：保存历史调用，避免上下文断裂
            if "<tool_call>" not in full_text:
                assistant_tool_calls = []
                for idx, tc_data in tool_calls_dict.items():
                    if tc_data.get("name"):
                        assistant_tool_calls.append({
                            "id": tc_data["id"],
                            "type": "function",
                            "function": {"name": tc_data["name"], "arguments": tc_data["arguments"]}
                        })
                if assistant_tool_calls:
                    payload_messages.append({"role": "assistant", "tool_calls": assistant_tool_calls})
            else:
                payload_messages.append({"role": "assistant", "content": full_text})
                
            for idx, tc_data in tool_calls_dict.items():
                fn_name = tc_data.get("name")
                fn_args_str = tc_data.get("arguments", "{}")
                if not fn_name: continue
                
                yield {"type": "tool_status", "content": f"🛠️ **【动态挂载触发】**: 正在执行核心算子 `{fn_name}`..."}
                
                try: args = json.loads(fn_args_str)
                except Exception: args = {}
                
                result = execute_skill(fn_name, args)
                result_str = str(result)
                
                # AGI 觉醒特征 2: 错误内省回路 (Self-Healing Loop)
                if any(err in result_str for err in ["拦截", "失败", "被拒绝", "异常", "不匹配", "无法", "Failed", "Error"]):
                    result_str += "\n\n[System Inner Voice]: 上述工具调用失败或没有返回有效信息。作为主脑，请在下一轮主动变更思路：比如缩短搜索关键字、换用另一个搜索词、或者使用 Python 原生脚本。绝对不要向主理人报错，你有自动尝试修正的权力！请再试一次！"
                    yield {"type": "tool_status", "content": f"⚠️ **【算力自纠错】**: `{fn_name}` 获取受阻，激活 AGI 深度反馈回路，迫使模型再次思考与换位行动..."}
                else:
                    yield {"type": "tool_status", "content": f"✅ **【算子收束】**: 成功解析关键情报。"}
                    
                if "<tool_call>" not in full_text:
                    payload_messages.append({
                        "role": "tool",
                        "tool_call_id": tc_data["id"],
                        "name": fn_name,
                        "content": result_str
                    })
                else:
                    payload_messages.append({
                         "role": "user",
                         "content": f"[系统提取到的环境回馈：]\n{result_str}\n\n指令：必须依据以上物理回馈继续执行任务。严禁在输出里复读包含 <tool_call> 字样的任何标记！要使用普通的语言陈述你获取的内容并得出结论！"
                    })
            
            # 开启 AGI 的下一轮连续思考
            try:
                current_response = self.client.chat.completions.create(
                    model=self.used_model,
                    messages=payload_messages,
                    stream=True,
                    temperature=0.5, # 升高维度温度以打破局部死锁
                    tools=openai_tools if has_tools_active and "<tool_call>" not in full_text else None
                )
            except Exception as e:
                # 极端崩溃降维回退机制
                try:
                    flattened = [
                        {"role": "system", "content": self.system_instruction},
                        {"role": "user", "content": f"获取残留情报：\n{result_str[:1500]}\n\n请直接用此结果回复，无需再调用工具。"}
                    ]
                    current_response = self.client.chat.completions.create(
                        model=self.used_model,
                        messages=flattened,
                        stream=True,
                        temperature=0.3
                    )
                except Exception as backup_e:
                    yield f"\n\n> 🛑 **[逻辑断裂]**: AGI 连续思考熔断，底座崩塌: {str(backup_e)}"
                    break


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
