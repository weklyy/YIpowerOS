# app.py
import streamlit as st
import os
from dotenv import load_dotenv

from core.llm import get_llm_node
from core.automation import init_automation, get_jobs

# 预加载本地环境变量
# 预加载本地环境变量
load_dotenv()

import json

CUSTOM_MODELS_FILE = "custom_models.json"

def get_custom_models():
    if os.path.exists(CUSTOM_MODELS_FILE):
        with open(CUSTOM_MODELS_FILE, "r") as f:
            return json.load(f)
    return []

def save_custom_model(m):
    models = get_custom_models()
    if m not in models:
        models.append(m)
        with open(CUSTOM_MODELS_FILE, "w") as f:
            json.dump(models, f)

def remove_custom_model(m):
    models = get_custom_models()
    if m in models:
        models.remove(m)
        with open(CUSTOM_MODELS_FILE, "w") as f:
            json.dump(models, f)

# ==========================================
# 页面配置：Light Mode & Minimalist
# ==========================================
st.set_page_config(
    page_title="YI-CORE // 破军阵",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 强制注入自定义浅色/极简 CSS
st.markdown("""
    <style>
    /* 隐藏 Streamlit 自带的右上角菜单和底部 Footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* 全局浅色极简调优 */
    .stApp {
        background-color: #F8F9FA;
        color: #202124;
        font-family: "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .css-1d391kg {
        background-color: #FFFFFF;
        border-right: 1px solid #EAEAEA;
    }
    /* 标题冷峻化 */
    h1, h2, h3 {
        color: #3C4043 !important;
        font-weight: 500 !important;
        letter-spacing: 0.1em;
    }
    </style>
""", unsafe_allow_html=True)

# 初始化异步挂载引擎
init_automation()

# ==========================================
# 安全门禁 (Security Sandbox)
# ==========================================
def check_password():
    """返回验证状态。如果需要验证，则渲染输入框阻止流执行。"""
    
    # 尝试从环境变量获取预设密码 (如果没有配置则默认为 yipower_2026)
    sys_password = os.getenv("YICORE_PASSWORD", "yipower_2026")
    
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("<h2 style='text-align: center; margin-top: 20%;'>🔒 [AUTH_REQUIRED] YI-CORE</h2>", unsafe_allow_html=True)
        pwd = st.text_input("终端接管秘钥：", type="password")
        if pwd:
            if pwd == sys_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ 识别失败，禁止登入。")
        return False
    return True

if not check_password():
    st.stop()  # 密码不正确，停止喧染后面的代码

# ==========================================
# 侧边栏：算力切换与状态控制面板
# ==========================================
with st.sidebar:
    st.markdown("### 🔌 物理算力切片")
    engine_choice = st.radio(
        "路由网关 (Gateway)",
        ["Google", "OpenRouter"],
        index=0,
        help="Google: 搭载 Gemini-2.5-Pro 重型算力\\nOpenRouter: 搭载高性价比轻型开源算力"
    )
    
    selected_model = None
    if engine_choice == "OpenRouter":
        st.markdown("#### 🧠 模型指定")
        base_options = [
            "arcee-ai/trinity-large-preview:free",
            "deepseek/deepseek-chat",
            "deepseek/deepseek-reasoner",
            "anthropic/claude-3-haiku",
            "meta-llama/llama-3.3-70b-instruct",
            "google/gemini-2.5-flash",
        ]
        
        custom_opts = get_custom_models()
        # 对自定义模型加前缀以便视觉区分
        display_custom_opts = [f"[自定义] {m}" for m in custom_opts]
        
        or_model_options = base_options + display_custom_opts + ["自定义 (Manual)"]
        
        or_model_choice = st.selectbox("选择或输入模型名", or_model_options)
        
        if or_model_choice == "自定义 (Manual)":
            selected_model = st.text_input("填入 OpenRouter Model ID:", "openai/gpt-4o-mini")
            if st.button("➕ 保存该模型"):
                if selected_model:
                    save_custom_model(selected_model)
                    st.rerun()
        else:
            if or_model_choice.startswith("[自定义] "):
                selected_model = or_model_choice.replace("[自定义] ", "")
                if st.button("🗑️ 移除此自定义模型"):
                    remove_custom_model(selected_model)
                    st.rerun()
            else:
                selected_model = or_model_choice

    st.markdown("---")
    st.markdown("### ⚙️ 后台守护进程")
    jobs = get_jobs()
    if jobs:
        for job in jobs:
            st.caption(f"[{job['id']}] {job['name']}")
            st.caption(f"下一次唤醒: {job['next_run_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.caption("暂无挂载异步任务。")

# ==========================================
# 主面板：系统状态与对话流
# ==========================================
st.title("YI-CORE // 破军阵")
st.caption("外佛内道，理正局清。")

# 初始 Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
    # 系统打招呼
    st.session_state.messages.append({
        "role": "assistant",
        "content": "> [SYSTEM]: 主理人协议已确认。我是易次方首席算法架构师，已挂载2026丙午年数据库。"
    })

# 渲染历史对话记录流
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 输入指令舱
if prompt := st.chat_input("输入推演指令 / 执行任务..."):
    # 显示用户指令
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 调用相应的路由节点
    with st.chat_message("assistant"):
        try:
            # 获取算子节点
            node = get_llm_node(engine_choice, selected_model)
            
            # 【溯源反馈】：前置显示当前调用的真实底层模型
            st.caption(f"⚡ `[物理链路接管]：{node.model_name}`")
            
            message_placeholder = st.empty()
            full_response = ""
            
            # TODO: 将历史消息格式化以适应不同节点的参数，此处仅传最新一条和较短的记录做演示
            request_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] == "user"]
            if not request_messages:
                 request_messages = [{"role": "user", "content": prompt}]
            
            # 流式获取输出
            for chunk in node.chat(messages=request_messages, tools=True):
                if isinstance(chunk, dict) and chunk.get("type") == "tool_status":
                    with st.status(chunk["content"], expanded=True):
                        st.markdown("⏳ 算子执行完毕，等待主脑汇编情报...")
                elif isinstance(chunk, str):
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
        
        except Exception as e:
            err_msg = f"❌ [内核错误]: 算力节点调用失败。详情: {str(e)}"
            st.error(err_msg)
            full_response = err_msg

    # 追加至对话记录
    st.session_state.messages.append({"role": "assistant", "content": full_response})
