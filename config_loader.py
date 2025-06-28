import configparser
import os
from collections import defaultdict
from datetime import datetime

class Config:
    """一个用于存储和访问配置的类。"""
    def __init__(self, config_data):
        self.column_mapping = dict(config_data['column_mapping'])
        self.history_path = config_data['settings']['history_path']
        self.jira_base_url = config_data['settings'].get('jira_base_url', '')
        self.charts_dir = config_data['settings']['charts_dir']
        
        # visualizer模块希望得到一个根目录，然后在内部拼接 'charts'
        # 例如，如果 charts_dir 是 'output/charts'，这里会得到 'output'
        self.output_dir_for_charts = os.path.dirname(self.charts_dir)
        
        self.repo_path = config_data['git']['repo_path']
        self.branch = config_data['git']['branch']
        self.template_path = config_data['report']['template_path']
        self.report_output_dir = config_data['report']['output_dir']
        self.project_name = config_data['report'].get('project_name', '项目')
        self.overdue_threshold_days = int(config_data['analysis']['overdue_threshold_days'])
        
        # 处理可能为空的 target_tags
        tags_str = config_data['analysis'].get('target_tags', '')
        self.target_tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

        # 加载 KPI 设置
        self.a_priority_name = config_data['kpi_settings']['a_priority_name']
        risk_priorities_str = config_data['kpi_settings'].get('risk_module_priorities', '')
        self.risk_module_priorities = [p.strip() for p in risk_priorities_str.split(',') if p.strip()]

        # 加载A/B/C类问题定义
        self.class_priorities = {
            'A': [p.strip() for p in config_data['kpi_settings'].get('class_a_priorities', '').split(',') if p.strip()],
            'B': [p.strip() for p in config_data['kpi_settings'].get('class_b_priorities', '').split(',') if p.strip()],
            'C': [p.strip() for p in config_data['kpi_settings'].get('class_c_priorities', '').split(',') if p.strip()],
        }

        # 加载当前收敛计划 (旧版，待废弃)
        self.convergence_plan = self._load_single_plan(config_data)
        
        # 加载历史收敛计划 (旧版，待废弃)
        self.historical_plans = self._load_historical_plans(config_data)

        # 加载新的多维度燃尽图计划
        self.burnup_plans = self._load_burnup_plans(config_data)

        # V3.0 P2 新增：加载自动化核心图表计划
        self.burndown_plan = self._load_burndown_plan(config_data)

    def _load_single_plan(self, config_data):
        """加载旧版的单个收敛计划。"""
        if 'convergence_plan' not in config_data:
            return None
        try:
            return {
                'name': config_data['convergence_plan']['plan_name'],
                'start_date': config_data['convergence_plan']['start_date'],
                'end_date': config_data['convergence_plan']['end_date'],
                'start_count': int(config_data['convergence_plan']['start_count']),
                'end_count': int(config_data['convergence_plan']['end_count'])
            }
        except KeyError:
            return None

    def _load_burndown_plan(self, config_data):
        """加载 V3.0 P2 的自动化核心图表计划。"""
        if 'BurndownPlan' not in config_data:
            return None
        
        section = config_data['BurndownPlan']
        try:
            plan = {
                'start_date': datetime.strptime(section['start_date'], '%Y-%m-%d').date(),
                'end_date': datetime.strptime(section['end_date'], '%Y-%m-%d').date(),
                'start_counts': {
                    'A': section.getint('start_a'),
                    'B': section.getint('start_b'),
                    'C': section.getint('start_c'),
                },
                'target_counts': {
                    'A': section.getint('target_a'),
                    'B': section.getint('target_b'),
                    'C': section.getint('target_c'),
                },
                'di_weights': {
                    'A': section.getint('di_weight_a'),
                    'B': section.getint('di_weight_b'),
                    'C': section.getint('di_weight_c'),
                }
            }
            return plan
        except (KeyError, ValueError) as e:
            print(f"警告：跳过格式错误的 [BurndownPlan] 计划。错误: {e}")
            return None

    def _load_historical_plans(self, config_data):
        """从配置中加载所有历史计划。"""
        plans = defaultdict(dict)
        for key, value in config_data['convergence_plan'].items():
            if not key.startswith('history_plan_'):
                continue
            
            parts = key.split('_')
            if len(parts) < 4:
                continue
            
            plan_id = parts[2]
            attr_name = "_".join(parts[3:])
            
            if 'count' in attr_name:
                plans[plan_id][attr_name] = int(value)
            else:
                plans[plan_id][attr_name] = value

        # 将字典转换为目标格式的列表
        historical_plans_list = []
        for _, plan_data in sorted(plans.items()):
            historical_plans_list.append({
                'name': plan_data.get('name'),
                'start_date': plan_data.get('start_date'),
                'end_date': plan_data.get('end_date'),
                'start_count': plan_data.get('start_count'),
                'end_count': plan_data.get('end_count')
            })
        return historical_plans_list

    def _load_burnup_plans(self, config_data):
        """加载所有新的燃尽图计划配置。"""
        plans = []
        for section in config_data.sections():
            if not section.startswith('plan_'):
                continue
            
            plan_data = config_data[section]
            
            if not plan_data.getboolean('enabled', False):
                continue

            try:
                plan = {
                    'id': section,
                    'name': plan_data.get('plan_name', '未命名计划'),
                    'metric': plan_data['metric_name'],
                    'start_date': plan_data['start_date'],
                    'end_date': plan_data['end_date'],
                    'start_count': plan_data.getint('start_count'),
                    'end_count': plan_data.getint('end_count')
                }
                plans.append(plan)
            except (KeyError, ValueError) as e:
                print(f"警告：跳过格式错误的燃尽图计划 '{section}'。错误: {e}")
                continue
        return plans

def load_config(path: str = 'config.ini') -> Config:
    """
    读取 .ini 配置文件并返回一个配置对象。

    Args:
        path (str): 配置文件的路径。

    Returns:
        Config: 一个包含所有配置信息的对象。
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"配置文件未找到: {path}")
        
    parser = configparser.ConfigParser()
    parser.read(path, encoding='utf-8')
    return Config(parser) 