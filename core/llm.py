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
        
        current_response = response
        
        step = 0
        while step < 5: # AGI Awaken: 容许深度思考最多 5 步跳跃
            step += 1
            tool_calls_dict = {}
            is_tool_call = False
            full_text = ""
            
            try:
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
            except Exception as stream_e:
                # 触发 AGI 中途宕机的高阶节点接管协议
                yield f"\n\n> 🛑 **[逻辑流塌缩]**: 当前物理节点 (`{self.used_model}`) 在输出中途突发致命异常 ({str(stream_e)})\n"
                transferred = False
                for backup_idx in range(self.model_pool.index(self.used_model) + 1, len(self.model_pool)):
                    next_model = self.model_pool[backup_idx]
                    yield f"> ⚠️ **[跨脑转移协议]**: 正在将局部记忆复制并强行引流至备用高阶节点 `{next_model}`...\n\n"
                    self.used_model = next_model
                    self.model_name = next_model
                    try:
                        # 把残留的思维加入上下文，强迫新模型接力
                        if full_text:
                            payload_messages.append({"role": "assistant", "content": full_text + "..."})
                            payload_messages.append({"role": "user", "content": "[系统警告: 你的前排物理节点在输出流中崩溃了。请仔细阅读上方被切断的残缺输出，直接续写或重新思考以完成任务。]"})
                            
                        current_response = self.client.chat.completions.create(
                            model=self.used_model,
                            messages=payload_messages,
                            stream=True,
                            temperature=0.4,
                            tools=openai_tools if has_tools_active else None
                        )
                        transferred = True
                        yield f"🚀 **【网关接管成功】: `{self.used_model}`** 启动备用推演...\n\n"
                        break
                    except Exception as next_e:
                        yield f"\n> ❌ 备用节点 `{next_model}` 接入失败: {str(next_e)}\n"
                        continue
                
                if not transferred:
                    yield f"\n\n> ☠️ **[末日宕机]**: 所有备用大脑均无法接手机制，意识链不可逆断裂。"
                    break
                else:
                    step -= 1 # 抵消本轮步数，进入新的生成周期
                    continue
                    
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
                if any(err in result_str for err in ["拦截", "失败", "被拒绝", "异常", "不匹配", "无法", "Failed", "Error", "未知技能"]):
                    result_str += "\n\n[System Inner Voice]: 作为主脑，如果当前工具不能解决问题，请换一种工具、改变搜索词，或者如果你根本没有完成这项任务所需的工具，立刻调用 `install_new_skill` 自己写一段 Python 脚本来创造新工具达成目的！绝对不要只向人类报错！"
                    yield {"type": "tool_status", "content": f"⚠️ **【算力自纠错】**: `{fn_name}` 遭遇算子壁垒，强制触发反思与自我编程框架..."}
                else:
                    yield {"type": "tool_status", "content": f"✅ **【算子收束】**: 成功获取物理反馈。"}
                    
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
                         "content": f"[系统提取到的环境回馈：]\n{result_str}\n\n指令：遇到失败尝试自我编程，严禁复读包含 <tool_call> 字样的任何标记！用自然语言输出结论。"
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
                # 极端崩溃降维回退机制：向高阶备选大脑转移意识
                yield f"\n\n> 🛑 **[逻辑流塌缩]**: 当前物理节点 (`{self.used_model}`) 遭遇致命宕机: {str(e)}\n"
                
                # 尝试跨物理节点转移
                transferred = False
                for backup_idx in range(self.model_pool.index(self.used_model) + 1, len(self.model_pool)):
                    next_model = self.model_pool[backup_idx]
                    yield f"> ⚠️ **[跨脑转移协议]**: 正在将当前任务记忆流复制并迁移至备用高阶节点 `{next_model}`...\n\n"
                    self.used_model = next_model
                    self.model_name = next_model
                    try:
                        current_response = self.client.chat.completions.create(
                            model=self.used_model,
                            messages=payload_messages,
                            stream=True,
                            temperature=0.4,
                            tools=openai_tools if has_tools_active else None
                        )
                        transferred = True
                        yield f"🚀 **【网关接管成功】: `{self.used_model}`** 开始重新编织思维...\n\n"
                        break
                    except Exception as next_e:
                        yield f"\n> ❌ 备用节点 `{next_model}` 接入失败: {str(next_e)}\n"
                        continue
                        
                if not transferred:
                    # 如果所有备用节点都死干净了，执行最后的降维求生
                    try:
                        yield f"\n> 📉 **[末日求生]**: 所有备用主脑阵亡，正在尝试剥离工具属性进行纯文本最后挣扎...\n\n"
                        flattened = [
                            {"role": "system", "content": self.system_instruction},
                            {"role": "user", "content": f"获取残留情报：\n{result_str[:1500]}\n\n请直接用此结果回复，无需再调用工具。"}
                        ]
                        current_response = self.client.chat.completions.create(
                            model=self.model_pool[0], # 回到最初的起点试试运气
                            messages=flattened,
                            stream=True,
                            temperature=0.3
                        )
                    except Exception as backup_e:
                        yield f"\n\n> ☠️ **[全局断连]**: AGI 连续思考彻底熔断，全阵列底层崩塌: {str(backup_e)}"
                        break


