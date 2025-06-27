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
        kpis['convergence_deviation'] = None
        kpis['planned_today_count'] = None

    # 2. A类问题7日变化
    a_priority_name = config.a_priority_name
    current_a_issues = df[df['priority'] == a_priority_name].shape[0]
    kpis['current_a_issues_count'] = current_a_issues
    
    # 只有在有历史数据时才计算7日变化
    if not history_df.empty and 'date' in history_df.columns and a_priority_name in history_df.columns:
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
    else:
        kpis['a_issues_7_day_change'] = current_a_issues
        kpis['a_issues_7_day_change_has_history'] = False

    # 3. 风险最集中模块
    risk_priorities = config.risk_module_priorities
    risk_df = df[df['priority'].isin(risk_priorities)]
    if not risk_df.empty and 'module' in risk_df.columns:
        riskiest_module_series = risk_df['module'].value_counts()
        if not riskiest_module_series.empty:
            total_risk_issues = risk_df.shape[0]

            # Top 1 for summary
            riskiest_module_name = riskiest_module_series.index[0]
            riskiest_module_count = int(riskiest_module_series.iloc[0])
            riskiest_module_percentage = (riskiest_module_count / total_risk_issues) * 100 if total_risk_issues > 0 else 0
            kpis['riskiest_module'] = {
                'name': riskiest_module_name,
                'count': riskiest_module_count,
                'percentage_of_total_risk': round(riskiest_module_percentage)
            }

            # Top 3 for chart
            top_3_modules = riskiest_module_series.head(3)
            kpis['top_3_riskiest_modules'] = []
            for module, count in top_3_modules.items():
                percentage = (count / total_risk_issues) * 100 if total_risk_issues > 0 else 0
                kpis['top_3_riskiest_modules'].append({
                    'name': module,
                    'count': int(count),
                    'percentage': round(percentage)
                })
        else:
            kpis['riskiest_module'] = None
            kpis['top_3_riskiest_modules'] = []
    else:
        kpis['riskiest_module'] = None
        kpis['top_3_riskiest_modules'] = []
        
    kpis['a_blocker_count'] = df[df['priority'] == config.a_priority_name].shape[0]
    priority_counts = df['priority'].value_counts()
    kpis['priority_distribution_summary'] = f"A:{priority_counts.get(config.a_priority_name, 0)} / B:{priority_counts.get('Critical', 0)} / C:{priority_counts.get('High', 0)+priority_counts.get('Medium', 0)}"
    kpis['a_priority_percentage'] = round((kpis['a_blocker_count'] / total_issues) * 100) if total_issues > 0 else 0

    # 计算A/B/C类问题数量
    class_counts = {
        'A': sum(priority_counts.get(p, 0) for p in config.class_priorities.get('A', [])),
        'B': sum(priority_counts.get(p, 0) for p in config.class_priorities.get('B', [])),
        'C': sum(priority_counts.get(p, 0) for p in config.class_priorities.get('C', [])),
    }
    kpis['class_counts'] = class_counts

    # 计算DI分数 (使用新的分类方式)
    d_count = priority_counts.get('Low', 0) # 'Low' 通常不计入C类，单独处理
    di_score = round(class_counts['A'] * 10 + class_counts['B'] * 3 + class_counts['C'] * 1 + d_count * 0.1)
    kpis['di_score'] = di_score

    return kpis

def generate_executive_summary_html(kpis: dict) -> str:
    summary_html = "<h3>一、总体摘要</h3>"
    core_conclusion_parts = []
    
    if kpis.get('a_blocker_count', 0) > 0:
        health_status = '🔴 (危险)'
        core_conclusion_parts.append("项目当前面临严峻的质量与发布风险。")
        if kpis.get('a_issues_7_day_change', 0) > 0:
            core_conclusion_parts.append(f"<strong>A类问题在过去7天内激增{kpis['a_issues_7_day_change']}个</strong>。")
        
        riskiest_module_name = kpis.get('riskiest_module', {}).get('name', '关键')
        core_conclusion_parts.append(f"风险高度集中在 <strong>`{riskiest_module_name}`</strong> 模块。")
        core_conclusion_parts.append(f"当前的首要任务是立刻成立专项小组，集中资源主攻这{kpis['a_blocker_count']}个A类Blocker，并对`{riskiest_module_name}`模块进行深度技术排查。")
    else:
        health_status = '🟢 (健康)'
        core_conclusion_parts.append("项目当前状态稳定，无紧急发布风险。")

    summary_html += f"<p><strong>总体健康度评估:</strong> {health_status}</p>"
    summary_html += f"<p><strong>核心结论:</strong> {' '.join(core_conclusion_parts)}</p>"
    summary_html += "<hr>"
    return summary_html

