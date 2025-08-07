# novel_splitter/utils.py
import re
import os
import logging # 新增导入
from rich.logging import RichHandler # 新增导入
def clean_filename(title: str, max_length: int = 60) -> str:
    """
    Cleans a string to be a valid filename.
    - Removes invalid characters.
    - Replaces whitespace with underscores.
    - Truncates to a maximum length.
    """
    # 移除Windows和Unix系统中的非法文件名字符
    title = re.sub(r'[\\/*?:"<>|]', "", title)
    title = title.replace(" ", "_").replace("\t", "_")

    # 移除标题前后的空白符
    title = title.strip('_. ')

    # 截断文件名以避免过长
    if len(title) > max_length:
        title = title[:max_length]

    return title if title else "untitled"

def ensure_dir(path: str) -> None:
    """Ensures that a directory exists."""
    if not os.path.exists(path):
        os.makedirs(path)

def setup_logger():
    """配置一个双路输出的日志系统：彩色控制台和详细的日志文件。"""

    # 获取根日志记录器
    log = logging.getLogger()
    log.setLevel(logging.DEBUG) # 设置根级别为DEBUG，以捕获所有信息

    # 如果已经有处理器，则不再重复添加，防止日志重复打印
    if log.hasHandlers():
        return log

    # 1. 配置控制台处理器 (RichHandler)
    # 只向控制台显示INFO级别及以上的信息
    console_handler = RichHandler(
        level=logging.INFO,
        rich_tracebacks=True, # 使用rich美化堆栈
        markup=True
    )
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    # 2. 配置文件处理器
    # 将所有DEBUG级别及以上的信息写入文件
    file_handler = logging.FileHandler("splitter.log", mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    # 定义写入文件的日志格式，包含时间、级别、模块和消息
    log_format = logging.Formatter(
        "%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s (%(filename)s:%(lineno)d)"
    )
    file_handler.setFormatter(log_format)

    # 为根日志记录器添加两个处理器
    log.addHandler(console_handler)
    log.addHandler(file_handler)

    return log
