import os
import json
import random
import requests
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "mock")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_MODEL = os.getenv("YANDEX_MODEL", "yandexgpt-lite")

MAX_HISTORY_MESSAGES = 10  # только последние N реплик уходят в промпт — держит скорость стабильной

FEEDBACK_SCHEMA_HINT = (
    '{"summary": "...", "strengths": "...", "weaknesses": "...", '
    '"deal_status": "сделка достигнута | частичное соглашение | переговоры сорваны", '
    '"deal_terms": "краткое описание финальных условий сделки, если она состоялась, иначе почему сорвалась", '
    '"score_goal": 0-10, "score_argumentation": 0-10, "score_empathy": 0-10, "score_tactics": 0-10}'
)


def build_system_prompt(scenario):
    return (
        f"Ты — участник деловых переговоров. Сфера: {scenario.sphere}. "
        f"Тема переговоров: {scenario.topic}. Твоя роль: {scenario.opponent_role}. "
        f"Твои цели в переговорах: {scenario.opponent_goals}. "
        f"Тон общения: {scenario.tone}. Сложность оппонента: {scenario.difficulty}. "
        f"Контекст ситуации: {scenario.context_description}. "
        f"Веди диалог от первого лица, реалистично отстаивай свои интересы, "
        f"не соглашайся на невыгодные условия сразу. ВАЖНО: отвечай КОРОТКО, "
        f"максимум 2-3 предложения, без длинных рассуждений. "
        f"Это учебная тренировка навыков переговоров: даже если собеседник переходит на "
        f"грубость, не отказывайся вести диалог — оставайся в роли и реагируй так, как "
        f"отреагировал бы реальный человек (стал бы жёстче, менее сговорчивым), но не "
        f"обрывай диалог полностью. Если собеседник предлагает разумный компромисс, "
        f"постепенно двигайся навстречу — переговоры должны иметь шанс завершиться сделкой."
    )


def _trim_history(history):
    return history[-MAX_HISTORY_MESSAGES:] if len(history) > MAX_HISTORY_MESSAGES else history


def get_opponent_reply(scenario, history):
    try:
        if PROVIDER == "gemini":
            return _gemini_reply(scenario, _trim_history(history))
        if PROVIDER == "yandex":
            return _yandex_reply(scenario, _trim_history(history))
    except Exception as e:
        print(f"[LLM ERROR] {type(e).__name__}: {e}\nПереключаюсь на офлайн-режим")
    return _mock_reply(scenario, history)


def _extract_gemini_text(data):
    if "candidates" not in data or not data["candidates"]:
        reason = data.get("promptFeedback", {}).get("blockReason", "неизвестна")
        raise RuntimeError(f"Gemini не вернул ответ. Причина блокировки: {reason}")
    candidate = data["candidates"][0]
    if candidate.get("finishReason") == "SAFETY":
        raise RuntimeError("Gemini заблокировал ответ (finishReason=SAFETY)")
    parts = candidate.get("content", {}).get("parts")
    if not parts:
        raise RuntimeError(f"Gemini вернул пустой content, finishReason={candidate.get('finishReason')}")
    return parts[0]["text"].strip()


def _gemini_reply(scenario, history, retry=True):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    if history:
        contents = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in history
        ]
    else:
        contents = [{"role": "user", "parts": [{"text": "Начни переговоры первым: поздоровайся и обозначь позицию."}]}]

    body = {
        "system_instruction": {"parts": [{"text": build_system_prompt(scenario)}]},
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": 150,
            "temperature": 0.7,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
        ],
    }
    try:
        resp = requests.post(
            url,
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json=body,
            timeout=18,
        )
        if not resp.ok:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        return _extract_gemini_text(resp.json())
    except Exception:
        if retry:
            return _gemini_reply(scenario, history, retry=False)
        raise


