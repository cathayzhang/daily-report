"""
核心分析模块
"""
import pandas as pd
from config_loader import Config
from datetime import datetime, timedelta, date
import numpy as np

def calculate_kpis(df: pd.DataFrame, history_df: pd.DataFrame, config: Config) -> dict:
    """
    计算报告所需的核心KPI指标。
    """
    kpis = {}
    today = datetime.now().date()
    
    # 从统一的计划配置中找到DI收敛计划
    di_plan = next((p for p in config.burnup_plans if p['metric'] == 'di_value'), None)
    
    convergence_deviation = None
    if di_plan:
        plan_start_date = pd.to_datetime(di_plan['start_date']).date()
        plan_end_date = pd.to_datetime(di_plan['end_date']).date()
        today = date.today()

        # 仅在当前日期处于计划周期内时才计算收敛偏差
        if plan_start_date <= today <= plan_end_date:
            total_days = (plan_end_date - plan_start_date).days
            elapsed_days = (today - plan_start_date).days
            
            start_di = di_plan['start_count']
            target_di = di_plan['end_count']
            
            # 计算理想DI值
            ideal_di = start_di - (start_di - target_di) * (elapsed_days / total_days)
            
            # 获取当天的实际DI值
            class_counts = get_class_counts(df, config)
            di_weights = config.di_weights
            current_di = (class_counts.get('A级', 0) * di_weights.get('a', 10) +
                          class_counts.get('B级', 0) * di_weights.get('b', 3) +
                          class_counts.get('C级', 0) * di_weights.get('c', 1))
            
            # 收敛偏差 = 理想值 - 实际值 (正数表示领先，负数表示落后)
            convergence_deviation = ideal_di - current_di

    # 获取A、B、C类问题的总数
    class_counts = get_class_counts(df, config)
    total_a_issues = class_counts.get('A级', 0)
    kpis['total_issues'] = len(df)
    kpis['class_counts'] = class_counts
    
    planned_today_di = np.nan
    actual_today_di = class_counts.get('A级', 0) * config.di_weights.get('a', 10) + \
                      class_counts.get('B级', 0) * config.di_weights.get('b', 3) + \
                      class_counts.get('C级', 0) * config.di_weights.get('c', 1)

    if config.burnup_plans:
        # 假设第一个计划可用于此处的某种通用计算，或者需要特定逻辑来选择计划
        # 注意：这里的逻辑可能需要根据实际需求进行审查和调整
        a_plan = next((p for p in config.burnup_plans if p['metric'] == 'A级'), None)
        if a_plan:
            plan_start_date = pd.to_datetime(a_plan['start_date']).date()
            plan_end_date = pd.to_datetime(a_plan['end_date']).date()
            if plan_start_date <= today <= plan_end_date:
                days_in_plan = (plan_end_date - plan_start_date).days
                days_from_start = (today - plan_start_date).days
                
                if days_in_plan > 0:
                    # 计算当天理想A,B,C值
                    b_plan = next((p for p in config.burnup_plans if p['metric'] == 'B级'), None)
                    c_plan = next((p for p in config.burnup_plans if p['metric'] == 'C级'), None)

                    ideal_a = a_plan['start_count'] - (a_plan['start_count'] - a_plan['end_count']) * (days_from_start / days_in_plan)
                    ideal_b = b_plan['start_count'] - (b_plan['start_count'] - b_plan['end_count']) * (days_from_start / days_in_plan) if b_plan else 0
                    ideal_c = c_plan['start_count'] - (c_plan['start_count'] - c_plan['end_count']) * (days_from_start / days_in_plan) if c_plan else 0
                    
                    # 计算当天理想DI值
                    planned_today_di = ideal_a * config.di_weights.get('a', 10) + \
                                       ideal_b * config.di_weights.get('b', 3) + \
                                       ideal_c * config.di_weights.get('c', 1)

    if not pd.isna(planned_today_di):
        kpis['convergence_deviation'] = round(convergence_deviation) if convergence_deviation is not None else None
        kpis['planned_today_count'] = round(planned_today_di) # 沿用旧key, 但值为DI
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
    kpis['a_priority_percentage'] = round((kpis['a_blocker_count'] / len(df)) * 100) if len(df) > 0 else 0

    # 计算DI分数
    # 这个DI值应该和 actual_today_di 一致
    kpis['di_score'] = round(actual_today_di)

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
    
