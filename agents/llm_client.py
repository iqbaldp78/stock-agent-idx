"""
LLM client — 9Router OpenAI-compatible API.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import (
    LLM_BASE_URL,
    LLM_MODEL_AGENT,
    LLM_MODEL_DEBATE_FALLBACK,
    LLM_MODEL_IM_FALLBACK,
    LLM_TEMPERATURE_DEBATE,
    LLM_TEMPERATURE_IM,
    NINEROUTER_API_KEY,
    get_model_for_agent,
    validate_llm_model,
)

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
_REFUSAL_RE = re.compile(
    r"(I'm Kiro|I am Kiro|coding assistant|development environment|"
    r"I cannot help with|I can't help with|as an AI (assistant|model))",
    re.IGNORECASE,
)


def get_chat_model(
    model: str,
    *,
    temperature: float = LLM_TEMPERATURE_DEBATE,
    max_tokens: int = 2048,
    json_mode: bool = True,
) -> ChatOpenAI:
    validate_llm_model(model)
    kwargs: dict[str, Any] = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    return ChatOpenAI(
        model=model,
        base_url=LLM_BASE_URL,
        api_key=NINEROUTER_API_KEY or "9router",
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=300,
        model_kwargs=kwargs,
    )


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = _JSON_BLOCK_RE.search(text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _is_refusal(content: str) -> bool:
    return bool(_REFUSAL_RE.search(content))


def _invoke_once(
    model: str,
    system: str,
    user: str,
    *,
    temperature: float,
    max_tokens: int,
    json_mode: bool,
) -> tuple[dict[str, Any] | None, str]:
    """Single LLM call; returns (parsed_json, raw_content)."""
    try:
        llm = get_chat_model(
            model, temperature=temperature, max_tokens=max_tokens, json_mode=json_mode
        )
        response = llm.invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        content = response.content
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        raw = str(content)
        if _is_refusal(raw):
            logger.warning("[LLM] persona refusal model=%s preview=%s", model, raw[:120])
            return None, raw
        parsed = _extract_json(raw)
        return parsed, raw
    except Exception as e:
        logger.warning("[LLM] invoke failed model=%s: %s", model, e)
        return None, ""


def invoke_json(
    model: str,
    system: str,
    user: str,
    *,
    fallback_model: str | None = None,
    temperature: float = LLM_TEMPERATURE_DEBATE,
    max_tokens: int = 2048,
    json_schema_hint: str | None = None,
    agent: str | None = None,
    ticker: str | None = None,
) -> dict[str, Any] | None:
    """
    Call LLM and parse JSON. Repair retry + fallback model on failure.
    """
    from agents.debate.personas import DEBATE_JSON_SCHEMA

    schema_hint = json_schema_hint or DEBATE_JSON_SCHEMA
    models_to_try: list[str] = [model]
    if fallback_model and fallback_model != model:
        models_to_try.append(fallback_model)

    ctx = f" agent={agent} ticker={ticker}" if agent else ""

    for attempt_model in models_to_try:
        for json_mode in (True, False):
            parsed, raw = _invoke_once(
                attempt_model,
                system,
                user,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
            if parsed is not None:
                logger.info("[LLM] OK model=%s%s json_mode=%s", attempt_model, ctx, json_mode)
                return parsed

            if raw and not _is_refusal(raw):
                repair_user = (
                    f"Your previous response was invalid. Output ONLY valid JSON matching:\n"
                    f"{schema_hint}\n"
                    f"No markdown. No explanation. Start with {{ and end with }}."
                )
                parsed2, _ = _invoke_once(
                    attempt_model,
                    system,
                    repair_user,
                    temperature=0.1,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )
                if parsed2 is not None:
                    logger.info("[LLM] OK after repair model=%s%s", attempt_model, ctx)
                    return parsed2

            if raw:
                logger.warning(
                    "[LLM] JSON parse failed model=%s%s json_mode=%s preview=%s",
                    attempt_model,
                    ctx,
                    json_mode,
                    raw[:200],
                )

    return None


def invoke_json_for_agent(
    agent: str,
    round_num: int,
    system: str,
    user: str,
    *,
    ticker: str | None = None,
    fallback_model: str | None = None,
) -> dict[str, Any] | None:
    """Invoke LLM using per-agent model from config."""
    model = get_model_for_agent(agent, round_num)
    fb = fallback_model or LLM_MODEL_DEBATE_FALLBACK
    logger.info("[LLM] agent=%s round=%s model=%s", agent, round_num, model)
    return invoke_json(
        model,
        system,
        user,
        fallback_model=fb,
        agent=agent,
        ticker=ticker,
    )


def invoke_json_im(
    model: str,
    system: str,
    user: str,
    *,
    fallback_model: str | None = None,
) -> dict[str, Any] | None:
    from agents.debate.personas import IM_JSON_SCHEMA

    return invoke_json(
        model,
        system,
        user,
        fallback_model=fallback_model or LLM_MODEL_IM_FALLBACK,
        temperature=LLM_TEMPERATURE_IM,
        max_tokens=4096,
        json_schema_hint=IM_JSON_SCHEMA,
        agent="investment_manager",
    )


def health_check(timeout: float = 5.0) -> bool:
    if not NINEROUTER_API_KEY or NINEROUTER_API_KEY == "your_key_from_dashboard":
        logger.debug("[LLM] health_check: API key not configured")
        return False
    url = LLM_BASE_URL.rstrip("/") + "/models"
    try:
        headers = {"Authorization": f"Bearer {NINEROUTER_API_KEY}"}
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                return True
            logger.warning("[LLM] health_check status=%s", resp.status_code)
            return False
    except Exception as e:
        logger.warning("[LLM] health_check failed: %s", e)
        return False


def get_status() -> dict[str, Any]:
    return {
        "base_url": LLM_BASE_URL,
        "healthy": health_check(),
        "api_key_configured": bool(
            NINEROUTER_API_KEY and NINEROUTER_API_KEY != "your_key_from_dashboard"
        ),
        "agent_models_r1": dict(LLM_MODEL_AGENT),
    }
