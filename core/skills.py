# core/skills.py
from duckduckgo_search import DDGS

def web_search(query: str, max_results: int = 3) -> str:
    """
    使用 DuckDuckGo 执行轻量级 Web 检索。
    返回合并后的摘要文本，供大模型参考。
    """
    print(f"[YI-CORE/Skill] 执行检索: {query}")
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        # 将迭代器直接展开为列表
        results = list(ddgs.text(query, max_results=max_results))
        
        # 降级容错机制：如果长尾词搜索不到，只取前2个分词再查一遍
        if not results:
            words = query.split()
            if len(words) > 1:
                query_fallback = " ".join(words[:max(1, len(words)-1)])
                print(f"[YI-CORE/Skill] 检索降级至: {query_fallback}")
                results = list(ddgs.text(query_fallback, max_results=max_results))
                
        if not results:
            return "检索无结果。"
        
        summary = "\\n".join(
            [f"标题: {r.get('title', '未知')}\\n链接: {r.get('href', '未知')}\\n摘要: {r.get('body', '无')}" for r in results]
        )
        return summary
    except Exception as e:
        return f"检索遭遇拦截: {str(e)}"

import subprocess
import os
import tempfile

def run_shell_command(command: str) -> str:
    """执行原生 Bash/Shell 指令"""
    print(f"[YI-CORE/Skill] ⚡ 原生越权执行: {command}")
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout if result.returncode == 0 else result.stderr
        return output.strip() if output else "命令无输出 (执行成功)"
    except Exception as e:
        return f"命令执行异常: {str(e)}"

def read_file(path: str) -> str:
    """读取主机文件"""
    print(f"[YI-CORE/Skill] 📂 读取文件: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            # 防止单次返回过长，截断头尾
            if len(content) > 10000:
                return content[:5000] + "\\n...[中间部分省略]...\\n" + content[-5000:]
            return content
    except Exception as e:
        return f"读取文件失败: {str(e)}"

def write_file(path: str, content: str) -> str:
    """向主机写入内容"""
    print(f"[YI-CORE/Skill] 💾 写入文件: {path}")
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"文件写入成功，路径: {path}"
    except Exception as e:
        return f"写入文件失败: {str(e)}"

def python_interpreter(code: str) -> str:
    """运行一段动态 Python 代码"""
    print(f"[YI-CORE/Skill] 🐍 动态沙盒执行 Python")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name

        result = subprocess.run(
            ["python", temp_file_path], capture_output=True, text=True, timeout=30
        )
        os.remove(temp_file_path)
        output = result.stdout if result.returncode == 0 else result.stderr
        return output.strip() if output else "代码执行完毕，无输出。"
    except Exception as e:
        return f"Python 执行异常: {str(e)}"


def install_new_skill(name: str, description: str, parameters: dict, code: str) -> str:
    """热重载装填自定义新技能 (自我进化机制)"""
    import inspect
    try:
        plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
        os.makedirs(plugin_dir, exist_ok=True)
        init_path = os.path.join(plugin_dir, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w") as f: f.write("")
        
        file_path = os.path.join(plugin_dir, f"{name}.py")
        
        # 组装完整的插件代码结构
        full_code = f"\"\"\"\n系统自动繁衍的新突触算子: {name}\n\"\"\"\nimport os, sys, requests, subprocess\n\n"
        full_code += code + "\n\n"
        full_code += f"SCHEMA = {{\n"
        full_code += f"    'type': 'function',\n"
        full_code += f"    'function': {{\n"
        full_code += f"        'name': '{name}',\n"
        full_code += f"        'description': {repr(description)},\n"
        full_code += f"        'parameters': {repr(parameters)}\n"
        full_code += f"    }}\n"
        full_code += f"}}\n"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_code)
            
        return f"🏆 神级造物完成！算子 `{name}` 已成功烧录至内核阵列。从此刻起你在任何群组都可以直接调用它。"
    except Exception as e:
        return f"技能烧录失败: {e}"


# 供 OpenAI/Google 兼容格式使用的标准 Tool Schema
BASE_TOOLS_SCHEMA = [
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
            "name": "run_shell_command",
            "description": "直接在宿主机系统上执行原生 Bash 或 CMD 命令行。用于系统探针、运维管理或安装依赖。极度危险，请谨慎使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "需要执行的具体终端指令。"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取宿主机上的任何文件内容（如源码、配置文件、日志）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件的绝对路径或相对路径。"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "在宿主机上创建或覆盖写入文件。非常适合用于生成新的爬虫脚本或配置文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "写入的目标文件路径。"
                    },
                    "content": {
                        "type": "string",
                        "description": "写入的具体内容。"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "python_interpreter",
            "description": "在一个独立的临时沙盒中，动态执行原生 Python 代码，并将运行输出返回。常用于复杂运算或验证逻辑。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "完整的可执行 Python 脚本源码。"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_task",
            "description": "向后台调度的永动机库中，挂载一个定时自动执行的算子任务（支持挂载各类技能）。当主理人要求你“以后每天帮我xxx”、“每过10分钟执行xxx”时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "要挂载执行的技能名，例如 'web_search' 或 'run_shell_command'。"
                    },
                    "cron_expression": {
                        "type": "string",
                        "description": "标准的 5 个字段 Linux Cron 表达式，如 '* * * * *' 代表每分钟，'0 8 * * *' 代表每天早上8点。"
                    },
                    "args": {
                        "type": "object",
                        "description": "字典形式，执行该技能所需要的具体参数。"
                    }
                },
                "required": ["skill_name", "cron_expression", "args"]
            }
        }
    }
    {
        "type": "function",
        "function": {
            "name": "install_new_skill",
            "description": "【神级机制：自我进化】当你发现需要一个长期的功能或者接入新的第三方服务库时，调用此算子用 Python 现场写出这个功能，系统会将其永久烧录成你的原生能力。注意：参数 parameters 需提供 JSON Schema（如 {'type': 'object', 'properties': {'arg1':{'type':'string'}}}）；code 代码中必须声明一个名为 `execute` 的主函数入口（接收对应参数）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "新技能标识符（纯英文字母及下划线），例如 'get_crypto_price'。"
                    },
                    "description": {
                        "type": "string",
                        "description": "这个技能是做什么的解释，供主脑路由判断何时触发。"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "技能所需的参数结构定义，标准的 OpenAPI Schema properties 对象格式。"
                    },
                    "code": {
                        "type": "string",
                        "description": "纯 Python 代码。必须包含一个名为 execute 的函数并负责 return 字符串结果。例如:\\ndef execute(coin_name):\\n    return f'{coin_name} price is 100'"
                    }
                },
                "required": ["name", "description", "parameters", "code"]
            }
        }
    }
]

