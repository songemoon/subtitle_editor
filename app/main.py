import os
from openai import OpenAI
from dotenv import load_dotenv
import nltk
nltk.download('punkt')
from nltk.tokenize import sent_tokenize
import re
from sqlalchemy import text

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def translate_text(text, target_lang="English"):
    prompt = f"Translate the following Korean subtitles into natural {target_lang}:\n\n{text}"

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

def parse_srt(content):
    pattern = re.compile(r"(\d+)\n([\d:,]+ --> [\d:,]+)\n(.+?)(?=\n\n|\Z)", re.DOTALL)
    matches = pattern.findall(content)

    subtitles = []
    for number, timestamp, text in matches:
        lines = text.strip().split("\n")
        merged_text = " ".join(line.strip() for line in lines)
        subtitles.append({
            "index": number,
            "timestamp": timestamp,
            "text": merged_text
        })
    return subtitles

def extract_sentences_from_srt(content):
    """SRT에서 텍스트만 뽑아 문장 단위로 나누는 함수"""
    subtitles = parse_srt(content)
    full_text = " ".join([s["text"] for s in subtitles])
    sentences = sent_tokenize(full_text)
    return sentences

def translate_sentences(sentences, client_id=None, target_lang="English"):
    from app.db import get_db_connection

    glossary_prompt = ""
    if client_id:
        conn = get_db_connection()
        glossary = conn.execute(
            text("SELECT korean, english FROM glossaries WHERE client_id = :client_id"),
            {"client_id": client_id}
        ).fetchall()
        conn.close()

        if glossary:
            glossary_prompt = "\n다음 용어는 반드시 반영해서 번역하세요:\n"
            for term in glossary:
                glossary_prompt += f"- {term['korean']} → {term['english']}\n"

    translated = []

    for i, sentence in enumerate(sentences, 1):
        print(f"[{i}/{len(sentences)}] 번역 중: {sentence}")

        prompt = f"""{glossary_prompt}

You are a professional subtitle translator.
Translate the following Korean sentence into fluent and natural {target_lang}, preserving the original tone, emotion, and nuance as much as possible.
If the sentence includes informal expressions, slang, or emotional delivery, reflect that appropriately in English.
Use clear and concise phrasing suitable for on-screen subtitles. Do not translate word-for-word; prioritize conveying the meaning and tone.
Do not explain or comment on the sentence. Only return the translated English subtitle.

Korean:
{sentence}

English:"""


        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        translated_text = response.choices[0].message.content.strip()
        translated.append(translated_text)

    return translated


def rebuild_srt(subtitles, translated_sentences):
    new_srt = ""

    for i, subtitle in enumerate(subtitles):
        index = subtitle["index"]
        timestamp = subtitle["timestamp"]
        translated_text = translated_sentences[i] if i < len(translated_sentences) else ""

        new_srt += f"{index}\n{timestamp}\n{translated_text}\n\n"

    return new_srt
