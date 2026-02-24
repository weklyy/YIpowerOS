# app.py
import streamlit as st
import os
from dotenv import load_dotenv

from core.llm import get_llm_node
from core.automation import init_automation, get_jobs
from core.memory import save_memory, load_recent_memory, clear_memory

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
        display_custom_opts = [f"[自定义] {m}" for m in custom_opts]
        
        # 插入明显的分隔符来做视觉上的组间隔离
        or_model_options = (
            ["--- 🌟 预设主力算子 ---"] + 
            base_options + 
            (["--- 🛠️ 您的自定义算子 ---"] + display_custom_opts if display_custom_opts else []) + 
            ["--- ➕ 其他 ---", "自定义 (Manual)"]
        )
        
        or_model_choice = st.selectbox("选择或输入模型名", or_model_options)
        
        if or_model_choice.startswith("--- "):
            # 如果不小心选到了分隔符，默认退回到第一个预设模型
            st.warning("您选到了分隔标签，已自动回归默认算子。")
            selected_model = base_options[0]
        elif or_model_choice == "自定义 (Manual)":
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
        
    st.markdown("---")
    st.markdown("### 💾 记忆中枢")
    if st.button("🧨 格式化物理记忆库"):
        clear_memory()
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 终端控制台 (Admin Dashboard)
# ==========================================
st.title("YI-CORE // 破军阵：联邦总控神坛")
st.caption("外佛内道，理正局清。大模型不再需要人工抽卡，由系统自己考试选拔。")

# 引入测跑组件
from core.benchmark import benchmark_engine

# 配置文件寻址
import json
CONFIG_FILE = "core/swarm_config.json"
def load_swarm_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"CEO": "", "Coder": "", "Social": ""}

def save_swarm_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

tab1, tab2 = st.tabs(["⚔️ Model Arena (算力角斗场)", "🧬 Swarm Dispatcher (群组部属)"])

with tab1:
    st.subheader("高抗压自动测跑台")
    st.markdown("填入你想测试的由英文逗号分隔的 OpenRouter `Model ID`（带上 :free 标志），引擎将同步启动并发推演验证其聪明度与挂载原生算子的成功率。")
    models_input = st.text_area(
        "候补兵营序列", 
        "arcee-ai/trinity-large-preview:free, stepfun/step-3.5-flash:free, google/gemini-2.5-pro:free, qwen/qwen-2.5-coder-32b-instruct:free",
        height=100
    )
    
    if st.button("🩸 注入题目，开始大逃杀测试 (可能耗时数分钟)"):
        with st.spinner("系统正在疯狂生成并行容器并下放《毁灭性测跑考卷》..."):
            models = [m.strip() for m in models_input.split(",") if m.strip()]
            results = benchmark_engine.batch_run(models)
            
            st.success("✅ 试炼结束，死生存亡结果已出！")
            
            # 展示榜单
            for idx, res in enumerate(results):
                with st.expander(f"🏅 Rank {idx+1}: {res['model_name']} | 评级: {res['rating']} | 得分: {res['overall_score']}"):
                    st.write(f"**综合成功率**: {res['success_rate']}")
                    st.json(res["details"])
                    
            # 自动生成分配建议
            st.session_state["benchmark_recommendations"] = benchmark_engine.generate_swarm_dispatch_recommendation(results)
            st.info("💡 测跑数据已生成底层神经元刻画。请前往【Swarm Dispatcher】查阅联邦系统的最终封神榜。")

with tab2:
    st.subheader("职能联邦分配书")
    st.markdown("系统将根据各算力的专项特长，将其分拨给不同群聊任务角色。您也可在此进行强制夺权调换。")
    
    current_cfg = load_swarm_config()
    rec_cfg = st.session_state.get("benchmark_recommendations", current_cfg)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🧠 破军枢纽 (CEO)")
        st.caption("负责解析意图并分发给底层算子。需要逻辑极强。")
        ceo_val = st.text_input("挂载终端号", value=rec_cfg.get("CEO", current_cfg.get("CEO")), key="ceo_input")
        
    with col2:
        st.markdown("### 💻 硅基黑客 (Coder)")
        st.caption("负责执行 Python 与 Shell 工具挂载。需要不易报错。")
        coder_val = st.text_input("挂载终端号", value=rec_cfg.get("Coder", current_cfg.get("Coder")), key="coder_input")
        
    with col3:
        st.markdown("### 📣 情报宣发 (Social)")
        st.caption("负责应对简单问答。需要速度极快、不限流。")
        social_val = st.text_input("挂载终端号", value=rec_cfg.get("Social", current_cfg.get("Social")), key="social_input")
        
    if st.button("🔥 将上述联邦编制熔铸进内核"):
        new_cfg = {
            "CEO": ceo_val,
            "Coder": coder_val,
            "Social": social_val
        }
        save_swarm_config(new_cfg)
        st.success("✅ 配置已烧录进物理底层。所有关联 Telegram 群组现在会以新脑区工作。")
