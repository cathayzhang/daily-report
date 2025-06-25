# Git 分析模块 (`git_analyzer.py`) 软件设计方案

## 1. 概述

`git_analyzer.py` 模块是 "开发日报"自动化工具的数据来源核心。它封装了与 Git 仓库的所有交互，负责根据指定的条件（如日期范围、分支、作者等）查询和提取提交（commit）历史，并将原始的 Git 数据处理成结构化的信息，供上层模块使用。

## 2. 功能需求

- **仓库访问**: 能够打开并访问指定路径下的本地 Git 仓库。
- **提交查询**: 能够根据以下条件筛选提交记录：
  - 日期范围（开始日期和结束日期）。
  - 指定的分支。
  - 指定的作者。
- **信息提取**: 从每个符合条件的提交中，提取以下关键信息：
  - Commit Hash (短哈希)。
  - 作者名称。
  - 作者邮箱。
  - 提交日期和时间。
  - 提交信息 (Commit Message)。
- **数据格式化**: 将提取的信息组织成统一、干净的结构化数据（例如，字典列表），方便其他模块消费。
- **错误处理**: 能够处理无效的仓库路径、不存在的分支、Git 命令执行失败等异常情况。

## 3. 模块设计

### 3.1. 核心依赖

为了与 Git 仓库进行交互，本模块将依赖 `GitPython` 库。这是一个成熟的 Python 库，提供了面向对象的接口来操作 Git 仓库，避免了直接调用和解析 `git` 命令行工具的复杂性。

### 3.2. 函数/类设计

- `def get_commits(repo_path: str, start_date: str, end_date: str, branch: str = 'main', author: str = None) -> list[dict]:`
  - **职责**: 作为模块的主要入口点，获取符合所有条件的提交记录。
  - **参数**:
    - `repo_path`: 本地 Git 仓库的路径。
    - `start_date`: 开始日期 (格式 'YYYY-MM-DD')。
    - `end_date`: 结束日期 (格式 'YYYY-MM-DD')。
    - `branch`: 要查询的分支名，默认为 'main'。
    - `author`: (可选) 作者名，用于筛选特定作者的提交。
  - **返回值**: 一个包含多个提交信息字典的列表。每个字典代表一个 commit，结构如下：
    ```python
    {
        "hash": "a1b2c3d",
        "author_name": "John Doe",
        "author_email": "john.doe@example.com",
        "date": "2023-10-27T10:30:00+08:00",
        "message": "feat: Implement the new login feature"
    }
    ```
  - **逻辑**:
    1.  使用 `git.Repo(repo_path)` 初始化仓库对象。
    2.  构造传递给 `repo.iter_commits()` 的参数字典，包括 `branch`, `since` (对应 `start_date`), `until` (对应 `end_date`), 和 `author`。
        - **注意**: 需要对传入的日期字符串进行处理，确保其符合 `GitPython` 的要求（可能需要附加时间信息，如 'YYYY-MM-DD 00:00:00'）。
    3.  调用 `repo.iter_commits(**kwargs)` 获取提交迭代器。
    4.  遍历迭代器，对每个 `commit` 对象，调用 `_format_commit()` 函数进行格式化。
    5.  将所有格式化后的字典收集到一个列表中并返回。
  - **异常处理**:
    - 使用 `try...except git.exc.InvalidGitRepositoryError` 捕获无效仓库路径的异常。
    - 使用 `try...except git.exc.GitCommandError` 捕获分支不存在等 Git 命令执行错误。

- `def _format_commit(commit: git.Commit) -> dict:`
  - **职责**: (内部私有函数) 将 `GitPython` 的 `Commit` 对象转换成标准字典格式。
  - **逻辑**:
    1.  提取 `commit.hexsha[:7]` 作为短哈希。
    2.  提取 `commit.author.name` 和 `commit.author.email`。
    3.  提取 `commit.authored_datetime.isoformat()` 作为 ISO 8601 格式的日期字符串。
    4.  提取 `commit.message.strip()` 作为提交信息。
    5.  组装并返回字典。

## 4. 依赖关系

- **第三方库**:
  - `GitPython`: 核心依赖，用于所有 Git 操作。
- **标准库**:
  - `datetime`: 用于处理日期和时间。

## 5. 数据流

1.  `main` 模块调用 `git_analyzer.get_commits()`，并传入仓库路径、日期等参数。
2.  `get_commits` 初始化 `git.Repo` 对象。
3.  `get_commits` 遍历从 `repo.iter_commits()` 获得的提交。
4.  对于每个提交，调用 `_format_commit` 将其转换为字典。
5.  `get_commits` 将所有字典组成的列表返回给 `main` 模块。

## 6. 注意事项

- **性能**: 对于大型仓库和长日期范围，一次性加载所有提交可能会消耗较多内存。虽然当前设计是返回列表，但未来可以考虑返回一个生成器 (generator) 来优化内存使用。
- **时区**: `GitPython` 处理时间时会考虑时区信息。`authored_datetime` 是一个带时区的 `datetime` 对象，输出为 ISO 8601 格式可以保留此信息，是最佳实践。 