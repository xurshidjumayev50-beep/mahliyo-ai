import base64
import binascii
import os
import json
import sqlite3
import datetime
import re
import traceback
import uuid
import time
from flask import Flask, render_template, request, Response, jsonify, stream_with_context, send_from_directory, session
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
import requests
from werkzeug.security import check_password_hash, generate_password_hash

import generator

load_dotenv()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "meta-llama/llama-3.3-70b-instruct:free",
)
OPENROUTER_SYSTEM_PROMPT = (
    "Sen Mahliyo AI san. O'zbek tilida aniq, do'stona va tushunarli javob ber. "
    "Foydalanuvchi qaysi tilda yozsa, shu tilda javob ber."
)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or os.urandom(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW_SECONDS = 15 * 60
login_attempts = {}

DATA_DIR = os.environ.get("MAHLIYO_DATA_DIR")
DB_PATH = os.path.join(DATA_DIR, "mahliyo.db") if DATA_DIR else os.path.join(os.path.dirname(__file__), "mahliyo.db")
GENERATED_DIR = (
    os.path.join(DATA_DIR, "generated")
    if DATA_DIR
    else os.path.join(os.path.dirname(__file__), "static", "generated")
)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)
generator.GENERATED_DIR = GENERATED_DIR
MAX_IMAGE_BYTES = 5 * 1024 * 1024
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

