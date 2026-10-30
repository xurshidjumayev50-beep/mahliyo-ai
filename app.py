import os
import json
import sqlite3
import datetime
import traceback
from flask import Flask, render_template, request, Response, jsonify, stream_with_context, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import requests

import generator

load_dotenv()

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "mahliyo.db")
GENERATED_DIR = os.path.join(os.path.dirname(__file__), "static", "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)

DEFAULT_SYSTEM_PROMPT = (
    "Sen Mahliyo — O'zbekiston uchun maxsus ishlab chiqilgan ilg'or, aqlli, "
    "xushmuomala va samimiy sun'iy intellekt yordamchisisan. "
    "Sen o'zbek tilida (lotin alifbosida) ravon, tushunarli, imlo qoidalariga rioya qilgan "
    "holda chiroyli javob berasan. Har bir mavzuni: dasturlash, rasmiy xat va arizalar, "
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
            updated_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def call_gemini_api(api_key, messages, model_name="gemini-1.5-flash", system_prompt=None):
    """Call Google Gemini API using REST endpoint"""
    if not model_name:
        model_name = "gemini-1.5-flash"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    contents = []
    system_instruction = system_prompt or DEFAULT_SYSTEM_PROMPT

    for m in messages:
        role = "user" if m.get("role") in ["user", "human"] else "model"
        text = m.get("content", "")
        contents.append({
            "role": role,
            "parts": [{"text": text}]
        })

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2500,
        }
    }

    resp = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=60
    )
    
    if resp.status_code != 200:
        return None, f"Gemini API xatosi ({resp.status_code}): {resp.text}"
        
    data = resp.json()
    try:
        candidate = data["candidates"][0]
        text = candidate["content"]["parts"][0]["text"]
        return text, None
    except Exception as e:
        return None, f"Javobni o'qishda xatolik: {str(e)}"


def check_and_generate_artifacts(query):
    """
    Checks if user is asking to create a presentation (slayd)
    or independent research paper (mustaqil ish / word doc),
    and generates the corresponding file!
    """
    q = query.lower()

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


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])
    api_key = data.get("api_key") or os.environ.get("GEMINI_API_KEY")
    model_name = data.get("model_name", "gemini-1.5-flash")
    system_prompt = data.get("system_prompt")

    if not message:
        return jsonify({"error": "Xabar bo'sh bo'lishi mumkin emas"}), 400

    # Check if user needs presentation or word doc generated
    artifact = check_and_generate_artifacts(message)

    # If API key is present, try Gemini
    if api_key and api_key.strip():
        formatted_messages = []
        for h in history[-8:]:
            formatted_messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        formatted_messages.append({"role": "user", "content": message})

        reply, err = call_gemini_api(api_key.strip(), formatted_messages, model_name, system_prompt)
        if reply:
            return jsonify({
                "reply": reply,
                "provider": "gemini",
                "model": model_name,
                "artifact": artifact
            })

    # Fallback response
    reply = generate_smart_fallback(message, history)
    return jsonify({
        "reply": reply,
        "provider": "mahliyo-local",
        "model": "mahliyo-core-v1",
        "artifact": artifact
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
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC")
    rows = cursor.fetchall()
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
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversations WHERE id = ?", (cid,))
    row = cursor.fetchone()
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
    now = datetime.datetime.now().isoformat()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversations (id, title, messages, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            messages = excluded.messages,
            updated_at = excluded.updated_at
    """, (cid, title, messages, now, now))
    conn.commit()
    conn.close()

    return jsonify({"status": "saved", "id": cid, "title": title})


@app.route("/api/conversations/<cid>", methods=["DELETE"])
def delete_conversation(cid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations WHERE id = ?", (cid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted", "id": cid})


@app.route("/api/test-key", methods=["POST"])
def test_key():
    data = request.get_json() or {}
    api_key = data.get("api_key", "").strip()
    if not api_key:
        return jsonify({"valid": False, "error": "Kalit kiritilmagan"}), 400

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return jsonify({"valid": True, "message": "Gemini API kaliti to'g'ri ishlamoqda!"})
        else:
            return jsonify({"valid": False, "error": f"Kalit yaroqsiz ({r.status_code}): {r.text}"}), 400
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 500


@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "app": "Mahliyo AI",
        "version": "1.1.0",
        "features": ["Chat", "Presentation PPTX", "Word DOCX", "Voice Recognition", "Speech Synthesis"],
        "timestamp": datetime.datetime.now().isoformat()
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
