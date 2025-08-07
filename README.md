# Novel Splitter (小说拆分器) v0.2.0

一个使用 **LangChain** 和 **LangGraph** 构建的、强大且可扩展的Python工具，用于智能地将小说 `.txt` 文件拆分为独立章节。

核心特性：
- **LangGraph驱动**：整个流程被建模为一个清晰、可调试的状态图。
- **支持本地模型**：通过 `langchain-openai`，可以轻松对接任何兼容OpenAI API的本地服务（如Ollama, vLLM, LM Studio等）。
- **人机协同**：保留了关键的“预览-审核”步骤，确保操作安全。
  ...

## 安装

```bash
# 克隆项目
git clone <your-repo-url>
cd novel_splitter_project

# 使用uv或pip安装 (会自动安装langchain, langgraph等依赖)
uv pip install -e .
```

## 配置

此工具通过 `langchain-openai` 与LLM服务通信，配置非常灵活。

### 方案一：使用本地LLM服务（推荐）

假设你的本地模型服务（如Ollama+LiteLLM）运行在 `http://localhost:8000`。

1.  **启动你的本地服务**。
2.  **设置环境变量**：
    ```bash
    # 设置服务的URL
    export OPENAI_API_BASE="http://localhost:8000/v1"
    
    # 设置API Key (对于很多本地服务，可以是任意非空字符串)
    export OPENAI_API_KEY="not-needed"
    ```

### 方案二：使用官方OpenAI服务

1.  获取你的 [OpenAI API Key](https://platform.openai.com/api-keys)。
2.  **设置环境变量**：
    ```bash
    export OPENAI_API_KEY="sk-..."
    # 不要设置 OPENAI_API_BASE
    ```

## 如何使用

修改 `examples/split_my_novel.py` 以指向你的模型和文件，然后运行。

```python
# examples/split_my_novel.py
import os
from novel_splitter import NovelSplitter

def main():
    # --- 配置你的LLM服务 ---
    # 对于本地服务 (例如，Ollama配合LiteLLM在8000端口)
    # 1. 确保你的本地服务正在运行
    # 2. 在终端设置:
    #    export OPENAI_API_BASE="http://localhost:8000/v1"
    #    export OPENAI_API_KEY="ollama" (或你的服务需要的任何key)
    #
    # 对于官方OpenAI服务, 只需设置 OPENAI_API_KEY
    #    export OPENAI_API_KEY="sk-..."

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_API_BASE", "http://localhost:8000/v1")  # 默认本地服务URL

    if not api_key:
        print("错误：请先设置 OPENAI_API_KEY 环境变量！")
        return

    # 创建拆分器实例，并传入连接参数
    splitter = NovelSplitter(
        api_key=api_key,
        base_url=base_url,
        model_name="Qwen3-30B-A3B-Instruct-2507-UD-Q4_K_XL.gguf" # 或你的本地模型名，如 "llama3"
    )

    # 指定你的小说文件路径
    novel_path = "sample_novel.txt"
    if not os.path.exists(novel_path):
        print(f"错误：示例小说 '{novel_path}' 未找到。")
        return

    # 运行拆分流程
    splitter.run(filepath=novel_path)

if __name__ == "__main__":
    main()

```

运行脚本：

```bash
uv run python examples/split_my_novel.py
```
