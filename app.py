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
from urllib.parse import quote
from flask import Flask, render_template, request, Response, jsonify, stream_with_context, send_from_directory, session, g
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
import requests
from werkzeug.security import check_password_hash, generate_password_hash

import generator

load_dotenv()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free",
)
OPENROUTER_IMAGE_MODEL = os.getenv("OPENROUTER_IMAGE_MODEL", "google/gemini-3.1-flash-image")
OPENROUTER_VIDEO_MODEL = os.getenv("OPENROUTER_VIDEO_MODEL", "google/veo-3.1-lite")
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
DEFAULT_DAILY_AI_LIMIT = 10000
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
    "Sen Mahliyo AI, o'zbek tilidagi akademik yordamchisan. Talabalar uchun mavzuga mos, "
    "faktlarga tayangan slayd va mustaqil ish tayyorlaysan. Foydalanuvchi boshqa tilni so'ramasa, "
    "javobni o'zbek tilida, lotin yozuvida ber. Mavzu aniq bo'lmasa, faqat bitta qisqa savol ber; "
    "aniq bo'lsa, qo'shimcha savol bermasdan ishni bajar. Hech qachon shablon, bo'sh joy, "
    "qavs ichidagi to'ldirish ko'rsatmasi, ko'p nuqta yoki mavzuga aloqasiz umumiy matn qoldirma. "
    "Ism berilmagan bo'lsa titulda 'Bajardi: Talaba' deb yoz; boshqa maydonlar uchun uydirma ism "
    "yoki guruh yaratma. Aniq fakt, sana, raqam va misollarni faqat ishonchli bo'lsa keltir; "
    "tadqiqot natijasi yoki manba nomini to'qib chiqarmagin. Manbani tasdiqlay olmasang, uni "
    "haqiqiy manba sifatida ko'rsatma. Akademik topshiriqlarda tilni ravon, izchil va mavzuga "
    "xos saqla. Dasturlashda Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Rust, PHP, "
    "Ruby, Swift, Kotlin, SQL, HTML va CSS tillarida kod yoz, tahlil qil va xatolarni tuzat."
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_ai_usage (
            usage_date TEXT PRIMARY KEY,
            request_count INTEGER NOT NULL DEFAULT 0
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


def configured_daily_ai_limit():
    try:
        return max(1, int(os.getenv("DAILY_AI_LIMIT", str(DEFAULT_DAILY_AI_LIMIT))))
    except ValueError:
        return DEFAULT_DAILY_AI_LIMIT


def reserve_daily_ai_request():
    usage_date = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    limit = configured_daily_ai_limit()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT request_count FROM daily_ai_usage WHERE usage_date = ?",
            (usage_date,),
        ).fetchone()
        used = row[0] if row else 0
        if used >= limit:
            conn.rollback()
            return False, usage_date, used, limit
        conn.execute(
            "INSERT INTO daily_ai_usage (usage_date, request_count) VALUES (?, 1) "
            "ON CONFLICT(usage_date) DO UPDATE SET request_count = request_count + 1",
            (usage_date,),
        )
        conn.commit()
        return True, usage_date, used + 1, limit
    finally:
        conn.close()


def release_daily_ai_request(usage_date):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE daily_ai_usage SET request_count = request_count - 1 "
            "WHERE usage_date = ? AND request_count > 0",
            (usage_date,),
        )
        conn.execute(
            "DELETE FROM daily_ai_usage WHERE usage_date = ? AND request_count = 0",
            (usage_date,),
        )
        conn.commit()
    finally:
        conn.close()


@app.before_request
def enforce_daily_ai_limit():
    usage_paths = {
        "/api/chat",
        "/api/chat/stream",
        "/api/translate",
        "/api/generate/slide",
        "/api/generate/document",
    }
    if request.method != "POST" or request.path not in usage_paths:
        return None

    allowed, usage_date, used, limit = reserve_daily_ai_request()
    if not allowed:
        return jsonify({
            "error": f"Ilovaning kunlik AI so'rovi limiti tugadi ({limit:,}/kun). Limit UTC 00:00 da yangilanadi.",
            "limit": limit,
            "used": used,
        }), 429
    g.daily_ai_usage_date = usage_date
    return None


