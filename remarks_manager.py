import pandas as pd
import sqlite3
import os
from database_manager import DB_FILE

class RemarksManager:
    """
    Manages the synchronization and retrieval of JIRA issue remarks.
    """
    def sync_remarks_from_csv(self, csv_path='remarks.csv'):
        """
        Reads remarks from a CSV file and syncs them to the database.
        The CSV file must have 'jira_key' and 'remark' columns.
        """
        if not os.path.exists(csv_path):
            print(f"备注文件未找到: {csv_path}。跳过备注同步。")
            return

        try:
            remarks_df = pd.read_csv(csv_path)
            # 校验表头
            if 'jira_key' not in remarks_df.columns or 'remark' not in remarks_df.columns:
                print(f"错误: 备注文件 {csv_path} 必须包含 'jira_key' 和 'remark' 列。")
                return

            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                for _, row in remarks_df.iterrows():
                    jira_key = row['jira_key']
                    remark = row['remark']
                    # 使用 INSERT OR REPLACE 实现插入或更新
                    query = "INSERT OR REPLACE INTO jira_remarks (jira_key, remark) VALUES (?, ?)"
                    cursor.execute(query, (jira_key, remark))
                conn.commit()
            print(f"成功从 {csv_path} 同步 {len(remarks_df)} 条备注到数据库。")
        except pd.errors.EmptyDataError:
            print(f"警告: 备注文件 {csv_path} 为空。")
        except Exception as e:
            print(f"同步备注失败: {e}")

    def get_all_remarks(self):
        """
        Retrieves all remarks from the database.

        Returns:
            dict: A dictionary with jira_key as key and remark as value.
        """
        remarks_dict = {}
        try:
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT jira_key, remark FROM jira_remarks")
                rows = cursor.fetchall()
                remarks_dict = {row[0]: row[1] for row in rows}
        except Exception as e:
            print(f"从数据库获取备注失败: {e}")
        return remarks_dict

    def update_remark(self, jira_key, new_remark, csv_path='remarks.csv'):
        """
        Updates a remark in both the database and the CSV file.

        Args:
            jira_key (str): The JIRA key of the issue.
            new_remark (str): The new remark text.
            csv_path (str): The path to the remarks CSV file.
        
        Returns:
            bool: True if update was successful, False otherwise.
        """
        try:
            # 1. Update the database
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                query = "INSERT OR REPLACE INTO jira_remarks (jira_key, remark) VALUES (?, ?)"
                cursor.execute(query, (jira_key, new_remark))
                conn.commit()
            
            # 2. Update the CSV file
            # Read all data from DB to ensure CSV is a full reflection of the DB state.
            all_remarks = self.get_all_remarks()
            # It's possible the key was just added, so update the local dict
            all_remarks[jira_key] = new_remark
            
            remarks_df = pd.DataFrame(list(all_remarks.items()), columns=['jira_key', 'remark'])
            remarks_df.to_csv(csv_path, index=False, encoding='utf-8')
            
            print(f"成功更新备注 {jira_key} 并同步到 {csv_path}。")
            return True
        except Exception as e:
            print(f"更新备注失败 for key {jira_key}: {e}")
            return False 