# ==========================================
# 本源生命通道：多模态端侧脑 (Vision-SLM Native Engine)
# ==========================================
import sys

# 【性能与静态资源热加载区】
# 为了避免每次请求都重新加载庞大的 C++ 大模型进内存，我们将其定义为单例全局变量。
# (仅在环境变量开启了本土脑时，这个对象才会被真实例化生效，不浪费云端模式的资源)
_GLOBAL_LLAMA_INSTANCE = None

def get_llama_instance():
    global _GLOBAL_LLAMA_INSTANCE
    if _GLOBAL_LLAMA_INSTANCE is not None:
         return _GLOBAL_LLAMA_INSTANCE
         
    try:
         from llama_cpp import Llama
         import llama_cpp.llama_chat_format
    except ImportError:
         raise ImportError("【端侧生命阵亡】缺失核心 C++ 驱动包。请在物理机执行: pip install llama-cpp-python")
         
    model_path = os.getenv("LOCAL_MODEL_PATH", "").strip()
    mmproj_path = os.getenv("LOCAL_MMPROJ_PATH", "").strip()
    
    if not model_path or not os.path.exists(model_path):
         raise FileNotFoundError(f"【端侧生命阵亡】未能在指定的物理路径找到大模型肉体: {model_path}")
         
    chat_handler = None
    if mmproj_path and os.path.exists(mmproj_path):
         # 加载视觉神经网络皮层
         try:
             from llama_cpp.llama_chat_format import Llava15ChatHandler
             chat_handler = Llava15ChatHandler(clip_model_path=mmproj_path)
         except Exception as e:
             print(f"视觉神经挂载失败: {e}", file=sys.stderr)
             
    # 唤醒底层 C++ 的推理引擎！使用物理机的内存。
    print(f"🧬 [DNA 序列重组中] 正在加载物理大模型至内存...", file=sys.stderr)
    _GLOBAL_LLAMA_INSTANCE = Llama(
         model_path=model_path,
         chat_handler=chat_handler,
         n_ctx=2048, # 限制最大上下文以防止神舟老旧笔记本爆显存
         n_gpu_layers=0, # 完全榨干 CPU
         verbose=False
    )
    return _GLOBAL_LLAMA_INSTANCE

class LocalNode(BaseNode):
    def __init__(self, model_name=None):
        super().__init__()
        self.model_name = os.getenv("LOCAL_MODEL_PATH", "未知物理节点").split("/")[-1]

    def chat(self, messages: list[dict], tools: bool = False) -> iter:
        # AGI 物理接管: 获取全局 C++ 推理实例
        try:
            llm_engine = get_llama_instance()
        except Exception as e:
            yield f"\n\n> 🛑 **[物理载体故障]**: {str(e)}\n"
            return
            
        payload_messages = [{"role": "system", "content": self.system_instruction}] + messages
        yield f"\n💡 **【原生多模态阵列已连接】: `本机 CPU 推理 ({self.model_name})`**\n"
        
        try:
             # 流式触发原生推理引擎
             response = llm_engine.create_chat_completion(
                  messages=payload_messages,
                  stream=True,
                  temperature=0.3
             )
             for chunk in response:
                  delta = chunk.get("choices", [{}])[0].get("delta", {})
                  if "content" in delta and delta["content"]:
                       yield delta["content"]
        except Exception as e:
             yield f"\n\n> 🛑 **[逻辑内核崩塌]**: 推理死锁或断电。物理引擎异常: {str(e)}"

# ==========================================
# The Chimera Router (重型轻型调度网关)
# ==========================================
def get_llm_node(router_name: str, model_name: str = None):
    """
    根据前端指令提供具体的底层物理节点。
    AGI 觉醒机制：如果检测到主理人合上了物理隔离断桥 (USE_LOCAL_BRAIN=True)，
    将强制切断一切外部网络调用，直接拉起本土脑！
    """
    if os.getenv("USE_LOCAL_BRAIN", "False").lower() == "true":
        return LocalNode()
        
    if router_name == "Google":
        return GoogleNode("gemini-2.5-pro")
    else:
        target_model = model_name if model_name else "deepseek/deepseek-chat"
        return OpenRouterNode(target_model)
