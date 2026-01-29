# app/core/azure_openai.py
from .azure_openai_client import call_chat

def call_model(system_prompt: str, user_prompt: str) -> str:
    """
    旧 app.services.azure_openai_service.call_model と同じ役割。
    既存コードを壊さず Core に統合するための薄いラッパ。
    """
    return call_chat(system_prompt, user_prompt)