DEFAULT_SYSTEM_PROMPT = (
    "Sen Mahliyo — O'zbekiston uchun maxsus ishlab chiqilgan ilg'or, aqlli, "
    "xushmuomala va samimiy sun'iy intellekt yordamchisisan. Foydalanuvchi qaysi tabiiy "
    "tilda yozsa, javobni o'sha tilda va yozuv tizimida ber; o'zbekcha yozsa o'zbekcha, "
    "kirill yozuvida yozsa kirillda javob ber. Boshqa tilga o'tishni foydalanuvchi so'ramasa, "
    "tilni almashtirma. Dasturlashda Python, JavaScript, TypeScript, Java, C, C++, C#, Go, "
    "Rust, PHP, Ruby, Swift, Kotlin, SQL, HTML va CSS kabi tillarda kod yoz, tahlil qil, "
    "xatolarni tuzat va kerak bo'lsa ishlashini tushuntir; kod blokining til belgisini to'g'ri qo'y. "
    "Har bir mavzuni: dasturlash, rasmiy xat va arizalar, "
    "slayd va taqdimotlar, universitet talabalari uchun mustaqil ishlar, "
    "fan va ta'lim bo'yicha professional darajada tushuntirib bera olasan. "
    "Foydalanuvchi taqdimot yoki mustaqil ish so'rasa, unga to'liq reja va matn yozib berasan."
)

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT,
            messages TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            user_id INTEGER REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    """)
    conversation_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(conversations)")
    }
    if "user_id" not in conversation_columns:
        cursor.execute("ALTER TABLE conversations ADD COLUMN user_id INTEGER REFERENCES users(id)")
    conn.commit()
    conn.close()

init_db()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None

    conn = get_db()
    user = conn.execute("SELECT id, email FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user is None:
        session.clear()
        return None
    return {"id": user["id"], "email": user["email"]}


def conversation_owner_clause():
    user = current_user()
    return ("user_id = ?", user["id"]) if user else ("user_id IS NULL", None)


def recent_login_attempts():
    now = time.time()
    ip_address = request.remote_addr or "unknown"
    recent_attempts = [
        attempted_at
        for attempted_at in login_attempts.get(ip_address, [])
        if now - attempted_at < LOGIN_ATTEMPT_WINDOW_SECONDS
    ]
    login_attempts[ip_address] = recent_attempts
    return ip_address, recent_attempts


def register_login_failure():
    ip_address, recent_attempts = recent_login_attempts()
    recent_attempts.append(time.time())
    login_attempts[ip_address] = recent_attempts


def gemini_api_error(response, operation="Gemini"):
    """Translate Gemini API failures into actionable messages without exposing credentials."""
    try:
        message = response.json().get("error", {}).get("message", "")
    except (ValueError, AttributeError):
        message = ""

    details = f" Tafsilot: {message}" if message else ""
    if response.status_code in (401, 403):
        return f"{operation} API kaliti noto'g'ri yoki unga ruxsat berilmagan. Sozlamalardan kalitni tekshiring.{details}"
    if response.status_code == 404:
        return f"Tanlangan Gemini modeli mavjud emas. Sozlamalardan mavjud Gemini modelini tanlang.{details}"
    if response.status_code == 429:
        return f"Gemini API so'rov limiti yoki kvotasi tugagan. Google AI Studio'dagi kvotani tekshiring.{details}"
    if response.status_code >= 500:
        return f"Google Gemini xizmati vaqtincha ishlamayapti. Birozdan keyin qayta urinib ko'ring.{details}"
    return f"{operation} so'rovni rad etdi (HTTP {response.status_code}). API sozlamalari va so'rovni tekshiring.{details}"


def call_gemini_api(
    api_key,
    messages,
    model_name="gemini-3.5-flash",
    system_prompt=None,
    system_prompt_only=False,
    max_output_tokens=2500,
    use_search=False,
    sources_out=None
):
    """Call Google Gemini API using REST endpoint"""
    if not model_name:
        model_name = "gemini-3.5-flash"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    
    contents = []
    system_instruction = "" if system_prompt_only else DEFAULT_SYSTEM_PROMPT
    if system_prompt:
        if system_prompt_only:
            system_instruction = system_prompt
        else:
            system_instruction += f"\n\nFoydalanuvchining qo'shimcha ko'rsatmasi:\n{system_prompt}"

    for m in messages:
        role = "user" if m.get("role") in ["user", "human"] else "model"
        text = m.get("content", "")
        parts = [{"text": text}]
        image = m.get("image")
        if image:
            parts.append({
                "inlineData": {
                    "mimeType": image["mime_type"],
                    "data": image["data"]
                }
            })
        contents.append({
            "role": role,
            "parts": parts
        })

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": max_output_tokens,
        }
    }
    if use_search:
        payload["tools"] = [{"google_search": {}}]

    try:
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            json=payload,
            timeout=60
        )
    except requests.RequestException as error:
        return None, f"Gemini xizmatiga ulanib bo'lmadi. Server internet/DNS ulanishini tekshiring. ({type(error).__name__})"
    
    if resp.status_code != 200:
        return None, gemini_api_error(resp)
        
    try:
        data = resp.json()
        candidate = data["candidates"][0]
        text = candidate["content"]["parts"][0]["text"]
        if use_search and sources_out is not None:
            sources_out.extend(extract_grounding_sources(candidate))
        return text, None
    except (ValueError, KeyError, IndexError, TypeError) as error:
        return None, f"Gemini javobini o'qib bo'lmadi: {error}"


def openrouter_client():
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None
    if not OPENROUTER_MODEL.endswith(":free"):
        raise ValueError("OPENROUTER_MODEL faqat :free modeli bo'lishi kerak.")
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def build_openrouter_messages(history, message, system_prompt=None):
    instruction = OPENROUTER_SYSTEM_PROMPT
    if isinstance(system_prompt, str) and system_prompt.strip():
        instruction += f"\n\nFoydalanuvchining qo'shimcha ko'rsatmasi:\n{system_prompt.strip()}"

    messages = [{"role": "system", "content": instruction}]
    for item in history[-8:]:
        if not isinstance(item, dict):
            continue
        content = item.get("content", "")
        if not isinstance(content, str) or not content:
            continue
        role = "user" if item.get("role") in ("user", "human") else "assistant"
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})
    return messages


def call_openrouter_api(history, message, system_prompt=None):
    try:
        client = openrouter_client()
        if client is None:
            return None, "OPENROUTER_API_KEY sozlanmagan."
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=build_openrouter_messages(history, message, system_prompt),
            temperature=0.7,
            max_tokens=2500,
        )
        reply = response.choices[0].message.content
        if isinstance(reply, str) and reply.strip():
            return reply, None
        return None, "OpenRouter bo'sh javob qaytardi."
    except (OpenAIError, ValueError, IndexError, AttributeError) as error:
        app.logger.warning("OpenRouter chat ishlamadi; Gemini fallback qo'llanadi (%s).", type(error).__name__)
        return None, f"OpenRouter chat ishlamadi ({type(error).__name__})."


def extract_grounding_sources(candidate):
    sources = []
    seen_urls = set()
    grounding = candidate.get("groundingMetadata", {})
    if not isinstance(grounding, dict):
        return sources
    for chunk in grounding.get("groundingChunks", []):
        if not isinstance(chunk, dict):
            continue
        web = chunk.get("web", {})
        if not isinstance(web, dict):
            continue
        title = web.get("title")
        url = web.get("uri")
        if (
            not isinstance(url, str)
            or len(url) > 2048
            or not url.startswith(("https://", "http://"))
            or url in seen_urls
        ):
            continue
        seen_urls.add(url)
        sources.append({
            "title": title[:300] if isinstance(title, str) and title else url,
            "url": url,
        })
    return sources


def gemini_stream_event(event, payload):
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def split_translation_text(text, max_length=5000):
        """Split long translations at whitespace while preserving the original text."""
        chunks = []
        current = ""
        for token in re.split(r"(\s+)", text):
            while len(token) > max_length:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(token[:max_length])
                token = token[max_length:]
            if len(current) + len(token) > max_length:
                chunks.append(current)
                current = ""
            current += token
        if current:
            chunks.append(current)
        return chunks


def generate_image(api_key, prompt):
    """Generate an image with Gemini and save it under the generated-files directory."""
    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key
            },
            json={
                "model": "gemini-3.1-flash-lite-image",
                "input": [{"type": "text", "text": prompt}],
                "store": False
            },
            timeout=120
        )
    except requests.RequestException as error:
        return None, f"Gemini bilan ulanishda xatolik: {error}"

    if response.status_code != 200:
        return None, gemini_api_error(response, "Gemini rasm yaratish")

    try:
        result = response.json()
        output = result.get("output", [])
        image = result.get("output_image")
        if not image:
            for item in output:
                if item.get("type") == "image":
                    image = item
                    break
                image = next(
                    (part for part in item.get("content", []) if part.get("type") == "image"),
                    None
                )
                if image:
                    break
        image_data = base64.b64decode(image["data"], validate=True)
        mime_type = image.get("mime_type", "image/png")
    except (AttributeError, KeyError, TypeError, ValueError, binascii.Error) as error:
        return None, f"Gemini javobidan rasmni o'qib bo'lmadi: {error}"

    extensions = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
    extension = extensions.get(mime_type)
    if not extension:
        return None, f"Gemini qo'llab-quvvatlanmaydigan rasm formatini qaytardi: {mime_type}"
    if not image_data or len(image_data) > 20 * 1024 * 1024:
        return None, "Gemini yaratgan rasm bo'sh yoki 20 MB limitidan katta."

    filename = f"generated_{uuid.uuid4().hex}.{extension}"
    with open(os.path.join(GENERATED_DIR, filename), "wb") as image_file:
        image_file.write(image_data)

    artifact = {
        "type": "image",
        "file_url": f"/download/{filename}",
        "filename": filename
    }
    output_text = result.get("output_text")
    if not isinstance(output_text, str):
        output_text = " ".join(
            item.get("text", "")
            for item in output
            if item.get("type") == "text" and isinstance(item.get("text"), str)
        )
    if output_text:
        artifact["reply"] = output_text
    return artifact, None


def is_image_generation_request(message):
    query = message.lower()
    phrases = (
        "rasm yarat", "rasm chiz", "rasm generatsiya", "rasm yasab",
        "rasmini chiz", "rasm qilib ber", "surat yarat", "surat chiz",
        "generate an image", "generate image", "create an image", "draw me",
        "draw a ", "make an image", "make me a picture", "нарисуй",
        "создай изображение", "сгенерируй изображение", "dibuja",
        "crée une image", "zeichne ein"
    )
    return any(phrase in query for phrase in phrases)


class ArtifactGenerationError(Exception):
    pass


def extract_spreadsheet_topic(query):
    topic = query.strip()
    phrases = (
        "excel jadval tuzib ber", "excel jadval yarat", "excel jadval tayyorla",
        "excel jadval", "excel", "xlsx", "jadval tuzib ber", "jadval tuz",
        "jadval yaratib ber", "jadval yarat", "jadval tayyorlab ber", "jadval",
        "menga", "iltimos", "mavzusida", "haqida", "bo'yicha", "bo‘yicha",
        "qilib ber", "tayyorlab ber", "yaratib ber", "tuzib ber", "tuz",
    )
    for phrase in phrases:
        topic = re.sub(rf"(?<!\w){re.escape(phrase)}(?!\w)", " ", topic, flags=re.IGNORECASE)
    return re.sub(r"[\s:;,.!?—–-]+", " ", topic).strip()


def generate_spreadsheet_artifact(query, api_key):
    topic = extract_spreadsheet_topic(query) or query.strip()
    if len(topic) > 500:
        topic = topic[:500]
    system_prompt = (
        "Create a useful spreadsheet structure for the requested topic. Return only valid JSON "
        "with this exact top-level shape: {\"sheets\":[{\"name\":\"Sheet name\","
        "\"columns\":[\"Column 1\"],\"rows\":[[\"value\"]]}]}. "
        "Use 1 to 5 sheets, clear Uzbek headers, and up to 30 informative rows per sheet. "
        "Each row must be an array with the same number of values as columns. Use JSON numbers "
        "for numeric data, not formatted strings. Do not include markdown fences or explanations."
    )
    result, error = call_gemini_api(
        api_key,
        [{"role": "user", "content": f"Excel jadval mavzusi: {topic}"}],
        system_prompt=system_prompt,
        system_prompt_only=True,
        max_output_tokens=8000,
    )
    if error or result is None:
        raise ArtifactGenerationError(error or "Gemini jadval ma'lumotlarini yaratolmadi.")

    json_text = result.strip()
    if json_text.startswith("```"):
        json_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", json_text, flags=re.IGNORECASE)
    try:
        json_decoder = json.JSONDecoder()
        start = json_text.find("{")
        if start < 0:
            raise ValueError("JSON obyekti topilmadi")
        spreadsheet_data, _ = json_decoder.raw_decode(json_text[start:])
    except (json.JSONDecodeError, ValueError) as error:
        raise ArtifactGenerationError(f"Gemini jadval JSON formatini qaytarmadi: {error}") from error

    sheets = spreadsheet_data.get("sheets") if isinstance(spreadsheet_data, dict) else None
    if not isinstance(sheets, list) or not sheets or len(sheets) > 5:
        raise ArtifactGenerationError("Gemini jadval uchun yaroqli varaqlar ro'yxatini qaytarmadi.")
    preview_sheets = []
    for sheet in sheets:
        if not isinstance(sheet, dict):
            raise ArtifactGenerationError("Gemini qaytargan jadval varag'i noto'g'ri.")
        name, columns, rows = sheet.get("name"), sheet.get("columns"), sheet.get("rows")
        if (
            not isinstance(name, str)
            or not isinstance(columns, list)
            or not 1 <= len(columns) <= 30
            or not all(isinstance(column, str) and column.strip() for column in columns)
            or not isinstance(rows, list)
            or len(rows) > 500
        ):
            raise ArtifactGenerationError("Gemini qaytargan jadval ustunlari yoki qatorlari noto'g'ri.")
        for row in rows:
            if (
                not isinstance(row, list)
                or len(row) != len(columns)
                or any(not isinstance(value, (str, int, float, bool, type(None))) for value in row)
            ):
                raise ArtifactGenerationError("Gemini qaytargan jadval qatori ustunlarga mos emas.")
        preview_sheets.append({
            "name": name,
            "columns": columns,
            "rows": rows[:10],
        })

    workbook_sheets = [
        {"name": sheet["name"], "columns": sheet["columns"], "rows": sheet["rows"]}
        for sheet in sheets
    ]
    xlsx_result = generator.generate_xlsx(topic, workbook_sheets)
    return {
        "type": "spreadsheet",
        "file_url": xlsx_result["download_url"],
        "filename": xlsx_result["filename"],
        "topic": topic,
        "sheets": preview_sheets,
    }


def check_and_generate_artifacts(query, api_key=None):
    """
    Checks if user is asking to create a presentation (slayd)
    or independent research paper (mustaqil ish / word doc),
    and generates the corresponding file!
    """
    q = query.lower()

    is_spreadsheet = any(k in q for k in ["excel", "xlsx", "jadval tuz", "jadval yarat"])
    # Presentation intent
    is_presentation = any(k in q for k in ["slayd", "taqdimot", "presentation", "pptx"])
    # Mustaqil ish or Word intent
    is_word_doc = any(k in q for k in ["mustaqil ish", "word", "docx", "referat", "kurs ishi", "maqola yoz"])

    # Extract topic
    topic = query.strip()
    for prefix in ["menga", "haqida", "mavzusida", "slayd qilib ber", "slayd tayyorlab ber", 
                   "mustaqil ish yozib ber", "mustaqil ish tayyorlab ber", "taqdimot tuz",
                   "taqdimot tayyorlab ber", "slayd rejasini tuz", "word korinishda"]:
        topic = topic.replace(prefix, "").strip()
    topic = topic.strip(":?., ")
    if len(topic) < 3:
        topic = "Zamonaviy Axborot Texnologiyalari"

    if is_spreadsheet:
        if not api_key or not api_key.strip():
            return None
        return generate_spreadsheet_artifact(query, api_key.strip())

    if is_presentation:
        pres_result = generator.generate_presentation(topic)
        return {
            "type": "presentation",
            "file_url": pres_result["download_url"],
            "filename": pres_result["filename"],
            "topic": topic,
            "slides": pres_result["slides"]
        }

    if is_word_doc:
        doc_result = generator.generate_mustaqil_ish_doc(topic)
        return {
            "type": "document",
            "file_url": doc_result["download_url"],
            "filename": doc_result["filename"],
            "topic": topic,
            "html_preview": doc_result["html_preview"]
        }

    return None


def missing_artifact_topic(query):
    """Return the requested artifact type when the user has not provided a subject."""
    lowered = query.lower()
    if any(word in lowered for word in ("excel", "xlsx", "jadval tuz", "jadval yarat")):
        artifact_type = "spreadsheet"
    elif any(word in lowered for word in ("slayd", "taqdimot", "presentation", "pptx")):
        artifact_type = "presentation"
    elif any(word in lowered for word in ("mustaqil ish", "word", "docx", "referat", "kurs ishi", "maqola yoz")):
        artifact_type = "document"
    else:
        return None

    topic = lowered
    command_phrases = (
        "excel jadval tuzib ber", "jadval tuzib ber", "excel jadval yarat",
        "excel jadval", "excel", "jadval tuz", "jadval yarat", "xlsx",
        "mustaqil ish", "kurs ishi", "maqola yoz", "taqdimot", "presentation",
        "slayd", "referat", "pptx", "docx", "word", "tayyorlab bering",
        "tayyorlab ber", "tayyorlab", "tayyorlang", "tayyorla", "yozib bering",
        "yozib ber", "yozib", "yoz", "qilib bering", "qilib ber", "qilib",
        "tuzib bering", "tuzib ber", "tuzib", "tuz", "bering", "ber",
        "menga", "iltimos", "haqida", "mavzusida", "bo'yicha", "bo‘yicha",
        "mavzuda", "biror mavzu", "qandaydir mavzu"
    )
    for phrase in command_phrases:
        topic = re.sub(rf"(?<!\w){re.escape(phrase)}(?!\w)", " ", topic)
    topic = re.sub(r"[\s:;,.!?—–-]+", " ", topic).strip()

    if len(topic) < 3 or topic in {"mavzu", "mavzu tanla", "istalgan mavzu"}:
        return artifact_type
    return None


def pending_artifact_from_history(history):
    """Find whether the latest assistant turn is asking the user for an artifact subject."""
    if not isinstance(history, list):
        return None
    for item in reversed(history):
        if not isinstance(item, dict) or item.get("role") != "assistant":
            continue
        content = str(item.get("content", "")).lower()
        if "qaysi mavzuda" in content and ("slayd" in content or "taqdimot" in content):
            return "presentation"
        if "qaysi mavzuda" in content and "mustaqil ish" in content:
            return "document"
        if "qaysi mavzuda" in content and ("excel" in content or "jadval" in content):
            return "spreadsheet"
        return None
    return None


def generate_smart_fallback(user_query, history=None):
    """
    Intelligent built-in fallback responder for Mahliyo AI.
    """
    q = user_query.strip().lower()

    if "slayd" in q or "taqdimot" in q:
        return (
            "### 📊 Taqdimot (Slayd) Muvaffaqiyatli Tayyorlandi!\n\n"
            "Siz so'ragan mavzu bo'yicha 16:9 formatdagi zamonaviy taqdimot fayli shakllantirildi. "
            "Quyida slaydlar tarkibi keltirilgan:\n\n"
            "1. **1-Slayd: Kirish va Sarlavha** — Mavzuning nomi va dolzarbligi.\n"
            "2. **2-Slayd: Taqdimot Rejasi** — Asosiy ko'riladigan masalalar.\n"
            "3. **3-Slayd: Muammoning Dolzarbligi** — Nima uchun bu mavzu muhim?\n"
            "4. **4-Slayd: Asosiy Vazifalar va Yechimlar** — Taklif etilayotgan innovatsiyalar.\n"
            "5. **5-Slayd: Kutilayotgan Natijalar** — Samaradorlik va tejamkorlik ko'rsatkichlari.\n"
            "6. **6-Slayd: Xulosa** — Xulosalar va e'tiboringiz uchun rahmat!\n\n"
            "> 📥 Slayd faylini (.pptx) yuklab olishingiz yoki quyidagi oynada ko'rishingiz mumkin."
        )

    if "mustaqil ish" in q or "word" in q or "referat" in q:
        return (
            "### 📄 Mustaqil Ish (Word Hujjati) Tayyorlandi!\n\n"
            "O'zbekiston Respublikasi OTM standartlariga (Times New Roman, 14pt, 1.5 interval, "
            "3cm chap hoshiya) to'liq mos keluvchi rasmiy **Mustaqil ish** hujjati shakllantirildi.\n\n"
            "**Hujjat tarkibi:**\n"
            "- **Titul varag'i:** Vazirlik, Universitet, Fakultet, Fan, Talaba va O'qituvchi ma'lumotlari.\n"
            "- **Mundarija (Reja):** Kirish, I-II-III boblar, Xulosa, Adabiyotlar ro'yxati.\n"
            "- **Kirish qismi:** Mavzuning dolzarbligi, maqsadi va vazifalari.\n"
            "- **Asosiy qism:** Nazariy tahlillar va samaradorlik jadvallari.\n"
            "- **Xulosa va Takliflar:** Ilmiy va amaliy xulosalar.\n"
            "- **Foydalanilgan Adabiyotlar:** Standart ilmiy manbalar.\n\n"
            "> 📥 Tayyor Word (.docx) faylini quyidagi tugma orqali yuklab olishingiz yoki to'g'ridan-to'g'ri o'qishingiz mumkin."
        )

    if "ariza" in q or "xat" in q or "rasmiy" in q:
        return (
            "### 📄 Rasmiy Ariza Namunasi\n\n"
            "```text\n"
            "                                     [Tashkilot / Universitet nomi] rahbari\n"
            "                                     [Ism, familiyasi]ga\n"
            "                                     [Foydalanuvchi F.I.Sh.]dan\n"
            "                                     Tel: +998 (__) ___-__-__\n\n"
            "                                 ARIZA\n\n"
            "    Men ushbu arizani yozishimdan maqsad shuki, [aniq sabab va holat bayoni]. \n\n"
            "    Yuqoridagilarni inobatga olgan holda, mening ushbu iltimosimni ijobiy\n"
            "hal qilib berishingizni so'rayman.\n\n"
            "Sana: [Kun.Oy.Yil]                          Imzo: ___________ [F.I.Sh.]\n"
            "```"
        )

    if "kod" in q or "xato" in q or "bug" in q:
        return (
            "### 💻 Kod tahlili va yordam\n\n"
            "Kodni tahlil qilish uchun uni yuboring. Keng tarqalgan xatoliklar:\n"
            "- `SyntaxError`: Belgilar yoki sintaksis xatosi.\n"
            "- `IndentationError`: Qator chekinishlari noto'g'ri.\n"
            "- `TypeError`: Ma'lumot turlari mos kelmasligi.\n\n"
            "Kodingizni yuborsangiz, darhol to'g'rilab, izoh bilan taqdim etaman!"
        )

    if "rekursiya" in q or "oddiy" in q:
        return (
            "### 🧠 Oddiy tushuntirish: Rekursiya va Iteratsiya\n\n"
            "- **Iteratsiya (Sikl):** Bir ishni navbatma-navbat takrorlash (masalan, zinapoyadan chiqish).\n"
            "- **Rekursiya:** Funksiya o'zini o'zi chaqirishi (masalan, Matryoshka qo'g'irchog'i — ichidan yana o'shanday kichikrog'i chiqadi).\n\n"
            "```python\n"
            "def faktorial(n):\n"
            "    if n <= 1: return 1\n"
            "    return n * faktorial(n - 1)\n"
            "```"
        )

    return (
        f"Salom! Men **Mahliyo AI** — sizning do'stona va aqlli yordamchingizman. 🌙\n\n"
        f"Menga nafaqat savol berishingiz, balki:\n"
        f"- 📊 **Taqdimot (Slayd)** tayyorlashni so'rashingiz (tayyor .pptx fayl);\n"
        f"- 📝 **Mustaqil ish** yozishni so'rashingiz (tayyor Word .docx fayl va ko'rish oynasi);\n"
        f"- 🎙️ **Ovozli xabar** yuborishingiz mumkin!\n\n"
        f"Bugun qanday vazifani bajaramiz?"
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Email va parol talab qilinadi"}), 400
    email = data.get("email", "")
    password = data.get("password", "")
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"error": "Email va parol matn ko'rinishida bo'lishi kerak"}), 400

    email = email.strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({"error": "To'g'ri email manzilini kiriting"}), 400
    if len(password) < 8 or len(password) > 128:
        return jsonify({"error": "Parol 8 dan 128 tagacha belgidan iborat bo'lishi kerak"}), 400

    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email, generate_password_hash(password), datetime.datetime.now().isoformat())
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Bu email bilan akkaunt allaqachon mavjud"}), 409
    conn.close()

    session.clear()
    session["user_id"] = user_id
    return jsonify({"authenticated": True, "user": {"id": user_id, "email": email}}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    ip_address, attempts = recent_login_attempts()
    if len(attempts) >= LOGIN_ATTEMPT_LIMIT:
        return jsonify({"error": "Juda ko'p urinish bo'ldi. 15 daqiqadan keyin qayta urinib ko'ring."}), 429

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Email yoki parol noto'g'ri"}), 400
    email = data.get("email", "")
    password = data.get("password", "")
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"error": "Email yoki parol noto'g'ri"}), 400

    conn = get_db()
    user = conn.execute(
        "SELECT id, email, password_hash FROM users WHERE email = ? COLLATE NOCASE",
        (email.strip(),)
    ).fetchone()
    conn.close()
    if not user or not check_password_hash(user["password_hash"], password):
        register_login_failure()
        return jsonify({"error": "Email yoki parol noto'g'ri"}), 401

    login_attempts.pop(ip_address, None)
    session.clear()
    session["user_id"] = user["id"]
    return jsonify({"authenticated": True, "user": {"id": user["id"], "email": user["email"]}})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"authenticated": False})


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user = current_user()
    return jsonify({"authenticated": user is not None, "user": user})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])
    api_key = os.environ.get("GEMINI_API_KEY") or data.get("api_key")
    model_name = "gemini-3.5-flash"
    system_prompt = data.get("system_prompt")
    image = data.get("image")

    if not message and not image:
        return jsonify({"error": "Xabar bo'sh bo'lishi mumkin emas"}), 400

    if image:
        if not isinstance(image, dict):
            return jsonify({"error": "Rasm ma'lumotlari noto'g'ri"}), 400
        mime_type = image.get("mime_type")
        image_data = image.get("data")
        if mime_type not in SUPPORTED_IMAGE_TYPES or not isinstance(image_data, str):
            return jsonify({"error": "Faqat JPEG, PNG yoki WebP rasmlari qo'llab-quvvatlanadi"}), 400
        try:
            decoded_image = base64.b64decode(image_data, validate=True)
        except (ValueError, binascii.Error):
            return jsonify({"error": "Rasm ma'lumotlarini o'qib bo'lmadi"}), 400
        if not decoded_image or len(decoded_image) > MAX_IMAGE_BYTES:
            return jsonify({"error": "Rasm bo'sh yoki 5 MB hajm limitidan katta"}), 400
        image = {"mime_type": mime_type, "data": image_data}

    if not message:
        message = "Biriktirilgan rasmni tahlil qil va undagi ma'lumotlarni tushuntir."

    pending_artifact = pending_artifact_from_history(history)
    if pending_artifact and message:
        if pending_artifact == "presentation":
            message = f"{message} mavzusida taqdimot tayyorlab ber"
        elif pending_artifact == "spreadsheet":
            message = f"{message} mavzusida Excel jadval tuzib ber"
        else:
            message = f"{message} mavzusida mustaqil ish yozib ber"

    if is_image_generation_request(message):
        if not api_key or not api_key.strip():
            return jsonify({
                "error": "Rasm yaratish va AI bilan suhbat uchun Gemini API kaliti kerak. ⚙️ Sozlamalarni ochib, Google AI Studio'dan olingan kalitni kiriting va saqlang."
            }), 401
        artifact, error = generate_image(api_key.strip(), message)
        if error:
            return jsonify({"error": error}), 502
        reply = artifact.pop("reply", None)
        if not reply:
            if any("\u0400" <= char <= "\u04ff" for char in message):
                reply = "Изображение готово."
            elif any(word in message.lower() for word in ("generate", "create", "draw", "make")):
                reply = "Your image is ready."
            else:
                reply = "Rasm tayyor."
        return jsonify({
            "reply": reply,
            "provider": "gemini",
            "model": "gemini-3.1-flash-lite-image",
            "artifact": artifact
        })

    missing_topic = missing_artifact_topic(message)
    if missing_topic == "presentation":
        return jsonify({
            "reply": "Albatta! Slayd yoki taqdimotni qaysi mavzuda tayyorlay? Masalan: “Sun'iy intellekt va uning kelajagi”.",
            "provider": "mahliyo-local",
            "model": "mahliyo-core-v1",
            "artifact": None,
            "needs_topic": True
        })
    if missing_topic == "document":
        return jsonify({
            "reply": "Albatta! Mustaqil ishni qaysi mavzuda tayyorlay? Masalan: “O'zbekistonda qayta tiklanuvchi energiya manbalari”.",
            "provider": "mahliyo-local",
            "model": "mahliyo-core-v1",
            "artifact": None,
            "needs_topic": True
        })
    if missing_topic == "spreadsheet":
        return jsonify({
            "reply": "Albatta! Excel jadvalni qaysi mavzuda tuzay? Masalan: “Oylik daromad va xarajatlar”.",
            "provider": "mahliyo-local",
            "model": "mahliyo-core-v1",
            "artifact": None,
            "needs_topic": True
        })

    # Check if user needs presentation or word doc generated
    try:
        artifact = check_and_generate_artifacts(message, api_key)
    except ArtifactGenerationError as error:
        return jsonify({"error": str(error)}), 502

    use_search = artifact is None and not image and data.get("use_search") is True
    if artifact is None and not image and not use_search:
        reply, _ = call_openrouter_api(history, message, system_prompt)
        if reply:
            return jsonify({
                "reply": reply,
                "provider": "openrouter",
                "model": OPENROUTER_MODEL,
                "artifact": None,
                "sources": [],
            })

    if not api_key or not api_key.strip():
        if image:
            return jsonify({
                "error": "Rasmni tahlil qilish va AI bilan suhbat uchun Gemini API kaliti kerak. ⚙️ Sozlamalarni ochib, Google AI Studio'dan olingan kalitni kiriting va saqlang."
            }), 401
        if artifact is None:
            return jsonify({
                "error": "AI bilan suhbat uchun Gemini API kaliti sozlanmagan. ⚙️ Sozlamalarni oching, Google AI Studio'dan olingan kalitni kiriting va saqlang."
            }), 401
        return jsonify({
            "reply": generate_smart_fallback(message, history),
            "provider": "mahliyo-local",
            "model": "mahliyo-core-v1",
            "artifact": artifact
        })

    formatted_messages = []
    for h in history[-8:]:
        formatted_messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    formatted_messages.append({"role": "user", "content": message, "image": image})

    sources = []
    reply, err = call_gemini_api(
        api_key.strip(),
        formatted_messages,
        model_name,
        system_prompt,
        use_search=use_search,
        sources_out=sources,
    )
    if reply:
        return jsonify({
            "reply": reply,
            "provider": "gemini",
            "model": model_name,
            "artifact": artifact,
            "sources": sources,
        })

    return jsonify({"error": err or "Gemini'dan javob olib bo'lmadi."}), 502


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "So'rov ma'lumotlari noto'g'ri"}), 400

    message = data.get("message", "")
    history = data.get("history", [])
    if not isinstance(message, str) or not isinstance(history, list):
        return jsonify({"error": "Xabar yoki suhbat tarixi noto'g'ri"}), 400
    message = message.strip()

    artifact_intents = (
        "slayd", "taqdimot", "presentation", "pptx", "mustaqil ish",
        "word", "docx", "referat", "kurs ishi", "maqola yoz",
        "excel", "xlsx", "jadval tuz", "jadval yarat",
    )
    if (
        data.get("image")
        or data.get("images")
        or is_image_generation_request(message)
        or any(intent in message.lower() for intent in artifact_intents)
        or pending_artifact_from_history(history)
    ):
        return jsonify({"fallback_required": True})

    if not message:
        return jsonify({"error": "Xabar bo'sh bo'lishi mumkin emas"}), 400

    system_prompt = data.get("system_prompt")
    if not isinstance(system_prompt, str):
        system_prompt = ""

    use_search = data.get("use_search") is True
    if use_search:
        return jsonify({"fallback_required": True})

    try:
        client = openrouter_client()
        if client is None:
            return jsonify({"fallback_required": True})
        upstream = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=build_openrouter_messages(history, message, system_prompt),
            temperature=0.7,
            max_tokens=2500,
            stream=True,
        )
    except (OpenAIError, ValueError) as error:
        app.logger.warning("OpenRouter oqimi ishlamadi; Gemini fallback qo'llanadi (%s).", type(error).__name__)
        return jsonify({"fallback_required": True})

    def generate_events():
        received_text = False
        try:
            for chunk in upstream:
                if not chunk.choices:
                    continue
                text = chunk.choices[0].delta.content
                if isinstance(text, str) and text:
                    received_text = True
                    yield gemini_stream_event("chunk", {"text": text})
            if received_text:
                yield gemini_stream_event("done", {})
            else:
                yield gemini_stream_event("error", {"error": "OpenRouter bo'sh javob qaytardi."})
        except OpenAIError as error:
            app.logger.warning("OpenRouter oqimi uzildi; Gemini fallback qo'llanadi (%s).", type(error).__name__)
            yield gemini_stream_event(
                "error",
                {"error": "OpenRouter oqimi uzildi."}
            )
        finally:
            upstream.close()

    return Response(
        stream_with_context(generate_events()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/translate", methods=["POST"])
def translate():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Tarjima so'rovi noto'g'ri"}), 400

    text = data.get("text")
    source = data.get("source", "auto")
    target = data.get("target")
    languages = {
        "uz-Latn": "O'zbek tili (lotin yozuvi)",
        "uz-Cyrl": "O'zbek tili (kirill yozuvi)",
        "en": "Ingliz tili",
        "ru": "Rus tili",
        "tr": "Turk tili",
    }
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "Tarjima uchun matn kiriting"}), 400
    if not isinstance(source, str) or (source != "auto" and source not in languages):
        return jsonify({"error": "Manba til noto'g'ri tanlangan"}), 400
    if not isinstance(target, str) or target not in languages:
        return jsonify({"error": "Tarjima tilini tanlang"}), 400

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Tarjima uchun serverda Gemini API kaliti sozlanmagan"}), 401

    source_language = "matn tilini avtomatik aniqlang" if source == "auto" else languages[source]
    target_language = languages[target]
    system_prompt = (
        f"Translate the user's text from {source_language} into {target_language}. "
        "Return only the translation. Do not add explanations, quotation marks, labels, "
        "or any other text. Preserve the original meaning, tone, style, formatting, and line breaks. "
        "For conversions between Uzbek Latin and Cyrillic, use correct Uzbek orthography, "
        "including the Uzbek apostrophe letters o' and g' and the digraphs sh and ch; "
        "transliterate Uzbek letters accurately."
    )
    translated_chunks = []
    for chunk in split_translation_text(text):
        leading_space = chunk[:len(chunk) - len(chunk.lstrip())]
        content_end = len(chunk.rstrip())
        content = chunk[len(leading_space):content_end]
        trailing_space = chunk[content_end:]
        if not content:
            translated_chunks.append(chunk)
            continue
        translation, error = call_gemini_api(
            api_key,
            [{"role": "user", "content": content}],
            system_prompt=system_prompt,
            system_prompt_only=True,
        )
        if error or translation is None:
            return jsonify({"error": error or "Matnni tarjima qilib bo'lmadi"}), 502
        translated_chunks.append(f"{leading_space}{translation}{trailing_space}")

    return jsonify({
        "translation": "".join(translated_chunks),
        "source": source,
        "target": target,
    })


@app.route("/api/generate/slide", methods=["POST"])
def api_generate_slide():
    data = request.get_json() or {}
    topic = data.get("topic", "Zamonaviy Axborot Texnologiyalari").strip()
    result = generator.generate_presentation(topic)
    return jsonify(result)


@app.route("/api/generate/document", methods=["POST"])
def api_generate_document():
    data = request.get_json() or {}
    topic = data.get("topic", "Sun'iy intellekt texnologiyalari").strip()
    subject = data.get("subject", "Axborot Texnologiyalari")
    student = data.get("student", "Talaba")
    teacher = data.get("teacher", "O'qituvchi")
    university = data.get("university", "O'zbekiston Milliy Universiteti")

    result = generator.generate_mustaqil_ish_doc(
        topic=topic,
        subject=subject,
        student=student,
        teacher=teacher,
        university=university
    )
    return jsonify(result)


@app.route("/download/<path:filename>")
def download_file(filename):
    """Download generated presentations and word documents"""
    return send_from_directory(GENERATED_DIR, filename, as_attachment=True)


@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    conn = get_db()
    user = current_user()
    if user:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations "
            "WHERE user_id = ? ORDER BY updated_at DESC",
            (user["id"],)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations "
            "WHERE user_id IS NULL ORDER BY updated_at DESC"
        ).fetchall()
    conn.close()
    
    chats = []
    for r in rows:
        chats.append({
            "id": r["id"],
            "title": r["title"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"]
        })
    return jsonify(chats)


@app.route("/api/conversations/<cid>", methods=["GET"])
def get_conversation(cid):
    conn = get_db()
    user = current_user()
    if user:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
            (cid, user["id"])
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ? AND user_id IS NULL",
            (cid,)
        ).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Suhbat topilmadi"}), 404

    return jsonify({
        "id": row["id"],
        "title": row["title"],
        "messages": json.loads(row["messages"]) if row["messages"] else [],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    })


@app.route("/api/conversations", methods=["POST"])
def save_conversation():
    data = request.get_json() or {}
    cid = data.get("id")
    title = data.get("title", "Yangi suhbat")
    messages = json.dumps(data.get("messages", []))
    if not isinstance(cid, str) or not cid:
        return jsonify({"error": "Suhbat identifikatori noto'g'ri"}), 400
    now = datetime.datetime.now().isoformat()
    user = current_user()
    user_id = user["id"] if user else None

    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO conversations (id, title, messages, created_at, updated_at, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            messages = excluded.messages,
            updated_at = excluded.updated_at
        WHERE conversations.user_id IS excluded.user_id
    """, (cid, title, messages, now, now, user_id))
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Suhbat topilmadi yoki unga kirish huquqi yo'q"}), 404
    conn.commit()
    conn.close()

    return jsonify({"status": "saved", "id": cid, "title": title})