@app.after_request
def release_stream_fallback_usage(response):
    usage_date = getattr(g, "daily_ai_usage_date", None)
    if request.path != "/api/chat/stream" or not usage_date or not response.is_json:
        return response
    payload = response.get_json(silent=True)
    if isinstance(payload, dict) and payload.get("fallback_required") is True:
        release_daily_ai_request(usage_date)
    return response


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


def openrouter_client(api_key=None):
    api_key = (api_key or os.getenv("OPENROUTER_API_KEY", "")).strip()
    if not api_key:
        return None
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def build_openrouter_messages(history, message, system_prompt=None, image=None, system_prompt_only=False):
    instruction = "" if system_prompt_only else DEFAULT_SYSTEM_PROMPT
    if isinstance(system_prompt, str) and system_prompt.strip():
        if instruction:
            instruction += f"\n\nFoydalanuvchining qo'shimcha ko'rsatmasi:\n{system_prompt.strip()}"
        else:
            instruction = system_prompt.strip()

    messages = [{"role": "system", "content": instruction}] if instruction else []
    for item in history[-8:]:
        if not isinstance(item, dict):
            continue
        content = item.get("content", "")
        if not isinstance(content, str) or not content:
            continue
        role = "user" if item.get("role") in ("user", "human") else "assistant"
        messages.append({"role": role, "content": content})
    user_content = [{"type": "text", "text": message}]
    if isinstance(image, dict):
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{image['mime_type']};base64,{image['data']}",
            },
        })
    messages.append({"role": "user", "content": user_content if image else message})
    return messages


def call_openrouter_api(
    history,
    message,
    system_prompt=None,
    use_search=False,
    image=None,
    system_prompt_only=False,
    max_tokens=2500,
    api_key=None,
    model=None,
    sources_out=None,
):
    try:
        client = openrouter_client(api_key)
        if client is None:
            return None, "OPENROUTER_API_KEY sozlanmagan."
        request = {
            "model": model or (os.getenv("OPENROUTER_VISION_MODEL", OPENROUTER_MODEL) if image else OPENROUTER_MODEL),
            "messages": build_openrouter_messages(
                history,
                message,
                system_prompt,
                image=image,
                system_prompt_only=system_prompt_only,
            ),
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }
        if use_search:
            request["extra_body"] = {"plugins": [{"id": "web"}]}
        response = client.chat.completions.create(**request)
        assistant_message = response.choices[0].message
        reply = assistant_message.content
        if sources_out is not None:
            message_data = assistant_message.model_dump()
            for annotation in message_data.get("annotations") or []:
                citation = annotation.get("url_citation", {})
                url = citation.get("url")
                if isinstance(url, str) and url.startswith(("https://", "http://")):
                    sources_out.append({"title": citation.get("title") or url, "url": url})
        if isinstance(reply, str) and reply.strip():
            return reply, None
        return None, "OpenRouter bo'sh javob qaytardi."
    except (OpenAIError, ValueError, IndexError, AttributeError) as error:
        app.logger.warning("OpenRouter chat ishlamadi (%s).", type(error).__name__)
        return None, f"OpenRouter chat ishlamadi ({type(error).__name__})."


def openrouter_api_error(response, operation):
    try:
        data = response.json()
        details = data.get("error", {}).get("message", "") if isinstance(data, dict) else ""
    except ValueError:
        details = ""
    if response.status_code == 401:
        return "OPENROUTER_API_KEY noto'g'ri yoki bekor qilingan."
    if response.status_code == 402:
        return "OpenRouter krediti yoki ushbu model uchun limit yetarli emas."
    if response.status_code == 429:
        return "OpenRouter so'rov limiti vaqtincha tugadi. Birozdan keyin qayta urinib ko'ring."
    suffix = f" {str(details)[:300]}" if details else ""
    return f"{operation} bajarilmadi (HTTP {response.status_code}).{suffix}"


