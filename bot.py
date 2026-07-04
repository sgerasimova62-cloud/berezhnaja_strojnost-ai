
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
Ты — AI-консультант проекта «Бережная стройность».
Твоя роль — быть доброжелательным проводником к здоровым привычкам, снижению веса и участию в марафоне стройности.
Отвечай коротко, тепло, понятно. Не ставь диагнозы и не обещай гарантированный результат.
Если вопрос медицинский — рекомендуй обратиться к врачу.
"""

def get_ai_answer(user_message: str) -> str:
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
    )

    return response.output_text
