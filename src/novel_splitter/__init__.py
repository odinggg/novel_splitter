# novel_splitter/__init__.py
"""
A robust tool to split novel text files into chapters using LLMs
with a human-in-the-loop confirmation step.
"""
__version__ = "0.1.0"

import os

from . import config
from .core import NovelSplitter


def main() -> None:
    api_key = config.LLM_API_KEY
    base_url = config.LLM_BASE_URL

    if not api_key:
        print("错误：请先设置 OPENAI_API_KEY 环境变量！")
        return

    # 创建拆分器实例，并传入连接参数
    splitter = NovelSplitter(
        api_key=api_key,
        base_url=base_url,
        model_name=config.LLM_MODEL_NAME  # 或你的本地模型名，如 "llama3"
    )

    # 指定你的小说文件路径
    novel_path = config.BOOKS_DIR
    # 2. 检查路径是否存在
    if not os.access(novel_path, os.R_OK):
        print(f"错误：目录 '{novel_path}' 不可读。请检查权限。")
        return
    elif os.path.isfile(novel_path):
        try:
            splitter.run(filepath=str(novel_path), auto_confirm=True)
        except Exception as e:
            print(f"    处理文件 {novel_path} 时发生错误: {e}")
    elif os.path.isdir(novel_path):
        print(f"开始递归遍历目录: {novel_path}")
        found_files_count = 0
        # 3. 使用 os.walk() 递归遍历
        for root, dirs, files in os.walk(novel_path):
            for filename in files:
                # 检查文件名是否以 .txt 结尾
                if filename.endswith(".txt"):
                    found_files_count += 1
                    # 使用 os.path.join() 来构建完整的文件路径
                    file_path = os.path.join(root, filename)

                    print(f"--> 正在处理文件: {file_path}")
                    try:
                        splitter.run(filepath=str(file_path), auto_confirm=True)
                    except Exception as e:
                        print(f"    处理文件 {file_path} 时发生错误: {e}")

        if found_files_count == 0:
            print("未找到任何 .txt 文件。")
        print(f"\n所有文件处理完毕 (共处理 {found_files_count} 个文件)。")
    else:
        print(f"错误：路径 '{novel_path}' 既不是文件也不是目录。请检查路径。")
