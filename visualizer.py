import os
import pandas as pd
import json
from datetime import datetime
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np

# 设置默认主题
pio.templates.default = "plotly_white"

def _setup_matplotlib_for_chinese():
    """
    配置 Matplotlib 以支持中文显示。
    会尝试在系统中寻找常见的中文字体。
    """
    # 常见中文字体列表，PingFang SC (macOS), Microsoft YaHei (Windows), WenQuanYi (Linux)
    font_list = ["PingFang SC", "SimHei", "Heiti TC", "Microsoft YaHei", "WenQuanYi Micro Hei", "Arial Unicode MS"]
    
    for font in font_list:
        try:
            plt.rcParams['font.sans-serif'] = [font]
            # 测试字体是否真的可用
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.set_title("测试")
            fig.canvas.draw()
            plt.close(fig)
            print(f"成功加载中文字体: {font}")
            break
        except Exception:
            continue
    else:
        print("警告：未找到可用的中文字体，图表中的中文可能会显示为方框。")
        print("请尝试安装 'SimHei', 'Microsoft YaHei' 或 'WenQuanYi Micro Hei' 等字体。")

    # 解决负号显示问题
    plt.rcParams['axes.unicode_minus'] = False


def get_trend_chart_data(history_df: pd.DataFrame) -> str:
    """
    根据历史数据准备用于 Chart.js 的趋势图数据。

    Args:
        history_df: 包含历史数据的 DataFrame。

    Returns:
        一个包含图表配置和数据的 JSON 字符串。
    """
    if history_df is None or history_df.empty:
        return None

    history_df['date'] = pd.to_datetime(history_df['date'])
    history_df = history_df.sort_values('date')

    chart_data = {
        "type": "line",
        "data": {
            "labels": history_df['date'].dt.strftime('%Y-%m-%d').tolist(),
            "datasets": [
                {
                    "label": "总问题数",
                    "data": history_df['total_issues'].tolist(),
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    "fill": True,
                    "tension": 0.1
                },
                {
                    "label": "已解决数",
                    "data": history_df['resolved_issues'].tolist(),
                    "borderColor": "rgba(75, 192, 192, 1)",
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "fill": True,
                    "tension": 0.1
                }
            ]
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {
                    "display": True,
                    "text": "问题数量趋势分析"
                }
            }
        }
    }
    return json.dumps(chart_data)


def get_module_distribution_chart_data(module_data: dict) -> str:
    """
    根据模块数据准备用于 Chart.js 的分布图数据。

    Args:
        module_data: 包含模块及其问题计数的字典。

    Returns:
        一个包含图表配置和数据的 JSON 字符串。
    """
    if not module_data:
        return None

    module_series = pd.Series(module_data).sort_values(ascending=False)
    
    background_colors = [
        'rgba(255, 99, 132, 0.8)', 'rgba(54, 162, 235, 0.8)',
        'rgba(255, 206, 86, 0.8)', 'rgba(75, 192, 192, 0.8)',
        'rgba(153, 102, 255, 0.8)', 'rgba(255, 159, 64, 0.8)',
        'rgba(199, 199, 199, 0.8)', 'rgba(83, 102, 255, 0.8)'
    ]
    border_colors = [
        'rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)', 'rgba(75, 192, 192, 1)',
        'rgba(153, 102, 255, 1)', 'rgba(255, 159, 64, 1)',
        'rgba(199, 199, 199, 1)', 'rgba(83, 102, 255, 1)'
    ]


    chart_data = {
        "type": "doughnut",
        "data": {
            "labels": module_series.index.tolist(),
            "datasets": [{
                "label": "问题数量",
                "data": module_series.values.tolist(),
                "backgroundColor": background_colors,
                "borderColor": border_colors,
                "borderWidth": 1
            }]
        },
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {
                    "position": 'top',
                },
                "title": {
                    "display": True,
                    "text": '各模块问题分布情况'
                }
            }
        }
    }
    return json.dumps(chart_data)


