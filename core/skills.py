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
    }
]

# 路由函数执行
def execute_skill(function_name: str, arguments: dict):
    if function_name == "web_search":
        return web_search(arguments.get("query", ""))
    return f"未知技能: {function_name}"
