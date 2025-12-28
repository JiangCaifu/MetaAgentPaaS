import sqlite3
import datetime
from typing import List, Dict
from utils.logger_config import logger


class ConversationDB:
    def __init__(self, db_path: str = "metaagentpaas.db"):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        """初始化对话表（兼容租户逻辑）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 对话记录表（关联租户ID）
        cursor.execute('''CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,  -- 新增：租户ID（插入所需）
                agent_ids TEXT NOT NULL,  -- 新增：Agent ID列表（插入所需）
                user_query TEXT NOT NULL, -- 新增：用户查询内容（插入所需）
                aggregated_result TEXT NOT NULL, -- 新增：聚合结果（插入所需）
                conversation_id TEXT NOT NULL, -- 新增：对话ID（插入所需）
                user_id TEXT DEFAULT '',  -- 移除 NOT NULL，设置默认空字符串
                content TEXT DEFAULT '', -- 移除 NOT NULL，设置默认空字符串
                create_time TEXT DEFAULT '' -- 移除 NOT NULL，设置默认空字符串
            )''')
        conn.commit()
        conn.close()
        logger.info("数据库表初始化完成")

    def add_conversation(self, tenant_id: str, agent_ids: List[str], user_query: str, aggregated_result: str,
                         conversation_id: str):
        """新增对话记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO conversations 
            (tenant_id, agent_ids, user_query, aggregated_result, conversation_id)
            VALUES (?, ?, ?, ?, ?)
            ''', (tenant_id, ",".join(agent_ids), user_query, aggregated_result, conversation_id))
            conn.commit()
            conn.close()
            logger.info(f"对话记录保存成功：{conversation_id}")
        except Exception as e:
            logger.error(f"保存对话记录失败：{str(e)}")
            raise

    def get_conversations(self, tenant_id: str) -> List[Dict]:
        """查询租户历史对话"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 支持按列名访问
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM conversations WHERE tenant_id = ? ORDER BY create_time DESC
            ''', (tenant_id,))
            rows = cursor.fetchall()
            conn.close()

            # 转换为字典列表
            result = []
            for row in rows:
                result.append({
                    "id": row["id"],
                    "tenant_id": row["tenant_id"],
                    "agent_ids": row["agent_ids"].split(","),
                    "user_query": row["user_query"],
                    "aggregated_result": row["aggregated_result"],
                    "conversation_id": row["conversation_id"],
                    "create_time": row["create_time"]
                })
            logger.info(f"查询租户{tenant_id}历史对话，共{len(result)}条")
            return result
        except Exception as e:
            logger.error(f"查询对话失败：{str(e)}")
            raise