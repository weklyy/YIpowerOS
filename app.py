# app.py
import streamlit as st
import os
from dotenv import load_dotenv

from core.llm import get_llm_node
from core.automation import init_automation, get_jobs

# 预加载本地环境变量
load_dotenv()

# ==========================================
# 页面配置：Dark Mode & Minimalist
# ==========================================
st.set_page_config(
    page_title="YI-CORE // 破军阵",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 强制注入自定义暗色/极简 CSS
st.markdown("""
    <style>
    /* 隐藏 Streamlit 自带的右上角菜单和底部 Footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* 全局暗色极简调优 */
    .stApp {
        background-color: #0E1117;
        color: #C9D1D9;
        font-family: "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .css-1d391kg {
        background-color: #161B22;
    }
    /* 标题冷峻化 */
    h1, h2, h3 {
        color: #8B949E !important;
        font-weight: 500 !important;
        letter-spacing: 0.1em;
    }
    </style>
""", unsafe_allow_html=True)

# 初始化异步挂载引擎
init_automation()

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
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # 获取算子节点
            node = get_llm_node(engine_choice)
            
            # TODO: 将历史消息格式化以适应不同节点的参数，此处仅传最新一条和较短的记录做演示
            request_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] == "user"]
            if not request_messages:
                 request_messages = [{"role": "user", "content": prompt}]
            
            # 流式获取输出
            for chunk in node.chat(messages=request_messages):
                if chunk:
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
        
        except Exception as e:
            err_msg = f"❌ [内核错误]: 算力节点调用失败。详情: {str(e)}"
            st.error(err_msg)
            full_response = err_msg

    # 追加至对话记录
    st.session_state.messages.append({"role": "assistant", "content": full_response})
