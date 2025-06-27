import os
import pandas as pd
import json
from datetime import datetime
import plotly.graph_objects as go
import plotly.io as pio

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


def generate_all_charts(analysis_data: dict, history_df: pd.DataFrame, config) -> dict:
    """
    生成所有需要的 Plotly 图表 HTML。

    Args:
        analysis_data: 来自 analyzer 模块的当日分析结果。
        history_df: 包含历史数据的 DataFrame。
        config: 加载的配置对象 (包含收敛计划)。

    Returns:
        一个包含各类图表HTML字符串的字典。
    """
    charts_html = {}

    # 生成趋势图
    if history_df is not None and not history_df.empty:
        # 传递A类问题的列名
        a_priority_name = config.a_priority_name
        trend_html = _get_trend_chart_html(history_df.copy(), a_priority_name)
        if trend_html:
            charts_html['trend_chart_html'] = trend_html
            print("趋势图HTML已生成。")

    # 生成模块分布图
    module_data = analysis_data.get('module_distribution')
    if module_data:
        module_dist_html = _get_module_distribution_chart_html(module_data)
        if module_dist_html:
            charts_html['module_dist_html'] = module_dist_html
            print("模块分布图HTML已生成。")

    # --- 新增: 生成优先级分布图 ---
    priority_data = analysis_data.get('priority_distribution')
    if priority_data:
        priority_dist_html = _get_priority_distribution_chart_html(priority_data)
        if priority_dist_html:
            charts_html['priority_dist_html'] = priority_dist_html
            print("优先级分布图HTML已生成。")

    # --- 新增: 生成Top 3风险模块图 ---
    top_3_risk_modules_data = analysis_data.get('kpis', {}).get('top_3_riskiest_modules')
    if top_3_risk_modules_data:
        risk_module_chart_html = _get_risk_module_bar_chart_html(top_3_risk_modules_data)
        if risk_module_chart_html:
            charts_html['top_3_riskiest_modules_html'] = risk_module_chart_html
            print("Top 3风险模块图HTML已生成。")
    
    # 生成燃尽图
    if hasattr(config, 'convergence_plan') and history_df is not None:
        burnup_html = _get_burnup_chart_html(history_df.copy(), config.convergence_plan)
        if burnup_html:
            charts_html['burnup_chart_html'] = burnup_html
            print("燃尽图HTML已生成。")
            
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
        title_text="",
        xaxis_title="",
        yaxis_title="",
        height=160,
        margin=dict(t=20, l=40, r=20, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


def _get_module_distribution_chart_html(module_data: dict) -> str:
    """
    Generate Plotly horizontal bar chart HTML from module data.
    """
    if not module_data:
        return None

    module_series = pd.Series(module_data).sort_values(ascending=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=module_series.index,
        x=module_series.values,
        text=module_series.values,
        textposition='auto',
        orientation='h',
        marker_color='rgba(54, 162, 235, 0.8)',
        marker_line_color='rgba(54, 162, 235, 1)',
        marker_line_width=1.5,
    ))

    fig.update_layout(
        title_text="",
        xaxis_title="问题数量",
        yaxis_title="模块",
        height=240,
        margin=dict(l=100, r=20, t=20, b=40),
        xaxis=dict(showgrid=True, zeroline=True, showticklabels=True),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=True),
        showlegend=False
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

def _get_priority_distribution_chart_html(priority_data: dict) -> str:
    """
    Generate Plotly pie chart HTML from priority data.
    """
    if not priority_data:
        return None

    priority_series = pd.Series(priority_data).sort_values(ascending=False)

    fig = go.Figure(data=[go.Pie(
        labels=priority_series.index,
        values=priority_series.values,
        hole=.3,
        hoverinfo='label+percent',
        textinfo='label+percent'
    )])

    fig.update_layout(
        title_text="",
        margin=dict(t=20, l=20, r=20, b=20),
        height=240,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )

    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

def _get_burnup_chart_html(history_df: pd.DataFrame, plan: dict) -> str:
    """
    Generate project convergence burn-up chart HTML.
    """
    if history_df is None or history_df.empty or not plan or 'total' not in history_df.columns:
        return None

    history_df['date'] = pd.to_datetime(history_df['date'])
    history_df = history_df.sort_values('date')

    try:
        plan_start_date = pd.to_datetime(plan['start_date'])
        plan_end_date = pd.to_datetime(plan['end_date'])
        start_count = int(plan['start_count'])
        end_count = int(plan['end_count'])
    except (KeyError, TypeError):
        return None

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=[plan_start_date, plan_end_date],
        y=[start_count, end_count],
        mode='lines+markers',
        name=f"Plan: {plan.get('name', 'Convergence Goal')}",
        line=dict(color='gray', dash='dash')
    ))

    actual_data = history_df[history_df['date'].between(plan_start_date, plan_end_date)]
    if not actual_data.empty:
        fig.add_trace(go.Scatter(
            x=actual_data['date'],
            y=actual_data['total'],
            mode='lines+markers',
            name='Actual Remaining',
            line=dict(color='rgba(220, 57, 18, 1)'),
        ))

    fig.update_layout(
        title="Project Convergence Burn-up",
        xaxis_title="Date",
        yaxis_title="Remaining Issues",
        margin=dict(t=40, l=20, r=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

def _get_risk_module_bar_chart_html(top_3_modules: list) -> str:
    """
    Generate a Plotly horizontal bar chart for the top 3 riskiest modules.
    """
    if not top_3_modules:
        return None

    df = pd.DataFrame(top_3_modules)
    df = df.sort_values(by='percentage', ascending=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df['name'],
        x=df['percentage'],
        text=df['percentage'].apply(lambda x: f'{x}%'),
        textposition='auto',
        orientation='h',
        marker_color='rgba(255, 99, 132, 0.8)',
        marker_line_color='rgba(255, 99, 132, 1)',
        marker_line_width=1.5,
    ))

    fig.update_layout(
        title_text="",
        xaxis_title="风险问题占比 (%)",
        yaxis_title="模块",
        height=240,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(showgrid=True, zeroline=True, showticklabels=True),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=True),
        showlegend=False
    )

    return pio.to_html(fig, full_html=False, include_plotlyjs=False) 