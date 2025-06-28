import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import os

# 定义要生成的历史数据天数
NUM_DAYS = 15

# 定义指标和其初始值、每日递减范围
METRICS_CONFIG = {
    'A': {'start': 40, 'decay': [1, 5]},
    'B': {'start': 80, 'decay': [2, 8]},
    'C': {'start': 120, 'decay': [5, 10]},
    'DI': {'start': 800, 'decay': [20, 50]},
    'total': {'start': 240, 'decay': [10, 20]}
}

# --- 生成数据 ---
today = datetime.now()
dates = [today - timedelta(days=i) for i in range(NUM_DAYS)][::-1] # 从过去到今天

history_data = {'date': [d.strftime('%Y-%m-%d') for d in dates]}

for metric, config in METRICS_CONFIG.items():
    values = []
    current_value = config['start']
    for _ in range(NUM_DAYS):
        # 确保值不为负
        current_value = max(0, current_value - np.random.randint(config['decay'][0], config['decay'][1] + 1))
        values.append(current_value)
    history_data[metric] = values

df = pd.DataFrame(history_data)

# --- 保存文件 ---
history_file_path = 'data/history.csv'
os.makedirs('data', exist_ok=True)
df.to_csv(history_file_path, index=False)

print(f"成功生成了包含 {NUM_DAYS} 天模拟数据的历史文件: {history_file_path}") 