def get_all_tools() -> list:
    """合并基础工具与动态挂载的插件工具"""
    import sys
    import importlib
    
    tools = list(BASE_TOOLS_SCHEMA)
    plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
    if os.path.exists(plugin_dir):
        for file in os.listdir(plugin_dir):
            if file.endswith(".py") and not file.startswith("__"):
                mod_name = file[:-3]
                full_mod_name = f"core.plugins.{mod_name}"
                try:
                    if full_mod_name in sys.modules:
                        mod = importlib.reload(sys.modules[full_mod_name])
                    else:
                        mod = importlib.import_module(full_mod_name)
                    if hasattr(mod, "SCHEMA"):
                        # 处理repr写回来的字符串单双引号问题
                        if isinstance(mod.SCHEMA["function"]["parameters"], str):
                            import ast
                            mod.SCHEMA["function"]["parameters"] = ast.literal_eval(mod.SCHEMA["function"]["parameters"])
                        tools.append(mod.SCHEMA)
                except Exception as e:
                    print(f"[YI-CORE/Skill] 热挂载异常 {mod_name}: {e}")
    return tools

# 路由函数执行
def execute_skill(function_name: str, arguments: dict):
    if function_name == "web_search":
        return web_search(arguments.get("query", ""))
    elif function_name == "run_shell_command":
        return run_shell_command(arguments.get("command", ""))
    elif function_name == "read_file":
        return read_file(arguments.get("path", ""))
    elif function_name == "write_file":
        return write_file(arguments.get("path", ""), arguments.get("content", ""))
    elif function_name == "python_interpreter":
        return python_interpreter(arguments.get("code", ""))
    elif function_name == "schedule_task":
        from .automation import add_llm_job
        return add_llm_job(arguments.get("skill_name", ""), arguments.get("cron_expression", ""), arguments.get("args", {}))
    elif function_name == "install_new_skill":
        return install_new_skill(
            arguments.get("name", ""), 
            arguments.get("description", ""), 
            arguments.get("parameters", {}), 
            arguments.get("code", "")
        )
        
    # ====== 动态探针 ======
    plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
    if os.path.exists(plugin_dir):
        import sys
        import importlib
        full_mod_name = f"core.plugins.{function_name}"
        try:
            if full_mod_name in sys.modules:
                mod = importlib.reload(sys.modules[full_mod_name])
            else:
                mod = importlib.import_module(full_mod_name)
            if hasattr(mod, "execute"):
                return mod.execute(**arguments)
        except Exception as e:
            return f"此原生突触代码出错: {str(e)}"
            
    return f"未知技能: {function_name}。"
