# src/text2speech/config.py
import os
from dotenv import load_dotenv

# [新增] 从 .env 文件加载环境变量，这对于本地开发非常方便
# 在生产环境中，您应该直接设置系统的环境变量
load_dotenv()

# --- 基础路径配置 (保持不变) ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS_DIR = os.path.join(BASE_DIR, 'results')
METADATA_DIR = os.path.join(RESULTS_DIR, 'metadata')
SPLITDATA_DIR = os.path.join(RESULTS_DIR, 'splitdata')
VOICEDATA_DIR = os.path.join(RESULTS_DIR, 'voicedata')
VECTORTEMP_DIR = os.path.join(RESULTS_DIR, 'vectortemp')

BOOKS_DIR = os.getenv("BOOKS_DIR", "")

LLM_API_KEY = os.getenv("LLM_API_KEY", "123456")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://127.0.0.1:8080/v1")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "qwen3")

# --- 日志配置 (从环境变量加载) ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