def generate_all_charts(analysis_data: dict, history_df: pd.DataFrame, config: 'Config') -> dict:
    """
    生成所有需要的 Plotly 图表 HTML。

    Args:
        analysis_data: 来自 analyzer 模块的当日分析结果。
        history_df: 包含历史数据的 DataFrame。
        config: 加载的配置对象 (Config 类的实例)。

    Returns:
        一个包含各类图表HTML字符串的字典。
    """
    charts_html = {}

    # 1. 生成趋势图 (A类问题趋势)
    if history_df is not None and not history_df.empty:
        a_priority_name = config.a_priority_name
        trend_html = _get_trend_chart_html(history_df.copy(), a_priority_name)
        if trend_html:
            charts_html['trend_chart_html'] = trend_html

    # 2. 生成模块分布图
    module_data = analysis_data.get('module_distribution')
    if module_data:
        module_dist_html = _get_module_distribution_chart_html(module_data)
        if module_dist_html:
            charts_html['module_dist_html'] = module_dist_html

    # 3. 生成优先级分布图
    priority_data = analysis_data.get('priority_distribution')
    if priority_data:
        priority_dist_html = _get_priority_distribution_chart_html(priority_data)
        if priority_dist_html:
            charts_html['priority_dist_html'] = priority_dist_html

    # 4. 生成Top 3风险模块图
    top_3_risk_modules_data = analysis_data.get('kpis', {}).get('top_3_riskiest_modules')
    if top_3_risk_modules_data:
        risk_module_chart_html = _get_risk_module_bar_chart_html(top_3_risk_modules_data)
        if risk_module_chart_html:
            charts_html['top_3_riskiest_modules_html'] = risk_module_chart_html
    
    # 5. 生成所有燃尽图 (DI, A级, B级等)
    if history_df is not None and not history_df.empty and config.burnup_plans:
        # 安全检查：确保日期列名为 'report_date'
        if 'report_date' not in history_df.columns and 'date' in history_df.columns:
            history_df = history_df.rename(columns={'date': 'report_date'})

        history_df['report_date'] = pd.to_datetime(history_df['report_date'])
        
        # 为DI燃尽图找到对应的计划
        di_plan = next((p for p in config.burnup_plans if p['metric'] == 'di_value'), None)
        if di_plan:
            plan_start = pd.to_datetime(di_plan['start_date'])
            plan_end = pd.to_datetime(di_plan['end_date'])
            filtered_df = history_df[(history_df['report_date'] >= plan_start) & (history_df['report_date'] <= plan_end)].copy()
            
            di_chart_html = _create_di_burndown_chart_from_plan(filtered_df, di_plan, config.di_weights)
            if di_chart_html:
                charts_html['di_burnup_chart_html'] = di_chart_html

        # 为ABC类问题燃尽图找到对应的计划
        abc_plans = [p for p in config.burnup_plans if p['metric'] in ['A级', 'B级', 'C级']]
        if abc_plans:
            plan_start = min(pd.to_datetime(p['start_date']) for p in abc_plans)
            plan_end = max(pd.to_datetime(p['end_date']) for p in abc_plans)
            filtered_df = history_df[(history_df['report_date'] >= plan_start) & (history_df['report_date'] <= plan_end)].copy()
            
            # 旧的燃尽图函数需要 'date' 列
            filtered_df_for_old_chart = filtered_df.rename(columns={'report_date': 'date'})
            
            abc_chart_html = _get_burnup_chart_html(
                filtered_df_for_old_chart,
                abc_plans,
                "按类问题收敛燃尽图",
                "剩余问题数"
            )
            if abc_chart_html:
                charts_html['abc_burnup_chart_html'] = abc_chart_html
                
    return charts_html