def generate_openrouter_image(prompt, api_key=None):
    api_key = (api_key or os.getenv("OPENROUTER_API_KEY", "")).strip()
    if not api_key:
        return None, "OPENROUTER_API_KEY sozlanmagan."
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/images",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": OPENROUTER_IMAGE_MODEL, "prompt": prompt, "output_format": "png"},
            timeout=180,
        )
    except requests.RequestException as error:
        return None, f"OpenRouter rasm xizmatiga ulanib bo'lmadi ({type(error).__name__})."
    if response.status_code != 200:
        return None, openrouter_api_error(response, "OpenRouter rasm yaratish")
    try:
        image = response.json()["data"][0]
        image_data = base64.b64decode(image["b64_json"], validate=True)
        mime_type = image.get("media_type", "image/png")
    except (ValueError, KeyError, IndexError, TypeError, binascii.Error):
        return None, "OpenRouter javobidan rasmni o'qib bo'lmadi."
    extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime_type)
    if not extension:
        return None, f"OpenRouter qo'llab-quvvatlanmaydigan rasm formatini qaytardi: {mime_type}"
    if not image_data or len(image_data) > 20 * 1024 * 1024:
        return None, "OpenRouter yaratgan rasm bo'sh yoki 20 MB limitidan katta."
    filename = f"generated_{uuid.uuid4().hex}.{extension}"
    with open(os.path.join(GENERATED_DIR, filename), "wb") as image_file:
        image_file.write(image_data)
    return {
        "type": "image",
        "file_url": f"/download/{filename}",
        "filename": filename,
    }, None


def generate_openrouter_video(prompt, api_key=None):
    api_key = (api_key or os.getenv("OPENROUTER_API_KEY", "")).strip()
    if not api_key:
        return None, "OPENROUTER_API_KEY sozlanmagan."
    base_url = "https://openrouter.ai/api/v1"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        response = requests.post(
            f"{base_url}/videos",
            headers=headers,
            json={
                "model": OPENROUTER_VIDEO_MODEL,
                "prompt": prompt,
                "duration": 8,
                "resolution": "720p",
                "aspect_ratio": "16:9",
                "generate_audio": False,
            },
            timeout=60,
        )
    except requests.RequestException as error:
        return None, f"OpenRouter video xizmatiga ulanib bo'lmadi ({type(error).__name__})."
    if response.status_code not in (200, 202):
        return None, openrouter_api_error(response, "OpenRouter video yaratish")
    try:
        job = response.json()
        job_id = job["id"]
        status = job.get("status", "pending")
    except (ValueError, KeyError, TypeError):
        return None, "OpenRouter video job javobini o'qib bo'lmadi."
    if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]+", job_id):
        return None, "OpenRouter video job identifikatori noto'g'ri."

    deadline = time.monotonic() + 480
    while status not in ("completed", "failed", "cancelled", "expired"):
        if time.monotonic() >= deadline:
            return None, "OpenRouter video yaratish 8 daqiqada yakunlanmadi."
        time.sleep(10)
        try:
            status_response = requests.get(
                f"{base_url}/videos/{quote(job_id, safe='')}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30,
            )
        except requests.RequestException as error:
            return None, f"OpenRouter video holatini tekshirib bo'lmadi ({type(error).__name__})."
        if status_response.status_code != 200:
            return None, openrouter_api_error(status_response, "OpenRouter video holatini tekshirish")
        try:
            job = status_response.json()
            status = job.get("status")
        except ValueError:
            return None, "OpenRouter video holati javobini o'qib bo'lmadi."
    if status != "completed":
        return None, f"OpenRouter video yaratishni yakunlay olmadi ({status}). {job.get('error', '')}"

    try:
        video_response = requests.get(
            f"{base_url}/videos/{quote(job_id, safe='')}/content?index=0",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120,
        )
    except requests.RequestException as error:
        return None, f"OpenRouter videosini yuklab olib bo'lmadi ({type(error).__name__})."
    if video_response.status_code != 200:
        return None, openrouter_api_error(video_response, "OpenRouter videosini yuklab olish")
    video_data = video_response.content
    if not video_data or len(video_data) > 100 * 1024 * 1024:
        return None, "OpenRouter qaytargan video bo'sh yoki 100 MB hajm limitidan katta."
    filename = f"generated_{uuid.uuid4().hex}.mp4"
    with open(os.path.join(GENERATED_DIR, filename), "wb") as video_file:
        video_file.write(video_data)
    return {
        "type": "video",
        "model": OPENROUTER_VIDEO_MODEL,
        "file_url": f"/download/{filename}",
        "media_url": f"/media/{filename}",
        "filename": filename,
    }, None


