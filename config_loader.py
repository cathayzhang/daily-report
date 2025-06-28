import configparser
import logging
import os
from collections import defaultdict
from datetime import datetime

class Config:
    """一个用于存储和访问配置的类。"""
    def __init__(self, config_data):
        self._config = config_data
        self.column_mapping = dict(self._config.items('column_mapping'))
        
        # --- Settings ---
        self.jira_base_url = self._config.get('settings', 'jira_base_url', fallback='https://your-jira-instance.com/browse/')
        
        # --- Report ---
        self.template_path = self._config.get('report', 'template_path', fallback='templates/report_template.html')
        self.report_output_dir = self._config.get('report', 'output_dir', fallback='output/reports/')
        self.project_name = self._config.get('report', 'project_name', fallback='项目开发日报')
        
        # --- Analysis ---
        self.overdue_threshold_days = self._config.getint('analysis', 'overdue_threshold_days', fallback=14)
        self.target_tags = [tag.strip() for tag in self._config.get('analysis', 'target_tags', fallback='').split(',') if tag.strip()]
        
        # --- KPI Settings ---
        self.a_priority_name = self._config.get('kpi_settings', 'a_priority_name', fallback='Blocker')
        self.risk_module_priorities = [p.strip() for p in self._config.get('kpi_settings', 'risk_module_priorities', fallback='').split(',') if p.strip()]
        self.class_a_priorities = [p.strip() for p in self._config.get('kpi_settings', 'class_a_priorities', fallback='').split(',') if p.strip()]
        self.class_b_priorities = [p.strip() for p in self._config.get('kpi_settings', 'class_b_priorities', fallback='').split(',') if p.strip()]
        self.class_c_priorities = [p.strip() for p in self._config.get('kpi_settings', 'class_c_priorities', fallback='').split(',') if p.strip()]
        
        # --- DI Weights ---
        self.di_weights = {k: self._config.getint('di_weights', k) for k in self._config.options('di_weights')}
        
        # --- Load All Burnup Plans ---
        self.burnup_plans = self._load_burnup_plans()
        
        # --- Load High Risk Rules ---
        self.high_risk_rules = self.get_high_risk_rules()

    def _load_burnup_plans(self):
        """Dynamically load all sections starting with 'plan_'."""
        plans = []
        for section in self._config.sections():
            if section.startswith('plan_') and self._config.getboolean(section, 'enabled', fallback=False):
                try:
                    plan = {
                        "id": section,
                        "name": self._config.get(section, 'plan_name'),
                        "metric": self._config.get(section, 'metric'),
                        "start_date": self._config.get(section, 'start_date'),
                        "end_date": self._config.get(section, 'end_date'),
                        "start_count": self._config.getfloat(section, 'start_count'),
                        "end_count": self._config.getfloat(section, 'end_count'),
                    }
                    plans.append(plan)
                except (configparser.NoOptionError, ValueError) as e:
                    logging.warning(f"Skipping invalid burndown plan in section '{section}': {e}")
        return plans

    def get_high_risk_rules(self):
        """Parses the [HighRiskRules] section from the config file."""
        rules = []
        if not self._config.has_section('HighRiskRules'):
            return rules

        for key, value in self._config.items('HighRiskRules'):
            parts = [part.strip() for part in value.split(',')]
            if len(parts) != 3:
                logging.warning(f"Skipping malformed rule '{key}': Rule must have 3 parts (column, operator, value).")
                continue

            column, operator, val_str = parts
            
            # For 'in' and 'not_in', the value can be a comma-separated list within the value part
            if operator in ['in', 'not_in']:
                value = [v.strip() for v in val_str.split(',')]
            else:
                value = val_str

            rules.append({'column': column, 'operator': operator, 'value': value})
        
        return rules

def load_config(path: str) -> Config:
    """Loads config from the given path and returns a Config object."""
    if not path:
        raise ValueError("Config file path cannot be empty.")
    
    config_data = configparser.ConfigParser(inline_comment_prefixes=';')
    try:
        config_data.read(path, encoding='utf-8')
    except FileNotFoundError:
        logging.error(f"Config file not found at: {path}")
        raise
        
    return Config(config_data) 