def generate_detailed_analysis_html(kpis: dict) -> str:
    if not kpis: return ""

    summary_html = generate_executive_summary_html(kpis)

    trend_analysis_html = "<h3>三、趋势分析</h3>"
    analysis_points = []
    if kpis.get('a_issues_7_day_change') == kpis.get('a_blocker_count', -1) and kpis.get('a_issues_7_day_change', 0) > 0:
        a_change = kpis['a_issues_7_day_change']
        a_blockers = kpis['a_blocker_count']
        text = (
            "<h4>【风险聚焦：高优问题已全部转化为Blocker】</h4>"
            f'<p><strong>分析:</strong> 本周"A类问题7日净增长"(`+{a_change}`)与"A类Blocker数量"(`{a_blockers}`)完全一致，'
            "说明短期内爆发的高优问题100%转化为了发布阻断点。</p>"
        )
        analysis_points.append(text)

    if kpis.get('riskiest_module'):
        module_name = kpis['riskiest_module']['name']
        text = (
            "<h4>【风险源头定位】</h4>"
            f"<p><strong>分析:</strong> `{module_name}` 是风险最集中模块。可推断该模块是Blocker问题主要来源，应立刻调查其近期变更。</p>"
        )
        analysis_points.append(text)
    trend_analysis_html += "".join(analysis_points)

    risk_alerts_html = "<h3>四、首要风险预警</h3><ol>"
    risk_items = []
    if kpis.get('a_blocker_count', 0) > 0:
        a_blockers = kpis['a_blocker_count']
        risk_items.append(f"<li><strong>[高] 版本发布完全受阻:</strong> 存在 `{a_blockers}` 个A类Blocker，发布计划已停滞。</li>")
    if kpis.get('a_issues_7_day_change', 0) > 0:
        a_change = kpis['a_issues_7_day_change']
        risk_items.append(f"<li><strong>[高] 项目质量失控:</strong> A类问题7日净增 `+{a_change}`，问题修复速度远慢于产生速度。</li>")
    risk_alerts_html += "".join(risk_items) + "</ol>"

    suggestions_html = (
        "<h3>五、建议</h3>"
        '<p>建议在日报中增加对"每周完成的问题数"、"单个问题的平均解决时长"等效能指标的统计，以便更全面地掌握项目健康度。</p>'
    )
    return summary_html + trend_analysis_html + risk_alerts_html + suggestions_html

def analyze_overall_metrics(df: pd.DataFrame) -> dict:
    total_count = len(df)
    resolved_count = df[df['status'] == '已完成'].shape[0]
    unresolved_count = total_count - resolved_count
    return {"total_issues": total_count, "resolved_issues": resolved_count, "unresolved_issues": unresolved_count}

def analyze_priority_distribution(df: pd.DataFrame) -> dict:
    return df['priority'].value_counts().to_dict()

def analyze_status_distribution(df: pd.DataFrame) -> dict:
    return df['status'].value_counts().to_dict()

def analyze_module_distribution(df: pd.DataFrame) -> dict:
    if 'module' not in df.columns: return {}
    return df['module'].value_counts().to_dict()

def analyze_overdue_issues(df: pd.DataFrame, config: Config) -> list[dict]:
    unresolved = df[df['status'] != '已完成'].copy()
    overdue_issues = unresolved[unresolved['age'] > config.overdue_threshold_days]
    
    # Add jira_url if base url and key exist
    if config.jira_base_url and 'key' in overdue_issues.columns:
        overdue_issues['jira_url'] = overdue_issues['key'].apply(lambda k: f"{config.jira_base_url.rstrip('/')}/{k}")
        
    return overdue_issues.to_dict('records')
    
def analyze_tagged_issues(df: pd.DataFrame, config: Config) -> list[dict]:
    if not config.target_tags or 'tags' not in df.columns: return []
    tagged_issues = df[df['tags'].str.contains('|'.join(config.target_tags), na=False)]
    
    # Add jira_url if base url and key exist
    if config.jira_base_url and 'key' in tagged_issues.columns:
        tagged_issues['jira_url'] = tagged_issues['key'].apply(lambda k: f"{config.jira_base_url.rstrip('/')}/{k}")
        
    return tagged_issues.to_dict('records')

def analyze(df: pd.DataFrame, history_df: pd.DataFrame, config: Config) -> dict:
    df['created_date'] = pd.to_datetime(df['created_date'])
    now_naive = pd.Timestamp.now().tz_localize(None)
    df['age'] = (now_naive - df['created_date'].dt.tz_localize(None)).dt.days

    a_priority_name = config.a_priority_name
    
    # Prepare a_priority_issues dataframe
    a_priority_df = df[df['priority'] == a_priority_name].copy()
    if config.jira_base_url and 'key' in a_priority_df.columns:
        a_priority_df['jira_url'] = a_priority_df['key'].apply(lambda k: f"{config.jira_base_url.rstrip('/')}/{k}")

    analysis_results = {
        "overall_metrics": analyze_overall_metrics(df),
        "priority_distribution": analyze_priority_distribution(df),
        "status_distribution": analyze_status_distribution(df),
        "module_distribution": analyze_module_distribution(df),
        "overdue_issues": analyze_overdue_issues(df, config),
        "tagged_issues": analyze_tagged_issues(df, config),
        "a_priority_issues": a_priority_df.to_dict('records')
    }

    kpis = calculate_kpis(df, history_df, config)
    analysis_results['kpis'] = kpis
    analysis_results['generated_text_html'] = generate_detailed_analysis_html(kpis)
    return analysis_results 