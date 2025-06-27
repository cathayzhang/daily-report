import argparse
import sys
import logging
import os

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
        # 1. 加载配置
        logging.info(f"正在从 '{args.config}' 加载配置...")
        config = load_config(args.config)
        logging.info("配置加载成功。")

        # 2. 加载数据
        logging.info(f"正在从 '{args.input_file}' 加载数据...")
        df = data_loader.load_data(args.input_file, config)
        logging.info(f"数据加载成功，共加载 {len(df)} 条记录。")

        # 3. 加载历史数据（在分析前）
        logging.info("加载历史数据以供分析...")
        history_mgr = history_manager.HistoryManager(config.history_path)
        history_df = history_mgr.history_df # 获取当前的历史数据
        logging.info(f"成功加载 {len(history_df)} 条历史记录。")

        # 4. 核心分析 (现在传入了历史数据)
        logging.info("开始执行核心数据分析...")
        analysis_results = analyzer.analyze(df, history_df, config)
        logging.info("数据分析完成。")

        # 处理可编辑的分析报告部分
        editable_analysis_path = os.path.join(config.report_output_dir, "editable_analysis.html")
        if os.path.exists(editable_analysis_path):
            logging.info(f"发现已存在的分析文件，将使用 '{editable_analysis_path}' 中的内容。")
            with open(editable_analysis_path, 'r', encoding='utf-8') as f:
                analysis_results['generated_text_html'] = f.read()
        else:
            logging.info(f"未发现可编辑的分析文件，将在 '{editable_analysis_path}' 创建新文件。")
            # 确保目录存在
            os.makedirs(os.path.dirname(editable_analysis_path), exist_ok=True)
            with open(editable_analysis_path, 'w', encoding='utf-8') as f:
                f.write(analysis_results['generated_text_html'])

        # 5. 更新历史数据 (使用新的分析结果)
        logging.info(f"正在更新历史数据文件: {config.history_path}...")
        # 从分析结果中提取需要记录到历史的指标
        # 未来这里可以扩展，记录更多每日快照
        metrics_to_save = {}

        # 记录总体和各优先级问题数
        metrics_to_save['total'] = analysis_results.get('overall_metrics', {}).get('total_issues', 0)
        priority_dist = analysis_results.get('priority_distribution', {})
        for priority, count in priority_dist.items():
            metrics_to_save[priority] = count
        
        # 记录A/B/C类问题总数
        class_counts = analysis_results.get('kpis', {}).get('class_counts', {})
        for class_name, count in class_counts.items():
            metrics_to_save[class_name] = count
            
        # 记录DI值
        metrics_to_save['DI'] = analysis_results.get('kpis', {}).get('di_score', 0)

        # 扩展：记录Top 5模块的问题数
        module_dist = analysis_results.get('module_distribution', {})
        if module_dist:
            # 按问题数降序排序，并取前5个
            top_5_modules = sorted(module_dist.items(), key=lambda item: item[1], reverse=True)[:5]
            for module_name, count in top_5_modules:
                # 为了CSV列名稳定，对模块名进行清洗，并添加前缀
                clean_module_name = f"module_{''.join(filter(str.isalnum, module_name))}"
                metrics_to_save[clean_module_name] = count

        history_mgr.add_record(metrics_to_save)
        history_mgr.save()
        # 获取更新 *后* 的历史数据，用于图表生成
        updated_history_df = history_mgr.history_df
        logging.info("历史数据更新完成。")

        # 6. 生成可视化图表 (HTML)
        logging.info("开始生成交互式可视化图表...")
        charts_html = visualizer.generate_all_charts(
            analysis_results,
            updated_history_df, # 使用更新后的历史数据
            config              # 传入完整的配置对象
        )
        logging.info("交互式图表HTML生成完成。")

        # 7. 准备报告上下文
        report_context = {
            "project_name": config.project_name,
            "analysis": analysis_results,
            "charts": charts_html, # 这里现在是包含HTML的字典
            "data_file": os.path.basename(args.input_file),
            "config_file": args.config,
            "historical_plans": config.historical_plans,
            "burnup_plans": config.burnup_plans
        }

        # 8. 生成最终报告
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