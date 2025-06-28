import argparse
import sys
import logging
import os
import markdown
from datetime import date

# 动态地将当前目录添加到sys.path，以帮助Python找到其他模块
# 这在直接从IDE或命令行运行脚本时特别有用
sys.path.append(os.getcwd())

# 现在可以安全地导入项目模块
from config_loader import load_config
import data_loader
import analyzer
import history_manager
import visualizer
import report_generator
import database_manager

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argument_parser() -> argparse.ArgumentParser:
    """配置和返回一个 argparse.ArgumentParser 对象。"""
    parser = argparse.ArgumentParser(description="开发日报自动化生成工具。")
    parser.add_argument(
        "input_file",
        type=str,
        help="输入的源数据文件路径 (Excel or CSV)。"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.ini",
        help="配置文件的路径 (默认为 'config.ini')。"
    )
    return parser

def main():
    """主程序入口，负责编排整个日报生成流程。"""
    arg_parser = setup_argument_parser()
    args = arg_parser.parse_args()

    try:
        # 0. 初始化数据库
        logging.info("正在初始化数据库...")
        database_manager.init_db()
        logging.info("数据库初始化完成。")

        # 1. 加载配置
        logging.info(f"正在从 '{args.config}' 加载配置...")
        config = load_config(args.config)
        logging.info("配置加载成功。")

        # 2. 加载数据
        logging.info(f"正在从 '{args.input_file}' 加载数据...")
        df = data_loader.load_data(args.input_file, config)
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

        # 8. 准备报告上下文
        report_context = {
            "project_name": config.project_name,
            "analysis": analysis_results,
            "charts": charts_html, # 这里现在是包含HTML的字典
            "data_file": os.path.basename(args.input_file),
            "config_file": args.config,
            "historical_plans": config.historical_plans,
            "burnup_plans": config.burnup_plans
        }

        # 9. 生成最终报告
        logging.info(f"开始生成HTML报告，输出至 '{config.report_output_dir}'...")
        report_path = report_generator.generate_report(
            report_context,
            config.template_path,
            config.report_output_dir
        )
        logging.info(f"恭喜！报告已成功生成: {report_path}")

    except FileNotFoundError as e:
        logging.error(f"文件未找到错误: {e}")
        sys.exit(1)
    except ValueError as e:
        logging.error(f"值错误或配置问题: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"发生未知错误: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 