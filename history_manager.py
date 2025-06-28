import pandas as pd
import database_manager
from datetime import date

def save_kpis(report_date: date, kpis_dict: dict):
    """
    将单日的KPI数据保存到数据库。如果当天记录已存在，则更新。

    参数:
        report_date (date): 报告日期。
        kpis_dict (dict): 包含KPI指标的字典。
    """
    report_date_str = report_date.strftime('%Y-%m-%d')
    
    # 在方案中，a_issues, b_issues, c_issues 的字段名是'A级', 'B级', 'C级'
    # 但是在数据库中的字段名是 a_issues, b_issues, c_issues
    # 所以在这里需要做一个映射
    params = (
        report_date_str,
        kpis_dict.get('total_issues'),
        kpis_dict.get('A级'),
        kpis_dict.get('B级'),
        kpis_dict.get('C级'),
        kpis_dict.get('di_value')
    )
    
    query = """
    INSERT OR REPLACE INTO daily_kpis (report_date, total_issues, a_issues, b_issues, c_issues, di_value)
    VALUES (?, ?, ?, ?, ?, ?);
    """
    
    database_manager.execute_update(query, params)
    print(f"已成功保存 {report_date_str} 的KPI数据到数据库。")

def load_kpi_history() -> pd.DataFrame:
    """
    从数据库加载所有KPI历史数据，并按日期升序排序。

    返回:
        pd.DataFrame: 包含所有历史KPI数据的DataFrame。
    """
    query = "SELECT * FROM daily_kpis ORDER BY report_date ASC;"
    history_df = database_manager.query_to_dataframe(query)
    
    if not history_df.empty:
        # 将 report_date 列转换为 datetime 对象，并重命名为 'date' 以便兼容旧代码
        history_df['report_date'] = pd.to_datetime(history_df['report_date'])
        history_df.rename(columns={'report_date': 'date'}, inplace=True)
    
    print("已从数据库加载KPI历史数据。")
    return history_df 