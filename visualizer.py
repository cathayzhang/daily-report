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
    
    # --- 生成燃尽图 ---
    if history_df is not None and not history_df.empty:
        # 准备数据: 确保列名和数据类型正确
        if 'date' in history_df.columns and 'report_date' not in history_df.columns:
            history_df = history_df.rename(columns={'date': 'report_date'})
        history_df['report_date'] = pd.to_datetime(history_df['report_date'])

        # 1. 生成新的、基于计划的DI燃尽图
        if config.burndown_plan:
            # 过滤数据到计划周期内
            plan_start = pd.to_datetime(config.burndown_plan['start_date'])
            plan_end = pd.to_datetime(config.burndown_plan['end_date'])
            filtered_df = history_df[(history_df['report_date'] >= plan_start) & (history_df['report_date'] <= plan_end)].copy()
            
            di_chart_html = _create_di_burndown_chart_from_plan(filtered_df, config.burndown_plan)
            if di_chart_html:
                charts_html['di_burnup_chart_html'] = di_chart_html
                print("新的DI值燃尽图HTML已生成。")
        
        # 2. 生成旧的ABC燃尽图
        abc_plans = [p for p in config.burnup_plans if p.get('metric') in ['A', 'B', 'C']]
        if abc_plans:
            # 为旧函数准备数据：过滤并重命名回 'date'
            plan_start = min(pd.to_datetime(p['start_date']) for p in abc_plans)
            plan_end = max(pd.to_datetime(p['end_date']) for p in abc_plans)
            
            # 使用 DI plan 的日期范围来对齐
            if config.burndown_plan:
                plan_start = pd.to_datetime(config.burndown_plan['start_date'])
                plan_end = pd.to_datetime(config.burndown_plan['end_date'])

            filtered_df_for_old_chart = history_df[(history_df['report_date'] >= plan_start) & (history_df['report_date'] <= plan_end)].copy()
            filtered_df_for_old_chart = filtered_df_for_old_chart.rename(columns={'report_date': 'date'})

            abc_chart_html = _get_burnup_chart_html(
                filtered_df_for_old_chart,
                abc_plans,
                "按类问题收敛燃尽图",
                "剩余问题数"
            )
            if abc_chart_html:
                charts_html['abc_burnup_chart_html'] = abc_chart_html
                print("ABC问题燃尽图HTML已生成。")
                
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

def _get_burnup_chart_html(history_df: pd.DataFrame, plans: list, title: str, yaxis_title: str) -> str:
    """
    根据配置中的多个计划，生成项目收敛燃尽图。
    """
    if history_df is None or history_df.empty or not plans:
        return None

    history_df['date'] = pd.to_datetime(history_df['date'])
    history_df = history_df.sort_values('date')
    
    fig = go.Figure()

    # 定义一组颜色以便区分不同的计划
    colors = [
        'rgba(220, 57, 18, 1)',   # Red
        'rgba(54, 162, 235, 1)', # Blue
        'rgba(255, 193, 7, 1)',   # Yellow
        'rgba(75, 192, 192, 1)',  # Teal
        'rgba(153, 102, 255, 1)'  # Purple
    ]

    for i, plan in enumerate(plans):
        color = colors[i % len(colors)]
        
        try:
            plan_start_date = pd.to_datetime(plan['start_date'])
            plan_end_date = pd.to_datetime(plan['end_date'])
            start_count = plan['start_count']
            end_count = plan['end_count']
            metric_name = plan['metric']
            plan_name = plan['name']
        except (KeyError, TypeError) as e:
            print(f"警告：跳过数据不完整的计划 '{plan.get('id', 'N/A')}': {e}")
            continue

        # 1. 绘制计划线 (虚线)
        fig.add_trace(go.Scatter(
            x=[plan_start_date, plan_end_date],
            y=[start_count, end_count],
            mode='lines',
            name=f"计划: {plan_name}",
            line=dict(color=color, dash='dash'),
            legendgroup=plan_name,
        ))

        # 2. 绘制实际值线 (实线)
        if metric_name in history_df.columns:
            actual_data = history_df[history_df['date'].between(plan_start_date, plan_end_date)]
            if not actual_data.empty:
                fig.add_trace(go.Scatter(
                    x=actual_data['date'],
                    y=actual_data[metric_name],
                    mode='lines+markers',
                    name=f"实际: {plan_name}",
                    line=dict(color=color),
                    legendgroup=plan_name,
                ))
        else:
            print(f"警告：在历史数据中未找到指标 '{metric_name}'，无法绘制实际曲线。")


    fig.update_layout(
        title=go.layout.Title(
            text=title,
            y=0.95,
            x=0.05,
            xanchor='left',
            yanchor='top'
        ),
        xaxis_title="日期",
        yaxis_title=yaxis_title,
        height=450,
        margin=dict(l=70, r=40, b=60, t=80),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1)
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs='cdn')

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

def _create_di_burndown_chart_from_plan(history_df: pd.DataFrame, plan_data: dict) -> str:
    """根据新的 [BurndownPlan] 配置和历史数据，生成 DI 燃尽图。"""
    if history_df.empty:
        return ""

    history_df = history_df.sort_values('report_date')

    # 计算理想DI系列
    start_date = pd.to_datetime(plan_data['start_date'])
    end_date = pd.to_datetime(plan_data['end_date'])
    total_days = (end_date - start_date).days
    
    if total_days <= 0:
        return ""

    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    ideal_counts_a = np.linspace(plan_data['start_counts']['A'], plan_data['target_counts']['A'], total_days + 1)
    ideal_counts_b = np.linspace(plan_data['start_counts']['B'], plan_data['target_counts']['B'], total_days + 1)
    ideal_counts_c = np.linspace(plan_data['start_counts']['C'], plan_data['target_counts']['C'], total_days + 1)
    
    ideal_di_values = (ideal_counts_a * plan_data['di_weights']['A'] +
                       ideal_counts_b * plan_data['di_weights']['B'] +
                       ideal_counts_c * plan_data['di_weights']['C'])
    
    ideal_di_series = pd.Series(ideal_di_values, index=date_range)

    fig = go.Figure()
    # ... (code to add traces) ...
    fig.update_layout(
        title_text="DI值收敛燃尽图",
        xaxis_title="日期",
        yaxis_title="DI值",
        xaxis_type='date',  # 强制X轴为日期类型
        height=450,
        margin=dict(l=70, r=40, b=60, t=80),
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
    )
    return pio.to_html(fig, full_html=False, include_plotlyjs=False) 