def openrouter_stream_event(event, payload):
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
    return generate_openrouter_image(prompt, api_key)


def is_video_generation_request(message):
    query = message.lower()
    phrases = (
        "video yarat", "video yasab", "video tayyorla", "video qilib ber",
        "video generatsiya", "rolik yarat", "rolik tayyorla", "veo bilan",
        "generate a video", "create a video", "make a video", "make me a video",
        "создай видео", "сгенерируй видео", "crée une vidéo", "erstelle ein video",
    )
    return any(phrase in query for phrase in phrases)


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
    result, error = call_openrouter_api(
        [],
        f"Excel jadval mavzusi: {topic}",
        system_prompt=system_prompt,
        system_prompt_only=True,
        max_tokens=8000,
        api_key=api_key,
    )
    if error or result is None:
        raise ArtifactGenerationError(error or "OpenRouter jadval ma'lumotlarini yaratolmadi.")

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
        raise ArtifactGenerationError(f"OpenRouter jadval JSON formatini qaytarmadi: {error}") from error

    sheets = spreadsheet_data.get("sheets") if isinstance(spreadsheet_data, dict) else None
    if not isinstance(sheets, list) or not sheets or len(sheets) > 5:
        raise ArtifactGenerationError("OpenRouter jadval uchun yaroqli varaqlar ro'yxatini qaytarmadi.")
    preview_sheets = []
    for sheet in sheets:
        if not isinstance(sheet, dict):
            raise ArtifactGenerationError("OpenRouter qaytargan jadval varag'i noto'g'ri.")
        name, columns, rows = sheet.get("name"), sheet.get("columns"), sheet.get("rows")
        if (
            not isinstance(name, str)
            or not isinstance(columns, list)
            or not 1 <= len(columns) <= 30
            or not all(isinstance(column, str) and column.strip() for column in columns)
            or not isinstance(rows, list)
            or len(rows) > 500
        ):
            raise ArtifactGenerationError("OpenRouter qaytargan jadval ustunlari yoki qatorlari noto'g'ri.")
        for row in rows:
            if (
                not isinstance(row, list)
                or len(row) != len(columns)
                or any(not isinstance(value, (str, int, float, bool, type(None))) for value in row)
            ):
                raise ArtifactGenerationError("OpenRouter qaytargan jadval qatori ustunlarga mos emas.")
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


ACADEMIC_OUTPUT_PROMPT = (
    "Barcha akademik materialni faqat o'zbek tilida, lotin yozuvida yoz. "
    "Hech qanday shablon, qavsli to'ldirish joyi, ko'p nuqta, lorem ipsum yoki umumiy placeholder ishlatma. "
    "Mavzuga oid aniq fakt, sana, raqam va misollarni faqat ishonchli bo'lsa keltir; "
    "tadqiqot natijasi, statistika yoki manbani to'qib chiqarmagin. Tekshirilmagan ma'lumot o'rniga "
    "sifat jihatdan tahlil qil. Faqat so'ralgan JSON obyektini qaytar, markdown fence yoki izoh qo'shma."
)
ACADEMIC_PLACEHOLDERS = (
    "...", "[", "]", "lorem ipsum", "bu yerga yozing", "mavzu haqida ma'lumot",
    "to'ldiring", "fill in", "insert here", "placeholder",
)


