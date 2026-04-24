import os
from typing import Dict, Optional
from dotenv import load_dotenv
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def _call_openai(prompt: str, temperature: float = 0.7, max_tokens: int = 450) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def summarize_text(text: str, target_length: int = 180) -> str:
    prompt = (
        f"Summarize the following content in {target_length} words or fewer."
        f"\n\nContent:\n{text}"
    )
    return _call_openai(prompt, temperature=0.5, max_tokens=300)


def generate_linkedin_post(summary: str, tone: str = "professional") -> str:
    prompt = (
        "Write a LinkedIn post based on the following summary. Keep the tone professional, engaging, and concise."
        f"\n\nSummary:\n{summary}"
    )
    return _call_openai(prompt, temperature=0.7, max_tokens=250)


def draft_email(summary: str, audience: str = "stakeholders") -> str:
    prompt = (
        "Draft a concise email to the specified audience using the summary below. Include a clear purpose and next steps."
        f"\n\nAudience: {audience}\nSummary:\n{summary}"
    )
    return _call_openai(prompt, temperature=0.7, max_tokens=350)


def create_text_from_tool(step_name: str, inputs: Dict[str, str]) -> str:
    if step_name == "summarize":
        return summarize_text(inputs.get("text", ""))
    if step_name == "linkedin_post":
        return generate_linkedin_post(inputs.get("summary", inputs.get("text", "")))
    if step_name == "email_draft":
        return draft_email(inputs.get("summary", inputs.get("text", "")))
    raise ValueError(f"Unsupported tool type: {step_name}")
