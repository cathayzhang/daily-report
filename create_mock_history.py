import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import os
import sys

# 确保项目根目录在 sys.path 中，以便导入其他模块
sys.path.append(os.getcwd())

import history_manager
import database_manager

# --- 配置 ---
NUM_DAYS = 15
METRICS_CONFIG = {
    'total_issues': {'start': 240, 'decay': [5, 15]},
    'A级': {'start': 40, 'decay': [1, 5]},
    'B级': {'start': 80, 'decay': [2, 8]},
    'C级': {'start': 120, 'decay': [3, 10]},
    'di_value': {'start': 800, 'decay': [20, 50]},
}

def create_and_save_mock_data():
    """
    生成模拟的KPI数据并将其逐条保存到SQLite数据库中。
    """
    print("开始生成并保存模拟历史数据到数据库...")
    
    # 1. 确保数据库和表已创建
    database_manager.init_db()

    # 2. 生成模拟数据
    today = datetime.now()
    dates = [today - timedelta(days=i) for i in range(NUM_DAYS)][::-1] # 从过去到现在

    # 为每个指标独立生成时间序列
    data_columns = {}
    for metric, config in METRICS_CONFIG.items():
        values = []
        current_value = config['start']
        for _ in range(NUM_DAYS):
            decay = np.random.randint(config['decay'][0], config['decay'][1] + 1)
            current_value = max(0, current_value - decay)
            values.append(current_value)
        data_columns[metric] = values

    # 3. 逐天保存到数据库
    for i in range(NUM_DAYS):
        report_date = dates[i].date()
        kpis_dict = {metric: data_columns[metric][i] for metric in METRICS_CONFIG}
        
        # 将Numpy类型转换为Python原生类型
        for key, value in kpis_dict.items():
            if isinstance(value, np.integer):
                kpis_dict[key] = int(value)
            elif isinstance(value, np.floating):
                kpis_dict[key] = float(value)

        history_manager.save_kpis(report_date, kpis_dict)

    print(f"\n成功生成并保存了 {NUM_DAYS} 天的模拟历史数据到数据库 'dev_report.db'。")

if __name__ == '__main__':
    create_and_save_mock_data() 