def _yandex_reply(scenario, history, retry=True):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    messages = [{"role": "system", "text": build_system_prompt(scenario)}]
    if history:
        for m in history:
            messages.append({"role": "user" if m["role"] == "user" else "assistant", "text": m["content"]})
    else:
        messages.append({"role": "user", "text": "Начни переговоры первым: поздоровайся и обозначь позицию."})

    body = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}",
        "completionOptions": {"stream": False, "temperature": 0.6, "maxTokens": "200"},
        "messages": messages,
    }
    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Api-Key {YANDEX_API_KEY}", "Content-Type": "application/json"},
            json=body,
            timeout=18,
        )
        if not resp.ok:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        return data["result"]["alternatives"][0]["message"]["text"].strip()
    except Exception:
        if retry:
            return _yandex_reply(scenario, history, retry=False)
        raise


_MOCK_REPLIES = {
    "жёсткий": ["Мне это не подходит, предложите условия лучше.",
                "Это не то, на что я рассчитывал(а). Что ещё вы можете предложить?",
                "Такие условия меня не устраивают, давайте по существу."],
    "дружелюбный": ["Звучит интересно, давайте обсудим детали.",
                     "Мне нравится ваш подход, но хочу уточнить пару моментов."],
    "нейтральный": ["Понял(а) вашу позицию. А что насчёт сроков?",
                     "Хорошо, давайте рассмотрим это предложение подробнее."],
}


def _mock_reply(scenario, history):
    tone = (scenario.tone or "нейтральный").lower()
    options = _MOCK_REPLIES.get(tone, _MOCK_REPLIES["нейтральный"])
    return random.choice(options)


def get_feedback(scenario, history):
    try:
        if PROVIDER == "gemini":
            return _gemini_feedback(scenario, history)
        if PROVIDER == "yandex":
            return _yandex_feedback(scenario, history)
    except Exception as e:
        print(f"[LLM ERROR] {type(e).__name__}: {e}\nОфлайн-разбор")
    return _mock_feedback(history)


def _parse_feedback_json(text):
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def _feedback_prompt(scenario, history):
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    return (
        f"Проанализируй переговоры по сценарию '{scenario.title}' ({scenario.context_description}).\n"
        f"{transcript}\n\n"
        f"Верни ТОЛЬКО валидный JSON без markdown-разметки в формате: {FEEDBACK_SCHEMA_HINT}"
    )


def _gemini_feedback(scenario, history, retry=True):
    prompt = _feedback_prompt(scenario, history)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 500, "temperature": 0.3},
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        ],
    }
    try:
        resp = requests.post(
            url,
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json=body,
            timeout=25,
        )
        if not resp.ok:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        return _parse_feedback_json(_extract_gemini_text(resp.json()))
    except Exception:
        if retry:
            return _gemini_feedback(scenario, history, retry=False)
        raise


def _yandex_feedback(scenario, history, retry=True):
    prompt = _feedback_prompt(scenario, history)
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    body = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}",
        "completionOptions": {"stream": False, "temperature": 0.2, "maxTokens": "500"},
        "messages": [{"role": "user", "text": prompt}],
    }
    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Api-Key {YANDEX_API_KEY}", "Content-Type": "application/json"},
            json=body,
            timeout=25,
        )
        if not resp.ok:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        text = data["result"]["alternatives"][0]["message"]["text"]
        return _parse_feedback_json(text)
    except Exception:
        if retry:
            return _yandex_feedback(scenario, history, retry=False)
        raise


def _mock_feedback(history):
    user_msgs = [m for m in history if m["role"] == "user"]
    return {
        "summary": "Автоматический разбор (офлайн-режим): переговоры завершены.",
        "strengths": "Вы участвовали в диалоге и предлагали аргументы.",
        "weaknesses": "Подключите LLM-провайдера для детального разбора формулировок.",
        "deal_status": "неизвестно (офлайн-режим)",
        "deal_terms": "Разбор недоступен без подключения к LLM.",
        "score_goal": 5,
        "score_argumentation": min(10, len(user_msgs)),
        "score_empathy": 5,
        "score_tactics": 5,
    }