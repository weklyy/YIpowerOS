# core/swarm.py
from core.llm import get_llm_node

class Agent:
    def __init__(self, name: str, role: str, instruction: str):
        self.name = name
        self.role = role
        self.instruction = instruction

class SwarmSystem:
    def __init__(self):
        # 预先登记的部门雇员（Agent 集合）
        self.agents = {
            "CEO": Agent("破军枢纽 (CEO)", "mastermind", "你处于系统的最高管控层..."),
            "Researcher": Agent("情报猎手", "searcher", "你专注于网络爬虫和资料检索，请优先调用 web_search 甚至 python 脚本去网罗情报。"),
            "Coder": Agent("硅基黑客", "developer", "你被赋予操作主机的完全权限，遇到需求可以大方调用 run_shell_command 和 python_interpreter 执行。"),
        }
        
    def get_agent_identity_prompt(self, agent_name: str) -> str:
        agent = self.agents.get(agent_name, self.agents["CEO"])
        return f"【职能覆盖注入】: 你现在是群组/任务中的 {agent.name} 身份。你的职责法则：{agent.instruction}\\n如果当前群组被划分为某固定阵地，请绝对服从阵地指令。"

    def process_chat(self, chat_id: str, message: str, group_role_context: str = ""):
        """
        接入社交渠道的一次提问。
        """
        from core.memory import load_recent_memory, save_memory
        
        # 提取过往该群组聊天上下文
        history = load_recent_memory(limit=10, session_id=chat_id)
        
        # 组装请求：包含全局背景与群组独有职能
        sys_prompt = self.get_agent_identity_prompt("CEO")
        if group_role_context:
            sys_prompt += f"\\n\\n【本阵地强制规则】: {group_role_context}"
            
        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        messages.append({"role": "user", "content": message})
        
        # 默认保存主理人的提问
        save_memory("user", message, session_id=chat_id)
        
        import os, json
        # 取出测跑分配书的配置
        config_file = os.path.join(os.path.dirname(__file__), "swarm_config.json")
        ceo_model = ""
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    cfg = json.load(f)
                    ceo_model = cfg.get("CEO", "").strip()
            except Exception:
                pass
                
        # 提取环境变量高可用算力预备池
        fallback_models = os.getenv(
            "OPENROUTER_DEFAULT_MODELS", 
            "arcee-ai/trinity-large-preview:free,stepfun/step-3.5-flash:free,google/gemini-2.5-pro:free"
        )
        
        if ceo_model:
             # 将 Dashboard 分配的最优模型挂载至列阵锋刃，若其失败则自动滑落至默认池
             fallback_models = f"{ceo_model},{fallback_models}"
        
        # 调用核心推演引擎
        node = get_llm_node("OpenRouter", fallback_models)
        node.system_instruction = sys_prompt
        
        full_response = ""
        # 拦截所有流并合成为一段（为了发报给 Telegram）
        for chunk in node.chat(messages=messages, tools=True):
            if isinstance(chunk, dict) and chunk.get("type") == "tool_status":
                # 群聊里可以暂时选择不播报繁杂的挂载过程，只播报最终结果
                pass
            elif isinstance(chunk, str):
                full_response += chunk
                
        # 保存机器人的回答
        save_memory("assistant", full_response, session_id=chat_id)
        
        return full_response

swarm_engine = SwarmSystem()
