"""
核心分析模块
"""
import pandas as pd
from config_loader import Config
from datetime import datetime, timedelta
import numpy as np

def calculate_kpis(df: pd.DataFrame, history_df: pd.DataFrame, config: Config) -> dict:
    """
    计算报告所需的核心KPI指标。
    """
    kpis = {}
    today = datetime.now().date()
    
    # 1. 收敛偏差
    plan = config.convergence_plan
    total_issues = len(df)
    kpis['total_issues'] = total_issues
    
    start_date = datetime.strptime(plan['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(plan['end_date'], '%Y-%m-%d').date()
    
    planned_today = np.nan
    if start_date <= today <= end_date:
        days_in_plan = (end_date - start_date).days
        days_from_start = (today - start_date).days
        if days_in_plan > 0:
            planned_today = plan['start_count'] - (plan['start_count'] - plan['end_count']) * (days_from_start / days_in_plan)
    
    if not pd.isna(planned_today):
        convergence_deviation = total_issues - planned_today
        kpis['convergence_deviation'] = round(convergence_deviation)
        kpis['planned_today_count'] = round(planned_today)
    else:
        kpis['convergence_deviation'] = None # 不在计划周期内
        kpis['planned_today_count'] = None

    # 2. A类问题7日变化
    a_priority_name = config.a_priority_name
    current_a_issues = df[df['priority'] == a_priority_name].shape[0]
    kpis['current_a_issues_count'] = current_a_issues
    
    seven_days_ago = today - timedelta(days=7)
    history_df['date'] = pd.to_datetime(history_df['date']).dt.date
    past_data = history_df[history_df['date'] <= seven_days_ago]
    
    if not past_data.empty:
        closest_date = past_data['date'].max()
        past_a_issues = past_data[past_data['date'] == closest_date][a_priority_name].iloc[0]
        kpis['a_issues_7_day_change'] = current_a_issues - past_a_issues
        kpis['a_issues_7_day_change_has_history'] = True
    else:
        kpis['a_issues_7_day_change'] = current_a_issues
        kpis['a_issues_7_day_change_has_history'] = False

    # 3. 风险最集中模块
    risk_priorities = config.risk_module_priorities
    risk_df = df[df['priority'].isin(risk_priorities)]
    if not risk_df.empty and 'module' in risk_df.columns:
        riskiest_module_series = risk_df['module'].value_counts()
        riskiest_module_name = riskiest_module_series.index[0]
        riskiest_module_count = int(riskiest_module_series.iloc[0])

        total_risk_issues = risk_df.shape[0]
        riskiest_module_percentage = (riskiest_module_count / total_risk_issues) * 100 if total_risk_issues > 0 else 0

        kpis['riskiest_module'] = {
            'name': riskiest_module_name,
            'count': riskiest_module_count,
            'percentage_of_total_risk': round(riskiest_module_percentage)
        }
    else:
        kpis['riskiest_module'] = None
        
    # 4. 其他简单KPI
    kpis['a_blocker_count'] = df[df['priority'] == config.a_priority_name].shape[0]
    priority_counts = df['priority'].value_counts()
    kpis['priority_distribution_summary'] = f"A:{priority_counts.get(config.a_priority_name, 0)} / B:{priority_counts.get('Critical', 0)} / C:{priority_counts.get('High', 0)+priority_counts.get('Medium', 0)}"
    kpis['a_priority_percentage'] = round((kpis['a_blocker_count'] / total_issues) * 100) if total_issues > 0 else 0

    return kpis

def generate_analysis_and_recommendations(kpis: dict) -> dict:
    """
    基于KPI生成分析和建议文案。
    """
    analysis = []
    recommendations = []

    # 分析收敛偏差
    if kpis.get('convergence_deviation') is not None and kpis['convergence_deviation'] > 0:
        deviation = kpis['convergence_deviation']
        analysis.append(f"当前的 <strong>收敛偏差</strong> 显示项目已落后计划 <strong>{deviation}</strong> 个问题。此偏差是由以下因素叠加导致：")
        
        factors = []
        # 分析A类问题趋势
        if kpis.get('a_issues_7_day_change', 0) > 0:
            change = kpis['a_issues_7_day_change']
            has_history_str = "" if kpis.get('a_issues_7_day_change_has_history') else "，且历史数据不足7天，"
            factors.append(f"<strong>核心风险加剧：</strong> A类问题7日内净增 <strong>+{change}</strong> 个{has_history_str}表明关键问题非但没有收敛，反而在持续累积。")

        # 分析风险模块
        if kpis.get('riskiest_module'):
            module = kpis['riskiest_module']
            factors.append(f"<strong>瓶颈效应凸显：</strong> <strong>{module['name']}</strong> 是风险最集中模块，该模块贡献了 {module['percentage_of_total_risk']}% 的高风险问题。")
        
        if factors:
            analysis.append("<ul><li>" + "</li><li>".join(factors) + "</li></ul>")

        recommendations.append(f"<strong>立即聚焦核心瓶颈：</strong> 建议立即召开 <strong><code>{kpis.get('riskiest_module', {}).get('name', '未知')}</code></strong> 的专题同步会。<strong>理由：</strong> 该模块是当前收敛落后的主要贡献者，需紧急评审其问题列表，识别瓶颈并重新分配资源。")

    # 分析Blocker
    if kpis.get('a_blocker_count', 0) > 0:
        blocker_count = kpis['a_blocker_count']
        analysis.append(f"存在的 <strong>{blocker_count}</strong> 个A类Blocker问题，直接阻碍了版本发布，并推高了存量总数。")
        recommendations.append(f"<strong>启动Blocker攻坚计划：</strong> 建议为 <strong>{blocker_count}</strong> 个A类Blocker问题成立攻坚小组，每日站会跟踪。<strong>理由：</strong> Blocker问题是最高优先级，解决它们能最快速度降低项目风险。")

    if not analysis:
        analysis.append("项目当前状态良好，各项指标均在可控范围内。")
    if not recommendations:
        recommendations.append("继续保持当前节奏，关注重点任务的完成情况。")

    return {
        "objective_analysis": "<ul><li>" + "</li><li>".join(analysis) + "</li></ul>",
        "actionable_recommendations": "<ol><li>" + "</li><li>".join(recommendations) + "</li></ol>"
    }

def analyze_overall_metrics(df: pd.DataFrame) -> dict:
    """
    分析总体指标
    :param df: 输入的DataFrame
    :return: 包含总体指标的字典
    """
    total_count = len(df)
    # 使用内部标准列名 'status'
    resolved_count = df[df['status'] == '已完成'].shape[0]
    unresolved_count = total_count - resolved_count
    # 假设 'created_date' 列存在, 并且是 datetime 类型
    # new_today_count = df[df['created_date'].dt.date == pd.Timestamp.now().date()].shape[0]
    
    return {
        "total_issues": total_count,
        "resolved_issues": resolved_count,
        "unresolved_issues": unresolved_count,
        # "new_today": new_today_count,
    }

def analyze_priority_distribution(df: pd.DataFrame) -> dict:
    """
    分析优先级分布
    :param df: 输入的DataFrame
    :return: 包含优先级分布的字典
    """
    # 使用内部标准列名 'priority'
    return df['priority'].value_counts().to_dict()

def analyze_status_distribution(df: pd.DataFrame) -> dict:
    """
    分析状态分布
    :param df: 输入的DataFrame
    :return: 包含状态分布的字典
    """
    # 使用内部标准列名 'status'
    return df['status'].value_counts().to_dict()

def analyze_module_distribution(df: pd.DataFrame) -> dict:
    """
    分析模块分布
    :param df: 输入的DataFrame
    :return: 包含模块分布的字典
    """
    # 使用内部标准列名 'module'
    if 'module' not in df.columns:
        return {}
    return df['module'].value_counts().to_dict()

def analyze_overdue_issues(df: pd.DataFrame, overdue_threshold_days: int) -> list[dict]:
    """
    分析超时问题
    :param df: 输入的DataFrame
    :param overdue_threshold_days: 超时阈值（天）
    :return: 超时问题列表
    """
    # 筛选未完成的问题
    unresolved = df[df['status'] != '已完成'].copy()
    
    # 筛选出超期问题
    overdue_issues = unresolved[unresolved['age'] > overdue_threshold_days]
    
    return overdue_issues.to_dict('records')
    
def analyze_tagged_issues(df: pd.DataFrame, target_tags: list[str]) -> list[dict]:
    """
    分析带特定标签的问题
    :param df: 输入的DataFrame
    :param target_tags: 目标标签列表
    :return: 带特定标签的问题列表
    """
    if not target_tags or 'tags' not in df.columns:
        return []
    
    # 使用正则表达式匹配包含任何一个目标标签的问题
    # na=False 表示 NaN 值不匹配
    tagged_issues = df[df['tags'].str.contains('|'.join(target_tags), na=False)]
    
    return tagged_issues.to_dict('records')

def analyze(df: pd.DataFrame, history_df: pd.DataFrame, config: Config) -> dict:
    """
    总分析函数，编排所有分析任务
    :param df: 输入的DataFrame
    :param history_df: 历史数据DataFrame
    :param config: 配置对象
    :return: 包含所有分析结果的字典
    """
    # --- 数据预处理：计算年龄 ---
    # 确保 'created_date' 是 datetime 类型
    df['created_date'] = pd.to_datetime(df['created_date'])
    # 计算问题年龄 (创建至今的天数)
    now_naive = pd.Timestamp.now().tz_localize(None)
    df['age'] = (now_naive - df['created_date'].dt.tz_localize(None)).dt.days

    # 从配置对象中直接获取分析参数
    overdue_threshold = config.overdue_threshold_days
    target_tags = config.target_tags
    a_priority_name = config.a_priority_name

    # 筛选出A类问题
    a_priority_issues = df[df['priority'] == a_priority_name]

    analysis_results = {
        "overall_metrics": analyze_overall_metrics(df),
        "priority_distribution": analyze_priority_distribution(df),
        "status_distribution": analyze_status_distribution(df),
        "module_distribution": analyze_module_distribution(df),
        "overdue_issues": analyze_overdue_issues(df, overdue_threshold),
        "tagged_issues": analyze_tagged_issues(df, target_tags),
        "a_priority_issues": a_priority_issues.to_dict('records') # 新增A类问题列表
    }

    # --- 新增高级分析 ---
    kpis = calculate_kpis(df, history_df, config)
    analysis_results['kpis'] = kpis
    
    generated_text = generate_analysis_and_recommendations(kpis)
    analysis_results['generated_text'] = generated_text
    
    return analysis_results 