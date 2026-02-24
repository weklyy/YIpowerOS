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
        "🔗 **[YI-CORE // 破军阵 联邦中枢] 已接入**\\n\\n"
        f"该阵地唯一信标 ID: `{chat_id}`\\n"
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
    await update.message.reply_text(f"✅ **阵地法则已烙印**:\\n{rules}\\n\\n以后的每一次指令，联邦特工都将服从该最高规则。", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not is_allowed(chat_id):
        print(f"[TG/Drop] 未授权的信标探测: {chat_id}")
        return

    text = update.message.text
    if not text:
        return
        
    print(f"[TG/Recv] 来自信标 {chat_id} 的指令: {text[:50]}...")
    
    # 立即响应防止超时
    status_msg = await update.message.reply_text("⏳ 联邦算力节点推演中...")
    
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
            group_role
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
        await status_msg.edit_text(f"🛑 [系统异常截断] 联邦节点遭遇了物理宕机或算力断裂:\\n{str(e)}")

def start_hub():
    if not TELEGRAM_BOT_TOKEN:
        print("[YI-CORE/Telegram] 缺少 TELEGRAM_BOT_TOKEN，社交网关未挂载。")
        return

    print("[YI-CORE/Telegram] 🚀 社会化联邦中枢正在点火监听...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("role", set_group_role))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 运行轮询
    application.run_polling()

if __name__ == "__main__":
    start_hub()
