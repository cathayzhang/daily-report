import sqlite3
import pandas as pd
import os

DB_FILE = 'dev_report.db'

def init_db():
    """
    Initializes the database and creates the necessary tables if they don't exist.
    """
    # SQL statements to create tables
    CREATE_DAILY_KPIS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS daily_kpis (
        report_date TEXT PRIMARY KEY, -- 报告日期 (格式: 'YYYY-MM-DD')，作为唯一标识
        total_issues INTEGER,       -- 当日JIRA问题总数
        a_issues INTEGER,           -- 当日A级问题数
        b_issues INTEGER,           -- 当日B级问题数
        c_issues INTEGER,           -- 当日C级问题数
        di_value REAL               -- 当日计算出的DI（缺陷指数）值
    );
    """
    
    CREATE_JIRA_REMARKS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS jira_remarks (
        jira_key TEXT PRIMARY KEY,    -- JIRA 问题唯一标识 (例如: 'PROJ-123')
        remark TEXT                   -- 备注的具体内容
    );
    """
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(CREATE_DAILY_KPIS_TABLE_SQL)
            cursor.execute(CREATE_JIRA_REMARKS_TABLE_SQL)
        print("数据库初始化完成。")
    except sqlite3.Error as e:
        print(f"数据库初始化失败: {e}")

def execute_update(query, params=()):
    """
    Executes an update (INSERT, UPDATE, DELETE) query.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
    except sqlite3.Error as e:
        print(f"数据库更新操作失败: {e}")

def query_to_dataframe(query, params=()):
    """
    Executes a SELECT query and returns the results as a pandas DataFrame.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            df = pd.read_sql_query(query, conn, params=params)
        return df
    except sqlite3.Error as e:
        print(f"数据库查询操作失败: {e}")
        return pd.DataFrame() 