def get_high_risk_issues(df: pd.DataFrame, rules: list) -> pd.DataFrame:
    """
    根据一组动态规则筛选高风险问题。

    Args:
        df (pd.DataFrame): 包含所有问题的DataFrame。
        rules (list): 从config加载的规则字典列表。

    Returns:
        pd.DataFrame: 筛选出的高风险问题。
    """
    if not rules:
        return pd.DataFrame()

    # 初始化一个全为 True 的掩码，作为所有条件的交集基础
    final_mask = pd.Series(True, index=df.index)

    for rule in rules:
        column = rule['column']
        operator = rule['operator']
        value = rule['value']

        if column not in df.columns:
            print(f"警告：规则中指定的列 '{column}' 不存在于数据中，跳过此规则。")
            continue

        try:
            # 根据操作符构建临时掩码
            if operator == 'equals':
                mask = (df[column].astype(str) == str(value))
            elif operator == 'not_equals':
                mask = (df[column].astype(str) != str(value))
            elif operator == 'contains':
                # 确保为字符串类型，并处理NaN值
                mask = df[column].astype(str).str.contains(str(value), na=False)
            elif operator == 'in':
                mask = df[column].isin(value)
            elif operator == 'not_in':
                mask = ~df[column].isin(value)
            elif operator == 'greater_than':
                # 使用 pd.to_numeric 并将错误转换为NaN，然后用False填充NaN
                mask = (pd.to_numeric(df[column], errors='coerce') > float(value)).fillna(False)
            elif operator == 'less_than':
                mask = (pd.to_numeric(df[column], errors='coerce') < float(value)).fillna(False)
            else:
                print(f"警告：未知的操作符 '{operator}'，跳过规则。")
                continue
            
            # 将当前规则的掩码与总掩码进行"与"运算
            final_mask &= mask
        except Exception as e:
            print(f"警告：处理规则 {rule} 时发生错误，跳过此规则。错误: {e}")
            continue

    return df[final_mask]

def analyze_tagged_issues(df: pd.DataFrame, config: Config) -> list[dict]:
    if not config.target_tags or 'tags' not in df.columns: return []
    tagged_issues = df[df['tags'].str.contains('|'.join(config.target_tags), na=False)]
    
    # Add jira_url if base url and key exist
    if config.jira_base_url and 'key' in tagged_issues.columns:
        tagged_issues['jira_url'] = tagged_issues['key'].apply(lambda k: f"{config.jira_base_url.rstrip('/')}/{k}")
        
    return tagged_issues.to_dict('records')

def get_class_counts(df: pd.DataFrame, config: 'Config') -> dict:
    """根据配置计算A、B、C类问题的数量。"""
    return {
        'A级': sum(df['priority'].isin(config.class_a_priorities)),
        'B级': sum(df['priority'].isin(config.class_b_priorities)),
        'C级': sum(df['priority'].isin(config.class_c_priorities)),
    }

def analyze(df: pd.DataFrame, history_df: pd.DataFrame, config: Config) -> dict:
    df['created_date'] = pd.to_datetime(df['created_date'])
    now_naive = pd.Timestamp.now().tz_localize(None)
    df['age'] = (now_naive - df['created_date'].dt.tz_localize(None)).dt.days

    a_priority_name = config.a_priority_name
    
    # Prepare a_priority_issues dataframe
    a_priority_df = df[df['priority'] == a_priority_name].copy()
    if config.jira_base_url and 'key' in a_priority_df.columns:
        a_priority_df['jira_url'] = a_priority_df['key'].apply(lambda k: f"{config.jira_base_url.rstrip('/')}/{k}")

    # V3.0 P3 新增：获取动态高风险问题
    high_risk_df = get_high_risk_issues(df, config.high_risk_rules).copy()
    if config.jira_base_url and 'key' in high_risk_df.columns:
        high_risk_df['jira_url'] = high_risk_df['key'].apply(lambda k: f"{config.jira_base_url.rstrip('/')}/{k}")

    analysis_results = {
        "overall_metrics": analyze_overall_metrics(df),
        "priority_distribution": analyze_priority_distribution(df),
        "status_distribution": analyze_status_distribution(df),
        "module_distribution": analyze_module_distribution(df),
        "overdue_issues": analyze_overdue_issues(df, config),
        "tagged_issues": analyze_tagged_issues(df, config),
        "a_priority_issues": a_priority_df.to_dict('records'),
        "high_risk_issues": high_risk_df.to_dict('records')
    }

    kpis = calculate_kpis(df, history_df, config)
    analysis_results['kpis'] = kpis
    analysis_results['generated_text_html'] = generate_detailed_analysis_html(kpis)
    return analysis_results 