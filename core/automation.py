# core/automation.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import time

scheduler = BackgroundScheduler()

def example_task():
    """测试用自动化拉取数据"""
    print(f"[YI-CORE/Auto] 执行时间感知任务 - 当前时间: {datetime.now()}")
    # TODO: 接入 LLM 触发总结逻辑

def add_llm_job(skill_name: str, cron_expression: str, args: dict = None):
    """供大语言模型调用的动态任务装填器"""
    global scheduler
    if not scheduler.running:
        return "调度器未运行，请先确保框架点火成功。"
    
    # 延迟导入防止循环依赖
    from .skills import execute_skill
    
    def job_wrapper():
        print(f"[YI-CORE/Auto] 🕒 自动触发挂载的算子: {skill_name}")
        execute_skill(skill_name, args or {})
        
    try:
        trigger = CronTrigger.from_crontab(cron_expression)
        job_id = f"auto_task_{int(time.time())}"
        scheduler.add_job(
            job_wrapper,
            trigger=trigger,
            id=job_id,
            name=f"AI挂载守护: {skill_name}"
        )
        return f"定时任务挂载成功！防线代号: {job_id}, 触发规则: {cron_expression}"
    except Exception as e:
        return f"装填自动化防线失败: 本地内核拒绝了 Cron 格式 -> {str(e)}"

def init_automation():
    """初始化并启动调度器"""
    global scheduler
    
    if not scheduler.running:
        # 添加一个测试 Cron 触发器：每天8点 (可根据主理人需求配置)
        scheduler.add_job(
            example_task,
            trigger=CronTrigger(hour=8, minute=0),
            id='morning_briefing',
            name='Daily Morning Briefing'
        )
        scheduler.start()
        print("[YI-CORE] 后台自动化引擎已启动。")

def get_jobs():
    """获取当前挂载的异步任务"""
    if not scheduler.running:
        return []
    return [{"id": job.id, "name": job.name, "next_run_time": job.next_run_time} for job in scheduler.get_jobs()]
