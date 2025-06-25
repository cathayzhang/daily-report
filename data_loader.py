import pandas as pd
import os
from config_loader import Config, load_config

def _rename_columns(df: pd.DataFrame, column_mapping: dict) -> pd.DataFrame:
    """
    Renames DataFrame columns based on the provided mapping.
    The mapping should be {internal_name: source_name}.
    This function reverses it for pandas' rename method.
    """
    reversed_mapping = {v: k for k, v in column_mapping.items()}
    df.rename(columns=reversed_mapping, inplace=True)
    return df

def _validate_columns(df: pd.DataFrame, required_columns: list):
    """
    Validates that all required columns exist in the DataFrame.
    """
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"错误：输入文件中缺少必需的列: '{col}' (映射后)。请检查 config.ini 中的 [column_mapping] 设置。")

def _clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Performs data cleaning operations on the DataFrame.
    """
    # Fill missing module values
    if 'module' in df.columns:
        df['module'] = df['module'].fillna('未分配模块')

    # Convert created_date to datetime objects
    if 'created_date' in df.columns:
        df['created_date'] = pd.to_datetime(df['created_date'], errors='coerce')

    # Strip whitespace from all object columns
    for col in df.select_dtypes(['object']).columns:
        df[col] = df[col].str.strip()
        
    return df

def load_data(file_path: str, config: Config) -> pd.DataFrame:
    """
    Loads data from an Excel or CSV file, renames columns, validates, and cleans the data.

    Args:
        file_path: Path to the input data file (.xlsx, .xls, .csv).
        config: The application's Config object.

    Returns:
        A cleaned and prepared pandas DataFrame.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"数据文件未找到: {file_path}")

    # Read file based on extension
    _, file_extension = os.path.splitext(file_path)
    if file_extension in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path, engine='openpyxl')
    elif file_extension == '.csv':
        df = pd.read_csv(file_path)
    else:
        raise ValueError(f"不支持的文件格式: '{file_extension}'。请输入 .xlsx, .xls, 或 .csv 文件。")

    # Rename columns to internal standard names
    df = _rename_columns(df, config.column_mapping)

    # Validate that all required internal columns are present
    required_cols = list(config.column_mapping.keys())
    _validate_columns(df, required_cols)

    # Clean and preprocess data
    df = _clean_data(df)

    return df

if __name__ == '__main__':
    # This block is for testing the data_loader module independently.
    print("--- Running data_loader.py tests ---")
    
    # 1. Load configuration
    try:
        config = load_config('config.ini')
        print("配置加载成功。")
    except Exception as e:
        print(f"配置加载失败: {e}")
        exit()

    # 2. Create a dummy data file for testing
    dummy_file_path = 'data/dummy_test_data.xlsx'
    print(f"创建测试数据文件: {dummy_file_path}")
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    # Create dummy data using source column names from config
    dummy_data = {
        config.column_mapping['summary']: ["修复登录按钮bug", "开发新首页", "调整API接口"],
        config.column_mapping['status']: ["已完成", "进行中", "待办"],
        config.column_mapping['priority']: ["高", "中", "高"],
        config.column_mapping['module']: ["用户认证", "前端", None],  # Add a None value for testing fillna
        config.column_mapping['created_date']: ["2023-10-26", "2023-10-27", "invalid-date"], # Add invalid date
        config.column_mapping['assignee']: ["张三 ", " 李四", "王五"], # Add whitespace for stripping test
        config.column_mapping['reporter']: ["产品经理A", "项目经理B", "开发C"]
    }
    dummy_df = pd.DataFrame(dummy_data)
    dummy_df.to_excel(dummy_file_path, index=False, engine='openpyxl')

    # 3. Run the load_data function
    try:
        print("\n开始加载和处理数据...")
        processed_df = load_data(dummy_file_path, config)
        print("数据加载和处理成功！")
        
        # 4. Print results for verification
        print("\n--- 处理后的DataFrame ---")
        print(processed_df.head())
        print("\n--- DataFrame 信息 ---")
        processed_df.info()
        
    except (FileNotFoundError, ValueError) as e:
        print(f"\n测试失败: {e}")
    finally:
        # 5. Clean up the dummy file
        if os.path.exists(dummy_file_path):
            os.remove(dummy_file_path)
            print(f"\n已删除测试文件: {dummy_file_path}")

    print("\n--- data_loader.py tests finished ---") 