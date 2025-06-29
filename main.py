import sys
import logging
import os
import markdown
from datetime import date
from flask import Flask, jsonify, request, render_template_string
from waitress import serve

# 动态地将当前目录添加到sys.path，以帮助Python找到其他模块
# 这在直接从IDE或命令行运行脚本时特别有用
sys.path.append(os.getcwd())

# 现在可以安全地导入项目模块
from config_loader import load_config, Config
import data_loader
import analyzer
import history_manager
import visualizer
import database_manager
from remarks_manager import RemarksManager

# --- Global Variables for Web App ---
app = Flask(__name__)
CONFIG_PATH = "config.ini"
# ------------------------------------

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_report_data(config: Config):
    """
    This function contains the original logic to process data and generate report context.
    It's called by the web view to get fresh data for each request.
    """
    # 0. 初始化数据库
    logging.info("正在初始化数据库...")
    database_manager.init_db()
    logging.info("数据库初始化完成。")

    # 新增步骤：同步JIRA问题备注
    logging.info("正在从 remarks.csv 同步JIRA问题备注...")
    remarks_manager = RemarksManager()
    remarks_manager.sync_remarks_from_csv()
    logging.info("JIRA问题备注同步完成。")

    # 1. 加载配置
    logging.info(f"正在从 '{config.input_file}' 加载数据...")
    df = data_loader.load_data(config.input_file, config)
    logging.info(f"数据加载成功，共加载 {len(df)} 条记录。")

    # 3. 加载历史数据（在分析前）
    logging.info("从数据库加载历史数据以供分析...")
    history_df = history_manager.load_kpi_history()
    logging.info(f"成功加载 {len(history_df)} 条历史记录。")

    # 4. 核心分析 (现在传入了历史数据)
    logging.info("开始执行核心数据分析...")
    analysis_results = analyzer.analyze(df, history_df, config)
    logging.info("数据分析完成。")

    # 5. 读取用户编辑的分析建议 (从 Markdown 文件)
    logging.info("正在加载用户自定义的分析与建议...")
    editable_analysis_path = "editable_analysis.md"
    try:
        with open(editable_analysis_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
            # 将 Markdown 转换为 HTML 并注入到分析结果中
            analysis_results['generated_text_html'] = markdown.markdown(markdown_content)
        logging.info(f"成功加载并转换 '{editable_analysis_path}'。")
    except FileNotFoundError:
        logging.warning(f"'{editable_analysis_path}' 文件未找到。将使用自动生成的分析。")
        # 如果文件不存在，我们依赖于 analyzer.py 中生成的默认 'generated_text_html'
        pass

    # 6. 更新历史数据 (使用新的分析结果)
    logging.info("正在保存当日KPI到数据库...")
    
    today = date.today()
    kpis_to_save = {
        'total_issues': analysis_results.get('overall_metrics', {}).get('total_issues', 0),
        'A级': analysis_results.get('kpis', {}).get('class_counts', {}).get('A级', 0),
        'B级': analysis_results.get('kpis', {}).get('class_counts', {}).get('B级', 0),
        'C级': analysis_results.get('kpis', {}).get('class_counts', {}).get('C级', 0),
        'di_value': analysis_results.get('kpis', {}).get('di_score', 0)
    }
    
    history_manager.save_kpis(today, kpis_to_save)
    
    # 获取更新 *后* 的历史数据，用于图表生成
    updated_history_df = history_manager.load_kpi_history()
    logging.info("历史数据更新完成。")

    # 7. 生成可视化图表 (HTML)
    logging.info("开始生成交互式可视化图表...")
    charts_html = visualizer.generate_all_charts(
        analysis_results,
        updated_history_df, # 使用更新后的历史数据
        config              # 传入完整的配置对象
    )
    logging.info("交互式图表HTML生成完成。")

    # 8. 获取备注信息以供报告使用
    all_remarks = remarks_manager.get_all_remarks()

    # 9. 准备报告上下文
    report_context = {
        "report_date": date.today().strftime("%Y-%m-%d"),
        "project_name": config.project_name,
        "analysis": analysis_results,
        "charts": charts_html, # 这里现在是包含HTML的字典
        "all_remarks": all_remarks, # 新增备注字典
        "data_file": os.path.basename(config.input_file),
        "config_file": CONFIG_PATH,
    }

    return report_context, config

@app.route('/')
def report_view():
    """Renders and serves the main report page."""
    logging.info("收到HTTP请求，正在动态生成报告...")
    try:
        config = load_config(CONFIG_PATH)
        report_context, _ = generate_report_data(config)
        
        # 动态读取模板文件内容
        with open(config.template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        logging.info("报告数据已生成，正在渲染HTML...")
        return render_template_string(template_content, context=report_context)
    except Exception as e:
        logging.error(f"渲染报告页面时发生错误: {e}", exc_info=True)
        return f"<h1>报告生成失败</h1><p>错误详情: {e}</p><pre>请查看后台日志获取更多信息。</pre>", 500

@app.route('/api/remark/update', methods=['POST'])
def update_remark():
    """API endpoint to update a remark."""
    data = request.get_json()
    if not data or 'jira_key' not in data or 'remark' not in data:
        return jsonify({'success': False, 'message': '请求体不合法，必须包含 jira_key 和 remark。'}), 400

    jira_key = data['jira_key']
    new_remark = data['remark']
    
    logging.info(f"收到备注更新请求: Key={jira_key}, Remark='{new_remark[:30]}...'")

    remarks_manager = RemarksManager()
    success = remarks_manager.update_remark(jira_key, new_remark)

    if success:
        logging.info(f"备注 {jira_key} 更新成功。")
        return jsonify({'success': True, 'message': '备注更新成功！'})
    else:
        logging.error(f"备注 {jira_key} 更新失败。")
        return jsonify({'success': False, 'message': '备注更新失败，请查看服务器日志。'}), 500

def main():
    """主程序入口，负责启动Web服务器。"""
    try:
        # Initial setup before starting server
        logging.info("正在初始化数据库和备注管理器...")
        database_manager.init_db()
        remarks_manager = RemarksManager()
        remarks_manager.sync_remarks_from_csv()
        logging.info("初始化完成。")

        logging.info("正在启动开发日报Web服务器...")
        logging.info("请在浏览器中访问 http://localhost:8080")
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
        print("Starting server on http://0.0.0.0:8080")
        serve(app, host='0.0.0.0', port=8080)

    except Exception as e:
        logging.error(f"启动服务器时发生错误: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 