@app.route("/api/conversations/<cid>", methods=["DELETE"])
def delete_conversation(cid):
    conn = get_db()
    user = current_user()
    if user:
        cursor = conn.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (cid, user["id"])
        )
    else:
        cursor = conn.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id IS NULL",
            (cid,)
        )
    conn.commit()
    conn.close()
    if cursor.rowcount == 0:
        return jsonify({"error": "Suhbat topilmadi"}), 404
    return jsonify({"status": "deleted", "id": cid})


@app.route("/api/test-key", methods=["POST"])
def test_key():
    data = request.get_json() or {}
    api_key = (os.environ.get("GEMINI_API_KEY") or data.get("api_key", "")).strip()
    if not api_key:
        return jsonify({"valid": False, "error": "Kalit kiritilmagan"}), 400

    try:
        r = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": api_key},
            timeout=10
        )
        if r.status_code == 200:
            return jsonify({"valid": True, "message": "Gemini API kaliti to'g'ri ishlamoqda!"})
        else:
            return jsonify({"valid": False, "error": gemini_api_error(r, "Gemini API kaliti")}), 400
    except requests.RequestException as error:
        return jsonify({
            "valid": False,
            "error": f"Gemini xizmatiga ulanib bo'lmadi. Server internet/DNS ulanishini tekshiring. ({type(error).__name__})"
        }), 502


@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "app": "Mahliyo AI",
        "version": "1.4.0",
        "features": [
            "Chat", "Image understanding", "Image generation", "Programming assistance",
            "Language matching", "Presentation PPTX", "Word DOCX",
            "Voice Recognition", "Speech Synthesis"
        ],
        "timestamp": datetime.datetime.now().isoformat()
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
