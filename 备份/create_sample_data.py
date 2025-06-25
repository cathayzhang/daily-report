import pandas as pd
import os

# 从 config.ini 加载列名，以便测试数据与项目配置保持一致
import configparser
config = configparser.ConfigParser()
config.read('config.ini')
cm = config['column_mapping']

# 确保 data 目录存在
os.makedirs('data', exist_ok=True)

# 创建与配置文件匹配的模拟数据
dummy_data = {
    cm['summary']: ["修复登录按钮bug", "开发新首页", "调整API接口", "数据库性能优化", "更新第三方SDK", "撰写技术文档", "修复支付网关超时", "UI界面微调", "部署测试环境", "重构用户认证模块"],
    cm['status']: ["已完成", "进行中", "待办", "已完成", "进行中", "已完成", "待办", "已完成", "进行中", "待办"],
    cm['priority']: ["高", "中", "高", "高", "低", "中", "紧急", "低", "中", "高"],
    cm['module']: ["用户认证", "前端", "后端", "数据库", "核心库", "文档", "支付", "前端", "运维", "用户认证"],
    cm['created_date']: ["2023-10-01", "2023-10-15", "2023-10-26", "2023-09-10", "2023-10-20", "2023-10-05", "2023-10-27", "2023-10-11", "2023-10-25", "2023-09-01"],
    cm['assignee']: ["张三", "李四", "王五", "张三", "赵六", "孙七", "王五", "李四", "周八", "张三"],
    cm['reporter']: ["产品A", "经理B", "开发C", "测试D", "产品A", "经理B", "客户服务", "设计E", "开发C", "架构师F"]
}
df = pd.DataFrame(dummy_data)

# 保存到 Excel 文件
file_path = 'data/sample_data.xlsx'
df.to_excel(file_path, index=False, engine='openpyxl')

print(f"示例数据文件已创建在: {file_path}") 