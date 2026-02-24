import os
import sys
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 确保能找到 core 下的兄弟模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from core.swarm import swarm_engine
from core.benchmark import benchmark_engine

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# 若填入白名单，则只响应指定的主理人 ID 或群组 ID (用逗号分割)
TELEGRAM_ALLOWLIST = os.getenv("TELEGRAM_ALLOWLIST", "")

def is_allowed(chat_id: str) -> bool:
    if not TELEGRAM_ALLOWLIST:
        return True
    allowed_ids = [x.strip() for x in TELEGRAM_ALLOWLIST.split(",")]
    return chat_id in allowed_ids

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        return

    welcome_msg = (
        "🔗 **[YI-CORE // 破军阵 联邦中枢] 已接入**\n\n"
        f"该阵地唯一信标 ID: `{chat_id}`\n"
        "主理人，请下达任务指令。CEO 及其联邦下属节点已就位，随时准备拆解或执行网关算子。"
    )
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def set_group_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    指令提取： /role [你的阵地属性描述]
    """
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        return
        
    rules = " ".join(context.args)
    if not rules:
        await update.message.reply_text("💡 请附加具体的阵地指令。如: `/role 这是一个只发IT新闻的群组，不管让你干什么，最后都要用新闻口吻汇报。`", parse_mode='Markdown')
        return
        
    context.chat_data["group_role"] = rules
    await update.message.reply_text(f"✅ **阵地法则已烙印**:\n{rules}\n\n以后的每一次指令，联邦特工都将服从该最高规则。", parse_mode='Markdown')

async def run_benchmark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    指令提取： /benchmark model_a, model_b
    """
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id): return
    
    models_str = " ".join(context.args)
    if not models_str:
        await update.message.reply_text("💡 必须提供要测跑的模型名。如: `/benchmark deepseek/deepseek-chat, google/gemini-2.5-pro:free`", parse_mode='Markdown')
        return
        
    models = [m.strip() for m in models_str.split(",") if m.strip()]
    
    status_msg = await update.message.reply_text("🚨 **[联邦征兵测试已启动]**\n\n正在并发下放高压考卷 (Logic, Tool, Security)...请等待系统汇报榜单 (耗时约1-3分钟)。", parse_mode='Markdown')
    
    try:
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, benchmark_engine.batch_run, models)
        
        reply = "🏆 **【算力大逃杀 终局榜单】**\n\n"
        for idx, res in enumerate(results):
            reply += f"🏅 Rank {idx+1}: `{res['model_name']}`\n"
            reply += f"⊢ 智能评级: **{res['rating']}** (得分:{res['overall_score']})\n"
            reply += f"⊢ 生存通关率: {res['success_rate']}\n\n"
            
        rec_cfg = benchmark_engine.generate_swarm_dispatch_recommendation(results)
        
        # 保存进内核并通知
        import os, json
        config_file = os.path.join(os.path.dirname(__file__), "swarm_config.json")
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, "w") as f:
            json.dump(rec_cfg, f, indent=4)
            
        reply += "⚙️ **【联邦职能重组报告】**\n系统已根据各节点专长，将最优胜者自动硬编码至底层：\n"
        reply += f"🧠 破军枢纽 (CEO): `{rec_cfg.get('CEO')}`\n"
        reply += f"💻 硅基黑客 (Coder): `{rec_cfg.get('Coder')}`\n"
        reply += f"📣 情报宣发 (Social): `{rec_cfg.get('Social')}`\n\n"
        reply += "*从此刻起，全阵地已采用此神阶编制为您效命。*"
        
        await status_msg.edit_text(reply, parse_mode='Markdown')
    except Exception as e:
        await status_msg.edit_text(f"🛑 测跑场地遭遇崩溃: {str(e)}")

async def get_sysinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    查看当前系统状态 /sysinfo
    """
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id): return
    
    import os, json
    config_file = os.path.join(os.path.dirname(__file__), "swarm_config.json")
    ceo_model = "未设专属"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                cfg = json.load(f)
                ceo_model = cfg.get("CEO", "")
        except: pass
        
    fallback_models = os.getenv("OPENROUTER_DEFAULT_MODELS", "默认保底池")
    
    msg = (
        "📊 **【YI-CORE // 破军阵 仪表盘】**\n\n"
        f"👑 当前主脑 (CEO): `{ceo_model}`\n"
        f"🛡️ 替补存活阵列: `{fallback_models}`\n\n"
        "💡 提示：键入 `/role` 可为当前群组注入独立人格；键入 `/benchmark` 可开启选拔并洗牌挂载架构。"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        print(f"[TG/Drop] 未授权的信标探测: {chat_id}")
        return

    text = update.message.text or update.message.caption or ""
    
    # 【感官进化】：检测是否包含图片 (视网膜输入)
    image_b64 = None
    if update.message.photo:
        try:
            print(f"[TG/Recv] 收到信标 {chat_id} 传回的视觉影像流...")
            # 取最高分辨率的图
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            # 下载到内存
            import io, base64
            img_byte_arr = io.BytesIO()
            await file.download_to_memory(out=img_byte_arr)
            img_byte_arr.seek(0)
            image_b64 = base64.b64encode(img_byte_arr.read()).decode('utf-8')
            if not text:
                 text = "请简要描述这张图里有什么。"
        except Exception as e:
            await update.message.reply_text(f"🛑 神经视觉通道解析失败: {e}")
            return
            
    if not text and not image_b64:
        return
        
    print(f"[TG/Recv] 来自信标 {chat_id} 的指令: {text[:50]}... [图片附加: {bool(image_b64)}]")
    
    # 立即响应防止超时
    status_msg = await update.message.reply_text("⏳ 原生视觉与算力节点联合推演中...")
    
    try:
        group_role = context.chat_data.get("group_role", "")
        # 转给 Swarm 系统
        # 使用 run_in_executor 防止阻塞异步事件循环
        loop = asyncio.get_running_loop()
        reply = await loop.run_in_executor(
            None, 
            swarm_engine.process_chat, 
            chat_id, 
            text, 
            group_role,
            image_b64
        )
        
        # 字数过长时切片发送
        MAX_LENGTH = 4000
        if len(reply) > MAX_LENGTH:
            await status_msg.edit_text(reply[:MAX_LENGTH])
            for i in range(MAX_LENGTH, len(reply), MAX_LENGTH):
                await update.message.reply_text(reply[i:i+MAX_LENGTH])
        else:
            await status_msg.edit_text(reply)
            
    except Exception as e:
        await status_msg.edit_text(f"🛑 [系统异常截断] 联邦节点遭遇了物理宕机或算力断裂:\n{str(e)}")

def start_hub():
    if not TELEGRAM_BOT_TOKEN:
        print("[YI-CORE/Telegram] 缺少 TELEGRAM_BOT_TOKEN，社交网关未挂载。")
        return

    print("[YI-CORE/Telegram] 🚀 社会化联邦中枢正在点火监听...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("role", set_group_role))
    application.add_handler(CommandHandler("benchmark", run_benchmark))
    application.add_handler(CommandHandler("sysinfo", get_sysinfo))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO & ~filters.COMMAND, handle_message))

    # 运行轮询
    application.run_polling()

if __name__ == "__main__":
    start_hub()
