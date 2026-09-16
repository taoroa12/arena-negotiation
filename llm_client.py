import os
import json
import random
import requests
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "mock")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")


def build_system_prompt(scenario):
    return (
        f"Ты — участник деловых переговоров. Сфера: {scenario.sphere}. "
        f"Тема переговоров: {scenario.topic}. Твоя роль: {scenario.opponent_role}. "
        f"Твои цели в переговорах: {scenario.opponent_goals}. "
        f"Тон общения: {scenario.tone}. Сложность оппонента: {scenario.difficulty}. "
        f"Контекст ситуации: {scenario.context_description}. "
        f"Веди диалог от первого лица, реалистично отстаивай свои интересы, "
        f"не соглашайся на невыгодные условия сразу, отвечай коротко (2-4 предложения)."
    )


def get_opponent_reply(scenario, history):
    try:
        if PROVIDER == "gemini":
            return _gemini_reply(scenario, history)
        if PROVIDER == "yandex":
            return _yandex_reply(scenario, history)
    except Exception as e:
        print(f"[LLM ERROR] {e}, переключаюсь на офлайн-режим")
    return _mock_reply(scenario, history)


def _gemini_reply(scenario, history):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    contents = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
        for m in history
    ]
    body = {
        "system_instruction": {"parts": [{"text": build_system_prompt(scenario)}]},
        "contents": contents,
    }
    resp = requests.post(
        url,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json=body,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _yandex_reply(scenario, history):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    messages = [{"role": "system", "text": build_system_prompt(scenario)}]
    for m in history:
        messages.append({"role": "user" if m["role"] == "user" else "assistant", "text": m["content"]})
    body = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {"stream": False, "temperature": 0.6, "maxTokens": 300},
        "messages": messages,
    }
    resp = requests.post(
        url,
        headers={"Authorization": f"Api-Key {YANDEX_API_KEY}", "Content-Type": "application/json"},
        json=body,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["result"]["alternatives"][0]["message"]["text"].strip()


_MOCK_REPLIES = {
    "жёсткий": ["Мне это не подходит, предложите условия лучше.",
                "Это не то, на что я рассчитывал(а). Что ещё вы можете предложить?"],
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
    except Exception as e:
        print(f"[LLM ERROR] {e}, офлайн-разбор")
    return _mock_feedback(history)


def _gemini_feedback(scenario, history):
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    prompt = (
        f"Проанализируй переговоры по сценарию '{scenario.title}'.\n{transcript}\n\n"
        "Верни ТОЛЬКО валидный JSON без markdown-разметки в формате: "
        '{"summary": "...", "strengths": "...", "weaknesses": "...", '
        '"score_goal": 0-10, "score_argumentation": 0-10, "score_empathy": 0-10, "score_tactics": 0-10}'
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    resp = requests.post(
        url,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json=body,
        timeout=20,
    )
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def _mock_feedback(history):
    user_msgs = [m for m in history if m["role"] == "user"]
    return {
        "summary": "Автоматический разбор (офлайн-режим): переговоры завершены.",
        "strengths": "Вы участвовали в диалоге и предлагали аргументы.",
        "weaknesses": "Подключите LLM-провайдера для детального разбора формулировок.",
        "score_goal": 5,
        "score_argumentation": min(10, len(user_msgs)),
        "score_empathy": 5,
        "score_tactics": 5,
    }   