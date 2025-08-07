# novel_splitter/llm_interface.py
from typing import Optional, Any, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import SecretStr

# 注意：返回值类型变了
def create_llm_and_parser(
        api_key: str,
        base_url: Optional[str] = None,
        model_name: str = "gpt-3.5-turbo"
) -> Tuple[ChatOpenAI, JsonOutputParser]:
    """
    初始化并返回一个LLM客户端和一个JSON解析器。

    :return: 一个包含 (llm, parser) 的元组。
    """
    parser = JsonOutputParser()

    llm = ChatOpenAI(
        model=model_name,
        api_key=SecretStr(api_key),
        base_url=base_url,
        temperature=0.0,
        max_retries=2,
    )

    return llm, parser
