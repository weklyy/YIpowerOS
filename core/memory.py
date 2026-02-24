# core/memory.py
import sqlite3
import json
import os
from datetime import datetime

# 存储在项目根目录
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'yicore_storage.db')

def init_db():
    """初始化历史记忆表结构"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def save_memory(role: str, content: str):
    """
    将单条对话记录永久写入 SQLite
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO chat_history (role, content) VALUES (?, ?)',
            (role, content)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[YI-CORE/Memory] 记忆写入失败: {e}")

def load_recent_memory(limit: int = 20) -> list[dict]:
    """
    启动时读取最近 N 条记忆
    """
    if not os.path.exists(DB_PATH):
        init_db()
        return []

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # 降序查询最新 N 条，然后再反转成升序给上下文
        cursor.execute(
            'SELECT role, content FROM chat_history ORDER BY id DESC LIMIT ?', 
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        # 将结果反转回正确的时序
        messages = [{"role": row[0], "content": row[1]} for row in reversed(rows)]
        return messages
    except Exception as e:
        print(f"[YI-CORE/Memory] 记忆提取失败: {e}")
        return []

def clear_memory():
    """核弹清空记忆"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM chat_history')
        # 重置自增 ID (可选)
        cursor.execute('DELETE FROM sqlite_sequence WHERE name="chat_history"')
        conn.commit()
        conn.close()
    except Exception as e:
        pass

# 首次引入时确保表存在
init_db()
