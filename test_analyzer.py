"""
核心分析模块 (`analyzer.py`) 的测试脚本
"""
import pandas as pd
import os
from pprint import pprint
from datetime import datetime, timedelta

# 假设这些模块都在同一个父目录下，或者已经配置好了 PYTHONPATH
from config_loader import load_config
from analyzer import analyze

def create_test_dataframe() -> pd.DataFrame:
    """
    创建一个用于测试的 DataFrame，模拟从 data_loader 清洗后的数据
    """
    # 获取今天的日期，以便创建相关的测试数据
    today = datetime.now()
    
    data = {
        'summary': [
            "修复登录页面的 on-fire bug", "一个非常旧的未完成任务", "一个普通的进行中任务",
            "一个低优先级已完成任务", "带有 critical-bug 标签的问题", "未分配模块的任务"
        ],
        'status': [
            "进行中", "待办", "进行中", "已完成", "待办", "进行中"
        ],
        'priority': [
            "高", "高", "中", "低", "高", "中"
        ],
        'module': [
            "用户认证", "订单系统", "用户认证", "支付网关", "订单系统", None
        ],
        'created_date': [
            (today - timedelta(days=5)).strftime('%Y-%m-%d'),
            (today - timedelta(days=30)).strftime('%Y-%m-%d'), # 这个会是超期任务
            (today - timedelta(days=10)).strftime('%Y-%m-%d'),
            (today - timedelta(days=20)).strftime('%Y-%m-%d'),
            (today - timedelta(days=2)).strftime('%Y-%m-%d'),
            (today - timedelta(days=1)).strftime('%Y-%m-%d'),
        ],
        'assignee': [
            "张三", "李四", "王五", "张三", "李四", "赵六"
        ],
        'reporter': [
            "产品A", "测试B", "开发C", "开发D", "测试E", "产品F"
        ],
        'tags': [
            "on-fire,backend", "performance", "frontend", "refactor", "critical-bug", ""
        ]
    }
    df = pd.DataFrame(data)

    # 模拟 data_loader 中的数据清洗步骤
    df['created_date'] = pd.to_datetime(df['created_date'])
    df['module'] = df['module'].fillna('未分配模块')
    
    return df

def main():
    """
    主测试函数
    """
    print("--- 开始测试核心分析模块 (analyzer.py) ---")

    # 1. 加载配置
    try:
        # 确保配置文件在正确的路径
        config = load_config('config.ini')
        print("✅ 配置加载成功。")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return

    # 2. 创建测试数据
    test_df = create_test_dataframe()
    print("✅ 测试数据创建成功。")
    print("\n--- 输入的测试 DataFrame ---")
    print(test_df)
    print("-" * 30)

    # 3. 运行分析模块
    try:
        analysis_results = analyze(test_df, config)
        print("✅ 分析函数运行成功。")
    except Exception as e:
        print(f"❌ 分析函数运行时出错: {e}")
        return

    # 4. 打印分析结果
    print("\n--- 分析结果 ---")
    pprint(analysis_results)
    print("-" * 30)
    
    # 5. 简单验证
    print("\n--- 结果验证 ---")
    assert analysis_results['overall_metrics']['total_issues'] == 6
    print("✅ 总体指标：问题总数正确。")
    
    assert analysis_results['overdue_issues'][0]['summary'] == "一个非常旧的未完成任务"
    print("✅ 超时问题：已正确识别。")

    assert len(analysis_results['tagged_issues']) == 2
    print("✅ 特定标签问题：已正确识别。")
    
    assert analysis_results['module_distribution']['未分配模块'] == 1
    print("✅ 模块分布：未分配模块已正确统计。")
    
    print("\n--- 核心分析模块测试完成 ---")


if __name__ == "__main__":
    main() 