def _get_trend_chart_html(history_df: pd.DataFrame, a_priority_name: str) -> str:
    """
    Generate Plotly trend chart HTML from history data.
    """
    if history_df is None or history_df.empty or 'total' not in history_df.columns:
        return None

    history_df['date'] = pd.to_datetime(history_df['date'])
    history_df = history_df.sort_values('date')

    fig = go.Figure()

    # 总问题趋势
    fig.add_trace(go.Scatter(
        x=history_df['date'],
        y=history_df['total'],
        mode='lines+markers',
        name='Total Issues',
        line=dict(color='rgba(54, 162, 235, 1)'),
        fill='tozeroy',
        fillcolor='rgba(54, 162, 235, 0.2)',
    ))

    # A类问题趋势
    if a_priority_name in history_df.columns:
        fig.add_trace(go.Scatter(
            x=history_df['date'],
            y=history_df[a_priority_name],
            mode='lines+markers',
            name=f'{a_priority_name} Issues',
            line=dict(color='rgba(255, 99, 132, 1)'),
            fill='tozeroy',
            fillcolor='rgba(255, 99, 132, 0.2)',
        ))

    if 'resolved' in history_df.columns:
        fig.add_trace(go.Scatter(
            x=history_df['date'],
            y=history_df['resolved'],
            mode='lines+markers',
            name='Resolved Issues',
            line=dict(color='rgba(75, 192, 192, 1)'),
            fill='tozeroy',
            fillcolor='rgba(75, 192, 192, 0.2)',
        ))

    fig.update_layout(
        title_text="问题数量总体趋势",
        xaxis_title="日期",
        yaxis_title="问题数量",
        legend_title="指标",
        hovermode="x unified"
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


def _get_module_distribution_chart_html(module_data: dict) -> str:
    """
    Generate Plotly module distribution chart HTML. (Horizontal Bar Chart)
    """
    if not module_data:
        return None

    module_series = pd.Series(module_data).sort_values(ascending=True)
    
    fig = go.Figure(go.Bar(
        y=module_series.index,
        x=module_series.values,
        orientation='h',
        marker_color='rgba(54, 162, 235, 0.8)'
    ))
    
    fig.update_layout(
        title_text=None,
        xaxis_title=None,
        yaxis_title=None,
        height=260,
        margin=dict(l=80, r=20, t=10, b=20)
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

def _get_priority_distribution_chart_html(priority_data: dict) -> str:
    """
    Generate Plotly priority distribution pie chart HTML.
    """
    if not priority_data:
        return None

    priority_series = pd.Series(priority_data).sort_index()

    fig = go.Figure(data=[go.Pie(
        labels=priority_series.index,
        values=priority_series.values,
        hole=.4,
        hoverinfo='label+percent+value',
        textinfo='percent'
    )])
    
    fig.update_layout(
        title_text=None,
        height=260,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=10, b=40)
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


def _get_burnup_chart_html(history_df: pd.DataFrame, plans: list, title: str, yaxis_title: str) -> str:
    """
    根据给定的计划和历史数据，生成燃尽图。
    """
    fig = go.Figure()
    
    # 提取所有计划的起止日期，以确定图表X轴范围
    all_start_dates = [pd.to_datetime(p['start_date']) for p in plans]
    all_end_dates = [pd.to_datetime(p['end_date']) for p in plans]
    chart_start_date = min(all_start_dates)
    chart_end_date = max(all_end_dates)

    # 绘制理想线
    for plan in plans:
        start_date = pd.to_datetime(plan['start_date'])
        end_date = pd.to_datetime(plan['end_date'])
        start_count = plan['start_count']
        end_count = plan['end_count']
        metric = plan.get('metric', 'value')
        
        fig.add_trace(go.Scatter(
            x=[start_date, end_date],
            y=[start_count, end_count],
            mode='lines',
            name=f"理想线 - {plan['name']}",
            line=dict(dash='dash')
        ))

    # 准备历史数据
    history_df['date'] = pd.to_datetime(history_df['date'])
    history_df = history_df[
        (history_df['date'] >= chart_start_date) & 
        (history_df['date'] <= chart_end_date)
    ]

    # 绘制实际线
    for plan in plans:
        metric_col = plan.get('metric')
        if metric_col and metric_col in history_df.columns:
            fig.add_trace(go.Scatter(
                x=history_df['date'],
                y=history_df[metric_col],
                mode='lines+markers',
                name=f"实际 - {plan['name']}"
            ))

    fig.update_layout(
        title=title,
        xaxis_title='日期',
        yaxis_title=yaxis_title,
        legend_title='图例'
    )
    
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

def _get_risk_module_bar_chart_html(top_3_modules: list) -> str:
    """
    为Top 3风险模块生成水平条形图。
    """
    if not top_3_modules:
        return ""

    module_names = [m['name'] for m in top_3_modules]
    module_counts = [m['count'] for m in top_3_modules]
    
    # Invert order for horizontal bar chart
    module_names.reverse()
    module_counts.reverse()
    
    fig = go.Figure(go.Bar(
        y=module_names,
        x=module_counts,
        orientation='h',
        text=module_counts,
        textposition='auto',
        marker_color='#EF553B'
    ))
    
    fig.update_layout(
        title_text="Top 3 风险来源模块",
        xaxis_title="高风险问题数",
        yaxis_title="模块名称",
        height=300,
        margin=dict(l=150, r=20, t=40, b=40)
    )
    
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

def _create_di_burndown_chart_from_plan(history_df: pd.DataFrame, plan_data: dict, di_weights: dict) -> str:
    """
    根据DI收敛计划和历史数据生成DI燃尽图。
    """
    start_date = pd.to_datetime(plan_data['start_date'])
    end_date = pd.to_datetime(plan_data['end_date'])
    start_di = plan_data['start_count']
    end_di = plan_data['end_count']
    
    # 检查历史数据是否为空
    if history_df.empty:
        # 如果没有历史数据，仍然可以绘制理想线
        actual_dates = pd.to_datetime([])
        actual_di = []
    else:
        actual_dates = history_df['report_date']
        actual_di = history_df['di_value']

    # 创建理想DI值的线性插值
    ideal_dates = pd.to_datetime([start_date, end_date])
    ideal_di = [start_di, end_di]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ideal_dates,
        y=ideal_di,
        mode='lines',
        name='理想DI值',
        line=dict(color='rgba(54, 162, 235, 1)', dash='dash'),
    ))

    fig.add_trace(go.Scatter(
        x=actual_dates,
        y=actual_di,
        mode='lines+markers',
        name='实际DI值',
        line=dict(color='rgba(255, 99, 132, 1)'),
    ))

    fig.update_layout(
        title_text="DI值收敛燃尽图",
        xaxis_title="日期",
        yaxis_title="DI值 (越低越好)",
        legend_title="指标",
        hovermode="x unified"
    )
    
    return pio.to_html(fig, full_html=False, include_plotlyjs=False) 