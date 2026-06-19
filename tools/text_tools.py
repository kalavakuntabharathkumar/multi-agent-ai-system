import os
from typing import Dict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

_parser = StrOutputParser()

_summarize_prompt = PromptTemplate(
    input_variables=["text", "target_length"],
    template="Summarize the following content in {target_length} words or fewer.\n\nContent:\n{text}",
)

_linkedin_prompt = PromptTemplate(
    input_variables=["summary"],
    template=(
        "Write a LinkedIn post based on the following summary. "
        "Keep the tone professional, engaging, and concise.\n\nSummary:\n{summary}"
    ),
)

_email_prompt = PromptTemplate(
    input_variables=["summary", "audience"],
    template=(
        "Draft a concise email to the specified audience using the summary below. "
        "Include a clear purpose and next steps.\n\nAudience: {audience}\nSummary:\n{summary}"
    ),
)

_summarize_chain = None
_linkedin_chain = None
_email_chain = None


def _get_chains():
    global _summarize_chain, _linkedin_chain, _email_chain
    if _summarize_chain is None:
        api_key = os.getenv("OPENAI_API_KEY", "")
        llm_default = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, max_tokens=450, openai_api_key=api_key)
        llm_summarize = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.5, max_tokens=300, openai_api_key=api_key)
        _summarize_chain = _summarize_prompt | llm_summarize | _parser
        _linkedin_chain = _linkedin_prompt | llm_default | _parser
        _email_chain = _email_prompt | llm_default | _parser
    return _summarize_chain, _linkedin_chain, _email_chain


def summarize_text(text: str, target_length: int = 180) -> str:
    chain, _, _ = _get_chains()
    return chain.invoke({"text": text, "target_length": str(target_length)})


def generate_linkedin_post(summary: str, tone: str = "professional") -> str:
    _, chain, _ = _get_chains()
    return chain.invoke({"summary": summary})


def draft_email(summary: str, audience: str = "stakeholders") -> str:
    _, _, chain = _get_chains()
    return chain.invoke({"summary": summary, "audience": audience})


def create_text_from_tool(step_name: str, inputs: Dict[str, str]) -> str:
    if step_name == "summarize":
        return summarize_text(inputs.get("text", ""))
    if step_name == "linkedin_post":
        return generate_linkedin_post(inputs.get("summary", inputs.get("text", "")))
    if step_name == "email_draft":
        return draft_email(inputs.get("summary", inputs.get("text", "")))
    if step_name == "web_search":
        from tools.search_tool import run_web_search
        query = inputs.get("query", inputs.get("text", inputs.get("summary", "")))
        return run_web_search(query)
    if step_name == "document_qa":
        from tools.document_tool import answer_from_document
        document = inputs.get("text", inputs.get("summary", ""))
        question = inputs.get("question", inputs.get("query", "Summarize the key points."))
        return answer_from_document(document, question)
    raise ValueError(f"Unsupported tool type: {step_name}")
