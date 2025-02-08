import json
from CONSTS import BASE_URL, API_KEY, MAX_TOKENS_IN_MESSAGE, SYSTEM_PROMPTS
import requests
from openai import OpenAI
from io import BytesIO
from converter import convert_rb_to_wav
import logging
client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)


def ask_gpt(messages, model, system_prompt):
    chat_completion = client.chat.completions.create(
        messages=[
            {
                'role': 'system',
                'content': SYSTEM_PROMPTS[system_prompt][0],
            }
        ] + messages,
        model=model,
        max_tokens=MAX_TOKENS_IN_MESSAGE
    )
    try:
        answer = chat_completion.choices[0].message.content
        tokens_in_answer = chat_completion.usage.total_tokens
        return True, answer, tokens_in_answer

    except Exception as e:
        print(e)
        return False, "Ошибка при обращении к GPT",  None


def transcript_audio(audio):

    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio
    )
    return transcript.text
