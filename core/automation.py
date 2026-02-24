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
