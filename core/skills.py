# core/skills.py
from duckduckgo_search import DDGS

def web_search(query: str, max_results: int = 3) -> str:
    """
    使用 DuckDuckGo 执行轻量级 Web 检索。
    返回合并后的摘要文本，供大模型参考。
    """
    print(f"[YI-CORE/Skill] 执行检索: {query}")
    try:
        results = DDGS().text(query, max_results=max_results)
        if not results:
            return "检索无结果。"
        
        summary = "\\n".join(
            [f"标题: {r['title']}\\n链接: {r['href']}\\n摘要: {r['body']}" for r in results]
        )
        return summary
    except Exception as e:
        return f"检索失败: {str(e)}"

import requests
import os

def openclaw_delegate(action: str, payload: dict) -> str:
    """
    将执行流代理给后端的 OpenClaw 服务集群。
    """
    endpoint = os.getenv("OPENCLAW_ENDPOINT", "http://127.0.0.1:8000")
    api_key = os.getenv("OPENCLAW_API_KEY", "")
    
    url = f"{endpoint}/api/v1/execute" # 假设的 OpenClaw 标准挂载点，主理人可依实际情况修改
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "action": action,
        "payload": payload
    }
    
    print(f"[YI-CORE/Skill] 代理唤醒 OpenClaw 集群: 执行动作 '{action}'")
    try:
        # 添加 10 秒超时防止线程卡死
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"[OpenClaw 链路异常]: {str(e)}"

# 供 OpenAI/Google 兼容格式使用的标准 Tool Schema
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "当主理人询问实时信息、新闻、或当前事实时，调用此工具进行联网检索。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要搜索的关键词短语，尽可能精简有效。"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "openclaw_delegate",
            "description": "当主理人要求执行复杂任务、系统控制、或其他 OpenClaw 所涵盖的技能时，调用此代理工具接入远程集群。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "需要 OpenClaw 执行的具体技能指令名 (例如 'send_telegram', 'read_file' 等)。"
                    },
                    "payload": {
                        "type": "object",
                        "description": "执行该动作所需的具体参数键值对。"
                    }
                },
                "required": ["action", "payload"]
            }
        }
    }
]

# 路由函数执行
def execute_skill(function_name: str, arguments: dict):
    if function_name == "web_search":
        return web_search(arguments.get("query", ""))
    elif function_name == "openclaw_delegate":
        return openclaw_delegate(arguments.get("action", ""), arguments.get("payload", {}))
    return f"未知技能: {function_name}"
