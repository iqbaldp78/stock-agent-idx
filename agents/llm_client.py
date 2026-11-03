"""
LLM client — 9Router OpenAI-compatible API.
"""
from __future__ import annotations

import os
import json
import logging
import re
from typing import Any

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import (
    LLM_BASE_URL,
    LLM_FALLBACK_BASE_URL,
    LLM_FALLBACK_API_KEY,
    LLM_FALLBACK_MODEL,
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
    base_url: str | None = None,
    api_key: str | None = None,
    temperature: float = LLM_TEMPERATURE_DEBATE,
    max_tokens: int = 2048,
    json_mode: bool = True,
    timeout: float | None = None,
) -> ChatOpenAI:
    validate_llm_model(model)
    kwargs: dict[str, Any] = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    
    actual_timeout = timeout if timeout is not None else float(os.getenv("LLM_TIMEOUT", "30.0"))
    target_base_url = (base_url or LLM_BASE_URL).rstrip("/")
    target_api_key = api_key if api_key is not None else (NINEROUTER_API_KEY or "9router")

    # Force max_retries to 0 so LangChain doesn't block indefinitely on 9router stalls
    return ChatOpenAI(
        model=model,
        base_url=target_base_url,
        api_key=target_api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=actual_timeout,
        max_retries=0,
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
    base_url: str | None = None,
    api_key: str | None = None,
) -> tuple[dict[str, Any] | None, str, Exception | None]:
    """Single LLM call; returns (parsed_json, raw_content, exception)."""
    target_base_url = (base_url or LLM_BASE_URL).rstrip("/")
    target_api_key = api_key if api_key is not None else (NINEROUTER_API_KEY or "9router")
    try:
        llm = get_chat_model(
            model,
            base_url=target_base_url,
            api_key=target_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
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
            logger.warning("[LLM] persona refusal model=%s base_url=%s preview=%s", model, target_base_url, raw[:120])
            return None, raw, None
        parsed = _extract_json(raw)
        return parsed, raw, None
    except Exception as e:
        logger.error("[LLM ERROR] Call to %s failed for model=%s: %s", target_base_url, model, e)
        return None, "", e


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
    If primary LLM endpoint fails, immediately switch to LLM_FALLBACK_BASE_URL.
    """
    from agents.debate.personas import DEBATE_JSON_SCHEMA

    schema_hint = json_schema_hint or DEBATE_JSON_SCHEMA
    models_to_try: list[str] = [model]
    if fallback_model and fallback_model != model:
        models_to_try.append(fallback_model)

    ctx = f" agent={agent} ticker={ticker}" if agent else ""
    last_err: Exception | None = None

    # 1. Primary endpoint execution
    for attempt_model in models_to_try:
        for json_mode in (True, False):
            parsed, raw, err = _invoke_once(
                attempt_model,
                system,
                user,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
            if err:
                last_err = err
            if parsed is not None:
                logger.info("[LLM] OK model=%s%s json_mode=%s", attempt_model, ctx, json_mode)
                return parsed

            if raw and not _is_refusal(raw):
                repair_user = (
                    f"Your previous response was invalid. Output ONLY valid JSON matching:\n"
                    f"{schema_hint}\n"
                    f"No markdown. No explanation. Start with {{ and end with }}."
                )
                parsed2, _, err2 = _invoke_once(
                    attempt_model,
                    system,
                    repair_user,
                    temperature=0.1,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )
                if err2:
                    last_err = err2
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

    # 2. Fallback endpoint execution (if primary failed)
    if LLM_FALLBACK_BASE_URL and LLM_FALLBACK_BASE_URL != LLM_BASE_URL:
        logger.warning(
            "[LLM FALLBACK] Primary endpoint failed%s (last_err=%s). Switching to fallback: %s with model=%s",
            ctx,
            last_err,
            LLM_FALLBACK_BASE_URL,
            LLM_FALLBACK_MODEL,
        )
        for json_mode in (True, False):
            parsed, raw, err = _invoke_once(
                LLM_FALLBACK_MODEL,
                system,
                user,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
                base_url=LLM_FALLBACK_BASE_URL,
                api_key=LLM_FALLBACK_API_KEY,
            )
            if err:
                last_err = err
            if parsed is not None:
                logger.info("[LLM FALLBACK OK] Fallback model=%s%s json_mode=%s succeeded", LLM_FALLBACK_MODEL, ctx, json_mode)
                return parsed

            if raw and not _is_refusal(raw):
                repair_user = (
                    f"Your previous response was invalid. Output ONLY valid JSON matching:\n"
                    f"{schema_hint}\n"
                    f"No markdown. No explanation. Start with {{ and end with }}."
                )
                parsed2, _, err2 = _invoke_once(
                    LLM_FALLBACK_MODEL,
                    system,
                    repair_user,
                    temperature=0.1,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                    base_url=LLM_FALLBACK_BASE_URL,
                    api_key=LLM_FALLBACK_API_KEY,
                )
                if err2:
                    last_err = err2
                if parsed2 is not None:
                    logger.info("[LLM FALLBACK OK] Fallback model=%s%s after repair succeeded", LLM_FALLBACK_MODEL, ctx)
                    return parsed2

    if last_err:
        logger.error("[LLM EXHAUSTED] All attempts to LLM_BASE_URL (%s) and fallback (%s) failed. Final error: %s", LLM_BASE_URL, LLM_FALLBACK_BASE_URL, last_err)
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
    # 1. Check primary health
    if NINEROUTER_API_KEY and NINEROUTER_API_KEY != "your_key_from_dashboard":
        url = LLM_BASE_URL.rstrip("/") + "/models"
        try:
            headers = {"Authorization": f"Bearer {NINEROUTER_API_KEY}"}
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    return True
                logger.warning("[LLM] primary health_check status=%s", resp.status_code)
        except Exception as e:
            logger.warning("[LLM] primary health_check failed: %s", e)

    # 2. Check fallback health if primary is not responding
    if LLM_FALLBACK_API_KEY:
        fb_url = LLM_FALLBACK_BASE_URL.rstrip("/") + "/models"
        try:
            fb_headers = {"Authorization": f"Bearer {LLM_FALLBACK_API_KEY}"}
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(fb_url, headers=fb_headers)
                if resp.status_code == 200:
                    return True
                logger.warning("[LLM] fallback health_check status=%s", resp.status_code)
        except Exception as e:
            logger.warning("[LLM] fallback health_check failed: %s", e)

    return False


def get_status() -> dict[str, Any]:
    return {
        "base_url": LLM_BASE_URL,
        "fallback_base_url": LLM_FALLBACK_BASE_URL,
        "fallback_model": LLM_FALLBACK_MODEL,
        "healthy": health_check(),
        "api_key_configured": bool(
            NINEROUTER_API_KEY and NINEROUTER_API_KEY != "your_key_from_dashboard"
        ),
        "fallback_api_key_configured": bool(LLM_FALLBACK_API_KEY),
        "agent_models_r1": dict(LLM_MODEL_AGENT),
    }
