"""Turns a prediction into a short, manager-friendly retention summary with OpenAI."""
import json

from openai import OpenAI

from app.config import OPENAI_MODEL, OPENAI_TIMEOUT_SECONDS, openai_key

SYSTEM = (
    "You are an HR analytics assistant at PROITBRIDGE. You explain an employee attrition-risk "
    "prediction to an HR manager in plain, kind, professional English. Use only the facts given. "
    "Never invent personal details, never judge the employee, and never suggest firing or punishment. "
    'Reply as JSON: {"summary": "<two sentences>", "actions": ["<action 1>", "<action 2>", "<action 3>"]}. '
    "Each action is one short, practical retention step tied to a listed driver."
)


class AIUnavailable(Exception):
    """Raised when the OpenAI key is missing."""


def ai_enabled():
    return bool(openai_key())


def explain(employee, prediction):
    if not ai_enabled():
        raise AIUnavailable("AI summary is off: OPENAI_API_KEY is not set.")
    raises = [f"{d['label']}: {d['value']}" for d in prediction["drivers"] if d["impact"] > 0][:3]
    lowers = [f"{d['label']}: {d['value']}" for d in prediction["drivers"] if d["impact"] < 0][:2]
    facts = {
        "attrition_risk": f"{prediction['risk_percent']}% ({prediction['band']})",
        "department": employee["department"],
        "drivers_raising_risk": raises,
        "drivers_lowering_risk": lowers,
    }
    client = OpenAI(api_key=openai_key(), timeout=OPENAI_TIMEOUT_SECONDS, max_retries=1)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": json.dumps(facts)}],
    )
    data = json.loads(response.choices[0].message.content or "{}")
    summary = str(data.get("summary", "")).strip()
    actions = [str(a).strip() for a in data.get("actions", []) if str(a).strip()][:3]
    if not summary or not actions:
        raise ValueError("The AI reply was empty.")
    return {"summary": summary, "actions": actions, "model": OPENAI_MODEL}
