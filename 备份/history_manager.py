import pandas as pd
import os
from datetime import date

class HistoryManager:
    """
    管理历史数据文件，提供读取、追加/更新和保存历史指标的功能。
    """
    def __init__(self, history_file_path: str):
        """
        初始化 HistoryManager。

        参数:
            history_file_path (str): 历史数据CSV文件的路径。
        """
        self.history_file_path = history_file_path
        self.history_df = self._load()

    def _load(self) -> pd.DataFrame:
        """
        从CSV文件加载历史数据。如果文件不存在，则返回一个空的DataFrame。
        """
        try:
            df = pd.read_csv(self.history_file_path)
            # 确保 'date' 列是日期对象，以便进行比较
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.date
            return df
        except FileNotFoundError:
            # 文件不存在时，返回一个空的DataFrame，列将在第一次添加记录时创建
            return pd.DataFrame()

    def add_record(self, new_metrics: dict):
        """
        添加或更新当天的记录。

        如果当天已经有记录，旧记录将被新记录替换。

        参数:
            new_metrics (dict): 包含当天新指标的字典。
        """
        today = date.today()
        
        # 检查DataFrame中是否已存在今天的记录，如果存在则将其移除
        if not self.history_df.empty and 'date' in self.history_df.columns:
            if today in self.history_df['date'].values:
                self.history_df = self.history_df[self.history_df['date'] != today].copy()

        # 准备新记录并转换为DataFrame
        record_data = {'date': today, **new_metrics}
        new_row_df = pd.DataFrame([record_data])

        # 将新记录追加到历史数据中
        self.history_df = pd.concat([self.history_df, new_row_df], ignore_index=True)
        
        # 按日期排序，保持CSV文件整洁
        self.history_df = self.history_df.sort_values(by='date').reset_index(drop=True)

    def save(self):
        """
        将内存中的历史数据DataFrame保存回CSV文件。
        """
        # 确保输出目录存在
        output_dir = os.path.dirname(self.history_file_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        self.history_df.to_csv(self.history_file_path, index=False)

def update_history(history_file_path: str, new_metrics: dict) -> pd.DataFrame:
    """
    一个便捷函数，用于实例化HistoryManager、添加记录、保存并返回更新后的DataFrame。

    参数:
        history_file_path (str): 历史数据CSV文件的路径。
        new_metrics (dict): 包含当天新指标的字典。

    返回:
        pd.DataFrame: 更新后的完整历史数据。
    """
    manager = HistoryManager(history_file_path)
    manager.add_record(new_metrics)
    manager.save()
    return manager.history_df

# --- 测试代码 ---
if __name__ == '__main__':
    print("开始测试 HistoryManager 模块...")

    # 定义测试用的历史文件路径
    test_history_file = os.path.join('output', 'history.csv')
    
    # 为了确保每次测试都是全新的开始，先删除旧的测试文件
    if os.path.exists(test_history_file):
        os.remove(test_history_file)
        print(f"已删除旧的测试文件: {test_history_file}")

    # 1. 第一次添加当天的记录
    print("\n--- 步骤 1: 第一次添加记录 ---")
    daily_metrics_1 = {'total_tasks': 100, 'completed': 80, 'new': 5}
    history1 = update_history(test_history_file, daily_metrics_1)
    print("成功添加第一条记录。当前历史数据:")
    print(history1)

    # 2. 第二次添加当天的记录（模拟更新）
    print("\n--- 步骤 2: 更新当天记录 ---")
    daily_metrics_2 = {'total_tasks': 102, 'completed': 85, 'new': 7}
    history2 = update_history(test_history_file, daily_metrics_2)
    print("成功更新当天记录。当前历史数据:")
    print(history2)

    # 3. 验证文件内容
    print("\n--- 步骤 3: 验证CSV文件内容 ---")
    if os.path.exists(test_history_file):
        final_df = pd.read_csv(test_history_file)
        print("从CSV文件直接读取的数据:")
        print(final_df)
        # 简单的断言来验证更新是否成功
        assert len(final_df) == 1
        assert final_df.iloc[0]['total_tasks'] == 102
        print("断言成功：记录总数为1，且任务总数已更新为102。")
    else:
        print("错误：未找到历史文件！")

    print("\nHistoryManager 模块测试完成。") 