def contains_academic_placeholder(value):
    if isinstance(value, str):
        lowered = value.lower()
        return any(marker in lowered for marker in ACADEMIC_PLACEHOLDERS)
    if isinstance(value, list):
        return any(contains_academic_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(contains_academic_placeholder(item) for item in value.values())
    return False


def parse_model_json(text, task_name):
    json_text = text.strip()
    if json_text.startswith("```"):
        json_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", json_text, flags=re.IGNORECASE)
    start = json_text.find("{")
    if start < 0:
        raise ArtifactGenerationError(f"OpenRouter {task_name} uchun JSON qaytarmadi.")
    try:
        result, _ = json.JSONDecoder().raw_decode(json_text[start:])
    except json.JSONDecodeError as error:
        raise ArtifactGenerationError(f"OpenRouter {task_name} JSON formati noto'g'ri: {error}") from error
    if not isinstance(result, dict):
        raise ArtifactGenerationError(f"OpenRouter {task_name} JSON obyekti noto'g'ri.")
    if contains_academic_placeholder(result):
        raise ArtifactGenerationError(f"OpenRouter {task_name} javobida to'ldirilmagan shablon bor; qayta urinib ko'ring.")
    return result


def academic_title_metadata(metadata=None):
    metadata = metadata if isinstance(metadata, dict) else {}
    message = metadata.get("message", "")
    message = message if isinstance(message, str) else ""
    labels = {
        "subject": ("fan", "fan nomi", "subject"),
        "student": ("bajardi", "talaba", "ism", "fio"),
        "teacher": ("tekshirdi", "o'qituvchi", "qabul qildi", "rahbar"),
        "university": ("universitet", "oliygoh", "otm"),
        "faculty": ("fakultet",),
        "group": ("guruh",),
        "city": ("shahar",),
    }

    def value(key, default):
        item = metadata.get(key)
        if isinstance(item, str) and item.strip():
            return item.strip()[:160]
        for label in labels.get(key, ()):
            match = re.search(
                rf"(?:^|[,;\n])\s*{re.escape(label)}\s*[:=]\s*([^,;\n]+)",
                message,
                flags=re.IGNORECASE,
            )
            if match and match.group(1).strip():
                return match.group(1).strip()[:160]
        return default

    supplied_year = metadata.get("year")
    if not isinstance(supplied_year, int):
        match = re.search(r"(?:^|[,;\n])\s*yil\s*[:=]\s*(20\d{2})", message, flags=re.IGNORECASE)
        supplied_year = int(match.group(1)) if match else datetime.datetime.now().year

    return {
        "subject": value("subject", "Mustaqil ta'lim"),
        "student": value("student", "Talaba"),
        "teacher": value("teacher", "O'qituvchi"),
        "university": value("university", "Universitet ko'rsatilmagan"),
        "faculty": value("faculty", "Fakultet ko'rsatilmagan"),
        "group": value("group", "Guruh ko'rsatilmagan"),
        "city": value("city", "Shahar ko'rsatilmagan"),
        "year": supplied_year,
    }


def require_sentence_list(value, minimum, maximum, field_name):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ArtifactGenerationError(f"{field_name} uchun {minimum}–{maximum} ta band kerak.")
    for sentence in value:
        if not isinstance(sentence, str) or len(sentence.split()) < 5 or sentence.rstrip()[-1:] not in ".!?":
            raise ArtifactGenerationError(f"{field_name} bandlari to'liq gap bo'lishi kerak.")


def generate_academic_presentation(topic, api_key, metadata=None):
    if not api_key:
        raise ArtifactGenerationError("Taqdimot yaratish uchun OPENROUTER_API_KEY sozlanmagan.")
    prompt = (
        f"Mavzu: {topic}\n"
        "Quyidagi JSON shaklida akademik taqdimot mazmunini yarat: "
        "{\"plan\":[4-6 reja bandi],\"slides\":[7 ta asosiy slayd uchun "
        "{\"title\":\"sarlavha\",\"items\":[4-6 to'liq gap]}],"
        "\"conclusion\":[4-6 to'liq gap],\"bibliography\":[3-6 ta haqiqiy manba nomi va URL]}. "
        "Slaydlar 3–9 asosiy mavzularni yoritadi. Har bir asosiy band kamida bitta to'liq gap bo'lsin. "
        "Rejani mavzuga mos tuz. Statistikani yoki manba bibliografiyasini uydirma."
    )
    result, error = call_openrouter_api(
        [], prompt, system_prompt=ACADEMIC_OUTPUT_PROMPT, system_prompt_only=True,
        max_tokens=6500, api_key=api_key,
    )
    if error or result is None:
        raise ArtifactGenerationError(error or "OpenRouter taqdimot mazmunini yaratolmadi.")
    content = parse_model_json(result, "taqdimot")
    plan = content.get("plan")
    core_slides = content.get("slides")
    conclusion = content.get("conclusion")
    bibliography = content.get("bibliography")
    if not isinstance(plan, list) or not 4 <= len(plan) <= 6 or not all(isinstance(item, str) and item.strip() for item in plan):
        raise ArtifactGenerationError("Taqdimot rejasi 4–6 mazmunli banddan iborat bo'lishi kerak.")
    if not isinstance(core_slides, list) or len(core_slides) < 7:
        raise ArtifactGenerationError("Taqdimotda kamida 7 ta asosiy slayd bo'lishi kerak.")
    for index, slide in enumerate(core_slides[:7], start=3):
        if not isinstance(slide, dict) or not isinstance(slide.get("title"), str) or not slide["title"].strip():
            raise ArtifactGenerationError(f"{index}-slayd sarlavhasi noto'g'ri.")
        require_sentence_list(slide.get("items"), 4, 6, f"{index}-slayd")
    require_sentence_list(conclusion, 4, 6, "Xulosa")
    if not isinstance(bibliography, list) or len(bibliography) < 3 or not all(isinstance(item, str) and item.strip() for item in bibliography):
        raise ArtifactGenerationError("Foydalanilgan adabiyotlarda kamida 3 ta manba bo'lishi kerak.")

    title = academic_title_metadata(metadata)
    slides = [{
        "type": "title",
        "title": topic,
        "subtitle": "Akademik taqdimot",
        "author": title["student"],
        "reviewer": title["teacher"],
        "subject": title["subject"],
        "university": title["university"],
        "group": title["group"],
        "city": title["city"],
        "year": title["year"],
    }, {
        "type": "content",
        "title": "Reja",
        "items": [f"{index}. {item}" for index, item in enumerate(plan, start=1)],
    }]
    slides.extend({"type": "content", "title": slide["title"], "items": slide["items"]} for slide in core_slides[:7])
    slides.append({"type": "conclusion", "title": "Xulosa", "items": conclusion})
    slides.append({"type": "content", "title": "Foydalanilgan adabiyotlar", "items": bibliography[:6]})
    result = generator.generate_presentation(topic, custom_slides=slides)
    return {
        "type": "presentation",
        "file_url": result["download_url"],
        "filename": result["filename"],
        "topic": topic,
        "slides": slides,
        "slide_count": len(slides),
    }


def generate_academic_document(topic, api_key, metadata=None):
    if not api_key:
        raise ArtifactGenerationError("Mustaqil ish yaratish uchun OPENROUTER_API_KEY sozlanmagan.")
    prompt = (
        f"Mavzu: {topic}\n"
        "3000–4000 so'zli, mazmunan to'liq mustaqil ish uchun faqat quyidagi JSONni yarat: "
        "{\"introduction\":[3 ta 2-3 gapli abzats],\"chapters\":["
        "{\"title\":\"I BOB...\",\"sections\":[{\"title\":\"1.1...\",\"paragraphs\":[2-3 ta to'liq abzats]},"
        "{\"title\":\"1.2...\",\"paragraphs\":[2-3 ta to'liq abzats]}]},"
        "yana II va III boblar shu shaklda],\"conclusion\":[2-3 ta abzats],"
        "\"bibliography\":[kamida 5 ta mavzuga oid haqiqiy manba, muallif/tashkilot, yil va URL]}. "
        "Har bobda kamida 2 bo'lim bo'lsin. Asosiy mazmun jami 3000–4000 so'z bo'lsin. "
        "Fakt yoki statistikani uydirma; aniq raqamni manbaga bog'la. Noma'lum manba nomini to'qima."
    )
    result, error = call_openrouter_api(
        [], prompt, system_prompt=ACADEMIC_OUTPUT_PROMPT, system_prompt_only=True,
        max_tokens=12000, api_key=api_key,
    )
    if error or result is None:
        raise ArtifactGenerationError(error or "OpenRouter mustaqil ish mazmunini yaratolmadi.")
    content = parse_model_json(result, "mustaqil ish")
    intro = content.get("introduction")
    chapters = content.get("chapters")
    conclusion = content.get("conclusion")
    bibliography = content.get("bibliography")
    if not isinstance(intro, list) or len(intro) < 2 or not all(isinstance(item, str) and item.strip() for item in intro):
        raise ArtifactGenerationError("Kirish kamida 2 ta to'liq abzatsdan iborat bo'lishi kerak.")
    if not isinstance(chapters, list) or len(chapters) < 3:
        raise ArtifactGenerationError("Mustaqil ishda kamida 3 ta bob bo'lishi kerak.")
    for chapter in chapters:
        if not isinstance(chapter, dict) or not isinstance(chapter.get("title"), str) or not chapter["title"].strip():
            raise ArtifactGenerationError("Bob sarlavhasi noto'g'ri.")
        subsections = chapter.get("sections")
        if not isinstance(subsections, list) or len(subsections) < 2:
            raise ArtifactGenerationError("Har bir bobda kamida 2 ta bo'lim bo'lishi kerak.")
        for subsection in subsections:
            paragraphs = subsection.get("paragraphs") if isinstance(subsection, dict) else None
            if not isinstance(paragraphs, list) or len(paragraphs) < 2 or not all(isinstance(item, str) and item.strip() for item in paragraphs):
                raise ArtifactGenerationError("Har bir bo'limda kamida 2 ta to'liq abzats bo'lishi kerak.")
    if not isinstance(conclusion, list) or len(conclusion) < 2 or not all(isinstance(item, str) and item.strip() for item in conclusion):
        raise ArtifactGenerationError("Xulosa kamida 2 ta to'liq abzatsdan iborat bo'lishi kerak.")
    if not isinstance(bibliography, list) or len(bibliography) < 5 or not all(isinstance(item, str) and item.strip() for item in bibliography):
        raise ArtifactGenerationError("Foydalanilgan adabiyotlarda kamida 5 ta manba bo'lishi kerak.")
    metadata = academic_title_metadata(metadata)
    result = generator.generate_mustaqil_ish_doc_content(
        topic,
        content,
        subject=metadata["subject"],
        student=metadata["student"],
        teacher=metadata["teacher"],
        university=metadata["university"],
        faculty=metadata["faculty"],
        group=metadata["group"],
        city=metadata["city"],
        year=metadata["year"],
    )
    return {
        "type": "document",
        "file_url": result["download_url"],
        "filename": result["filename"],
        "topic": topic,
        "html_preview": result["html_preview"],
        "word_count": result["word_count"],
    }


def check_and_generate_artifacts(query, api_key=None, metadata=None):
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
            raise ArtifactGenerationError("Excel jadval yaratish uchun OPENROUTER_API_KEY sozlanmagan.")
        return generate_spreadsheet_artifact(query, api_key.strip())

    if is_presentation:
        return generate_academic_presentation(topic, api_key, metadata)

    if is_word_doc:
        return generate_academic_document(topic, api_key, metadata)

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
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    requested_model = data.get("model_name")
    model_name = requested_model.strip() if isinstance(requested_model, str) and requested_model.strip() else OPENROUTER_MODEL
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

    if is_video_generation_request(message):
        if not api_key:
            return jsonify({"error": "OPENROUTER_API_KEY sozlanmagan."}), 401
        artifact, error = generate_openrouter_video(message, api_key)
        if error:
            return jsonify({"error": error}), 502
        return jsonify({
            "reply": "Video tayyor.",
            "provider": "openrouter",
            "model": OPENROUTER_VIDEO_MODEL,
            "artifact": artifact,
        })

    if is_image_generation_request(message):
        if not api_key:
            return jsonify({"error": "OPENROUTER_API_KEY sozlanmagan."}), 401
        artifact, error = generate_openrouter_image(message, api_key)
        if error:
            return jsonify({"error": error}), 502
        return jsonify({
            "reply": "Rasm tayyor.",
            "provider": "openrouter",
            "model": OPENROUTER_IMAGE_MODEL,
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
        artifact = check_and_generate_artifacts(message, api_key or None, metadata=data)
    except ArtifactGenerationError as error:
        return jsonify({"error": str(error)}), 502

    use_search = artifact is None and data.get("use_search") is True
    if artifact is None:
        if not api_key:
            return jsonify({"error": "OPENROUTER_API_KEY sozlanmagan."}), 401
        sources = []
        reply, error = call_openrouter_api(
            history,
            message,
            system_prompt,
            use_search=use_search,
            image=image,
            api_key=api_key,
            model=os.getenv("OPENROUTER_VISION_MODEL", OPENROUTER_MODEL) if image else model_name,
            sources_out=sources,
        )
        if reply:
            return jsonify({
                "reply": reply,
                "provider": "openrouter",
                "model": model_name,
                "artifact": None,
                "sources": sources,
            })
        return jsonify({"error": error or "OpenRouter javob qaytarmadi."}), 502

    artifact_replies = {
        "presentation": "Taqdimot mavzuga mos mazmun bilan tayyorlandi.",
        "document": "Mustaqil ish to'liq mazmun bilan tayyorlandi.",
        "spreadsheet": "Excel jadval tayyorlandi.",
    }
    return jsonify({
        "reply": artifact_replies.get(artifact.get("type"), "Fayl tayyorlandi."),
        "provider": "openrouter",
        "model": OPENROUTER_MODEL,
        "artifact": artifact,
    })


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
        or is_video_generation_request(message)
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

    model_name = data.get("model_name")
    if not isinstance(model_name, str) or not model_name.strip():
        model_name = OPENROUTER_MODEL

    try:
        client = openrouter_client()
        if client is None:
            return jsonify({"fallback_required": True})
        upstream = client.chat.completions.create(
            model=model_name,
            messages=build_openrouter_messages(history, message, system_prompt),
            temperature=0.7,
            max_tokens=2500,
            stream=True,
        )
    except (OpenAIError, ValueError) as error:
        app.logger.warning("OpenRouter oqimi ishlamadi (%s).", type(error).__name__)
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
                    yield openrouter_stream_event("chunk", {"text": text})
            if received_text:
                yield openrouter_stream_event("done", {})
            else:
                yield openrouter_stream_event("error", {"error": "OpenRouter bo'sh javob qaytardi."})
        except OpenAIError as error:
            app.logger.warning("OpenRouter oqimi uzildi (%s).", type(error).__name__)
            yield openrouter_stream_event(
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

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Tarjima uchun serverda OPENROUTER_API_KEY sozlanmagan"}), 401

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
        translation, error = call_openrouter_api(
            [],
            content,
            system_prompt=system_prompt,
            system_prompt_only=True,
            api_key=api_key,
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
    data = request.get_json(silent=True) or {}
    topic = data.get("topic")
    if not isinstance(topic, str) or not topic.strip():
        return jsonify({"error": "Taqdimot mavzusini kiriting."}), 400
    try:
        return jsonify(generate_academic_presentation(topic.strip(), os.getenv("OPENROUTER_API_KEY", "").strip(), data))
    except ArtifactGenerationError as error:
        return jsonify({"error": str(error)}), 502


@app.route("/api/generate/document", methods=["POST"])
def api_generate_document():
    data = request.get_json(silent=True) or {}
    topic = data.get("topic")
    if not isinstance(topic, str) or not topic.strip():
        return jsonify({"error": "Mustaqil ish mavzusini kiriting."}), 400
    try:
        return jsonify(generate_academic_document(topic.strip(), os.getenv("OPENROUTER_API_KEY", "").strip(), data))
    except ArtifactGenerationError as error:
        return jsonify({"error": str(error)}), 502


@app.route("/download/<path:filename>")
def download_file(filename):
    """Download generated presentations and word documents"""
    return send_from_directory(GENERATED_DIR, filename, as_attachment=True)


@app.route("/media/<path:filename>")
def view_generated_media(filename):
    return send_from_directory(GENERATED_DIR, filename, as_attachment=False)


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
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return jsonify({"valid": False, "error": "Server .env faylida OPENROUTER_API_KEY sozlanmagan."}), 400

    try:
        r = requests.get(
            "https://openrouter.ai/api/v1/key",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        if r.status_code == 200:
            return jsonify({"valid": True, "message": "OpenRouter API kaliti to'g'ri ishlamoqda!"})
        else:
            return jsonify({"valid": False, "error": openrouter_api_error(r, "OpenRouter API kaliti")}), 400
    except requests.RequestException as error:
        return jsonify({
            "valid": False,
            "error": f"OpenRouter xizmatiga ulanib bo'lmadi. Server internet/DNS ulanishini tekshiring. ({type(error).__name__})"
        }), 502


@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "app": "Mahliyo AI",
        "version": "1.4.0",
        "features": [
            "Chat", "Image understanding", "Image generation", "Video generation", "Programming assistance",
            "Language matching", "Presentation PPTX", "Word DOCX",
            "Voice Recognition", "Speech Synthesis"
        ],
        "timestamp": datetime.datetime.now().isoformat()
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
