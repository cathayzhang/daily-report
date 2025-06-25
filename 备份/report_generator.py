import os
from datetime import date
from jinja2 import Environment, FileSystemLoader, exceptions

def generate_report(context: dict, template_path: str, output_dir: str) -> str:
    """
    使用Jinja2模板和分析数据生成HTML报告。

    Args:
        context (dict): 包含所有分析结果和图表路径的字典。
        template_path (str): Jinja2模板文件的路径。
        output_dir (str): 保存报告的目录。

    Returns:
        str: 生成的报告文件的完整路径。
    """
    try:
        template_dir = os.path.dirname(template_path)
        template_name = os.path.basename(template_path)
        
        env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
        template = env.get_template(template_name)
        
        # 添加报告生成日期到上下文中
        context['report_date'] = date.today().strftime("%Y-%m-%d")
        
        # 将整个context字典作为名为'context'的变量传递给模板
        report_content = template.render(context=context)
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 定义输出文件路径
        report_filename = f"{context['report_date']}-Report.html"
        output_path = os.path.join(output_dir, report_filename)
        
        # 保存报告
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content)
            
        return os.path.abspath(output_path)

    except exceptions.TemplateNotFound:
        print(f"错误：模板文件未找到 '{template_path}'")
        raise
    except exceptions.TemplateSyntaxError as e:
        print(f"错误：模板语法错误 '{template_path}' at line {e.lineno}: {e.message}")
        raise
    except Exception as e:
        print(f"生成报告时发生未知错误: {e}")
        raise

if __name__ == '__main__':
    # 这是一个用于测试和演示的示例
    print("开始测试 ReportGenerator 模块...")
    
    # 1. 模拟从各模块获取的数据
    mock_context = {
        "analysis": {
            "overall_metrics": {
                "total_issues": 150,
                "resolved_issues": 120,
                "unresolved_issues": 30,
            },
            "priority_distribution": {"高": 25, "中": 50, "低": 5},
            "status_distribution": {"已完成": 120, "进行中": 20, "待办": 10},
            "module_distribution": {"后端API": 10, "用户认证": 8, "前端UI": 12},
            "overdue_issues": [
                {"summary": "修复古老的IE6兼容问题", "assignee": "王五", "age": 99},
                {"summary": "重构支付模块", "assignee": "李四", "age": 45},
            ],
            "tagged_issues": [],
        },
        "charts": {
            "trend_chart_path": os.path.abspath("output/charts/trend_chart_20231027103000.png"),
            "module_dist_path": os.path.abspath("output/charts/module_dist_20231027103000.png"),
        },
        "data_file": "data/sample_jira_export.xlsx",
    }

    # 2. 定义文件路径
    TEMPLATE_FILE = os.path.join("templates", "report_template.html")
    OUTPUT_DIR = os.path.join("output", "reports")
    
    # 3. 检查模板文件是否存在，如果不存在则创建一个简单的占位符
    if not os.path.exists(TEMPLATE_FILE):
        print(f"警告：模板文件 '{TEMPLATE_FILE}' 不存在，将创建一个简单的占位符。")
        os.makedirs(os.path.dirname(TEMPLATE_FILE), exist_ok=True)
        with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>开发日报 - {{ report_date }}</title>
</head>
<body>
    <h1>开发日报 {{ report_date }}</h1>
    <h2>数据源: {{ context.data_file }}</h2>
    
    <h3>概览</h3>
    <ul>
    {% for key, value in context.analysis.overall_metrics.items() %}
        <li>{{ key }}: {{ value }}</li>
    {% endfor %}
    </ul>

    <h3>图表</h3>
    <p>趋势图:</p>
    <img src="{{ context.charts.trend_chart_path }}" alt="趋势图">
    <p>模块分布图:</p>
    <img src="{{ context.charts.module_dist_path }}" alt="模块分布图">

    <h3>超期问题 ({{ context.analysis.overdue_issues|length }}个)</h3>
    <table border="1">
        <tr><th>标题</th><th>负责人</th><th>超期天数</th></tr>
    {% for issue in context.analysis.overdue_issues %}
        <tr>
            <td>{{ issue.summary }}</td>
            <td>{{ issue.assignee }}</td>
            <td>{{ issue.age }}</td>
        </tr>
    {% else %}
        <tr><td colspan="3">无超期问题。</td></tr>
    {% endfor %}
    </table>
</body>
</html>
            """)

    # 4. 生成报告
    try:
        report_path = generate_report(mock_context, TEMPLATE_FILE, OUTPUT_DIR)
        print(f"报告已成功生成并保存到: {report_path}")
    except Exception as e:
        print(f"报告生成失败: {e}")
    
    print("\nReportGenerator 模块测试完成。") 