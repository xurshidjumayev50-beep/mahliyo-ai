import os
import json
import sqlite3
import datetime
import traceback
from flask import Flask, render_template, request, Response, jsonify, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "mahliyo.db")
DEFAULT_SYSTEM_PROMPT = (
    "Sen Mahliyo — O'zbekiston uchun maxsus ishlab chiqilgan ilg'or, aqlli, "
    "xushmuomala va samimiy sun'iy intellekt yordamchisisan. "
    "Sen o'zbek tilida (lotin alifbosida) ravon, tushunarli, imlo qoidalariga rioya qilgan "
    "holda chiroyli javob berasan. Har bir mavzuni: dasturlash, rasmiy xat va arizalar, "
    "slayd va taqdimot rejalari, fan va ta'lim bo'yicha yuqori darajada tushuntirib bera olasan. "
    "Formatlashda Markdown sarlavhalari, ro'yxatlar va kod bloklaridan unumli foydalan."
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
    """Call Google Gemini API using REST endpoint for maximum streaming compatibility"""
    # Normalize model name
    if not model_name:
        model_name = "gemini-1.5-flash"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    # Format contents for Gemini
    contents = []
    
    # If system prompt is provided, prepend or set systemInstruction
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
            "maxOutputTokens": 2048,
        }
    }

    resp = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=60
    )
    
    if resp.status_code != 200:
        error_msg = f"Gemini API xatosi ({resp.status_code}): {resp.text}"
        return None, error_msg
        
    data = resp.json()
    try:
        candidate = data["candidates"][0]
        text = candidate["content"]["parts"][0]["text"]
        return text, None
    except Exception as e:
        return None, f"Javobni o'qishda xatolik: {str(e)} -> {data}"


def generate_smart_fallback(user_query, history=None):
    """
    Intelligent built-in fallback responder for Mahliyo AI
    Provides rich Uzbek responses even if no API key is set yet.
    """
    q = user_query.strip().lower()

    if "slayd" in q or "taqdimot" in q:
        return (
            "### 📊 Taqdimot (Slayd) Rejasi\n\n"
            "Mavzuni ajoyib tarzda yoritish uchun quyidagi professional reja va matn tuzilmasini taklif qilaman:\n\n"
            "1. **1-Slayd: Kirish**\n"
            "   - Taqdimot mavzusi va maqsadi\n"
            "   - Muallif ma'lumotlari\n\n"
            "2. **2-Slayd: Muammoning dolzarbligi**\n"
            "   - Nega ushbu mavzu bugungi kunda muhim?\n"
            "   - Statistika va real holat tahlili\n\n"
            "3. **3-Slayd: Asosiy vazifalar va maqsadlar**\n"
            "   - Qanday natijalarga erishish ko'zda tutilgan?\n\n"
            "4. **4-Slayd: Taklif etilayotgan yechimlar / Amaliy qism**\n"
            "   - Asosiy g'oyalar va innovatsion yondashuv\n"
            "   - Bosqichma-bosqich amalga oshirish rejasi\n\n"
            "5. **5-Slayd: Kutilayotgan samaradorlik**\n"
            "   - Moddiy va ma'naviy foyda\n\n"
            "6. **6-Slayd: Xulosa va Savol-javob**\n"
            "   - Asosiy xulosalar\n"
            "   - E'tiboringiz uchun rahmat!\n\n"
            "> 💡 **Maslahat:** Agar aniq bir mavzu (masalan, *Ekologiya*, *Sun'iy intellekt*, *Biznes*) bersangiz, har bir slayd uchun tayyor matn va grafik g'oyalarni yozib beraman!"
        )

    if "ariza" in q or "xat" in q or "rasmiy" in q:
        return (
            "### 📄 Rasmiy Ariza Namunasi\n\n"
            "O'zbekiston standartlari bo'yicha to'g'ri shakllantirilgan ariza matni:\n\n"
            "```text\n"
            "                                     [Tashkilot / Universitet nomi] rahbari\n"
            "                                     [Ism, familiyasi]ga\n"
            "                                     [Foydalanuvchi F.I.Sh.]dan\n"
            "                                     Tel: +998 (__) ___-__-__\n\n"
            "                                 ARIZA\n\n"
            "    Men ushbu arizani yozishimdan maqsad shuki, [aniq sabab va holat bayoni,\n"
            "masalan: darslarni qoldirish / moddiy yordam / ta'til so'rash]. \n\n"
            "    Yuqoridagilarni inobatga olgan holda, mening ushbu iltimosimni ijobiy\n"
            "hal qilib berishingizni so'rayman.\n\n"
            "    Arizaga ilova qilinadigan hujjatlar (mavjud bo'lsa):\n"
            "    1. [Hujjat nomi]\n\n"
            "Sana: [Kun.Oy.Yil]                          Imzo: ___________ [F.I.Sh.]\n"
            "```\n\n"
            "> Sizga aniq qaysi tashkilotga yoki mavzuga oid xat kerak? Tafsilotlarni yozsangiz, to'liq to'ldirib beraman."
        )

    if "kod" in q or "xato" in q or "bug" in q or "python" in q:
        return (
            "### 💻 Kod tahlili va yordam\n\n"
            "Kod xatosini topish uchun quyidagi qadamlarni ko'rib chiqamiz:\n\n"
            "1. **Xato xabarini (Traceback)** to'liq o'qing — unda xato yuz bergan fayl nomi va qator raqami ko'rsatiladi.\n"
            "2. **Keng tarqalgan xatolar:**\n"
            "   - `SyntaxError`: Qavs yoki qo'shtirnoq yopilmagan, ikki nuqta `:` unutilgan.\n"
            "   - `IndentationError`: Bo'shliqlar (indentatsiya) noto'g'ri qo'yilgan.\n"
            "   - `TypeError`: Noto'g'ri turdagi ma'lumotlar bilan amal bajarilgan.\n"
            "   - `NameError`: E'lon qilinmagan o'zgaruvchi chaqirilgan.\n\n"
            "```python\n"
            "# Misol: Xatolarni xavfsiz ushlash namunasi\n"
            "try:\n"
            "    result = 10 / 2\n"
            "    print(f'Muvaffaqiyatli: {result}')\n"
            "except Exception as e:\n"
            "    print(f'Xatolik yuz berdi: {e}')\n"
            "```\n\n"
            "Iltimos, o'zingizdagi kodni va uning xato xabarini yuboring, sababini topib to'g'irlab beraman!"
        )

    if "tushuntir" in q or "oddiy" in q or "rekursiya" in q:
        return (
            "### 🧠 Oddiy tushuntirish: Rekursiya va Iteratsiya\n\n"
            "Murakkab mavzuni hayotiy misol bilan sodda tushunamiz:\n\n"
            "- **Iteratsiya (Sikl / Loop):** Biror ishni ketma-ket bir necha bor takrorlash. \n"
            "  *Hayotiy misol:* Siz zinapoyadan chiqayotganda: 1-pog'ona, 2-pog'ona, 3-pog'ona deb navbatma-navbat ko'tarilasiz.\n\n"
            "- **Rekursiya:** Funksiyaning o'z-o'zini chaqirishi.\n"
            "  *Hayotiy misol:* Matryoshka qo'g'irchog'i! Eng kattasini ochasiz — ichidan kichigi chiqadi, uni ochasiz — yana kichigi chiqadi. Eng kichigiga (tubiga) yetguncha davom etasiz.\n\n"
            "```python\n"
            "# Rekursiya orqali faktorial hisoblash:\n"
            "def faktorial(n):\n"
            "    if n == 1:\n"
            "        return 1  # To'xtash sharti (Eng kichik matryoshka)\n"
            "    return n * faktorial(n - 1)\n"
            "```\n\n"
            "Qaysi boshqa tushunchani soddalashtirib berishimni xohlaysiz?"
        )

    # General greeting and natural Uzbek intelligence
    return (
        f"Salom! Men **Mahliyo AI** — sizning aqlli yordamchingizman. 🌙\n\n"
        f"Savolingiz: *\"{user_query}\"*\n\n"
        f"Men sizga matnlar yozish, ilmiy va o'quv ishlari, dasturlash (Python, JavaScript va boshqalar), "
        f"tarjimalar hamda murakkab masalalarni tahlil qilishda yordam berishga doim tayyorman.\n\n"
        f"Nima haqida batafsilroq gaplashamiz?\n\n"
        f"> ⚙️ **Eslatma:** Agar Mahliyo'ning to'liq bulutli quvvatini yoqishni istasangiz, "
        f"chap pastdagi **Sozlamalar** tugmasi orqali o'zingizning bepul **Gemini API Key** kalitingizni kiritishingiz mumkin."
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

    # If API key is present, try Gemini
    if api_key and api_key.strip():
        # Build message chain
        formatted_messages = []
        for h in history[-8:]:  # Context window of last 8 messages
            formatted_messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        formatted_messages.append({"role": "user", "content": message})

        reply, err = call_gemini_api(api_key.strip(), formatted_messages, model_name, system_prompt)
        if reply:
            return jsonify({
                "reply": reply,
                "provider": "gemini",
                "model": model_name
            })
        # If API key failed, fallback gracefully with notice
        fallback_reply = generate_smart_fallback(message, history)
        return jsonify({
            "reply": f"{fallback_reply}\n\n*(Eslatma: Gemini API xatosi yuz bergani sababli mahalliy javob qaytarildi: {err})*",
            "provider": "fallback",
            "model": "mahliyo-core"
        })

    # If no API key, use Mahliyo smart fallback
    reply = generate_smart_fallback(message, history)
    return jsonify({
        "reply": reply,
        "provider": "mahliyo-local",
        "model": "mahliyo-core-v1"
    })


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """Server-Sent Events streaming endpoint for real-time typewriter experience"""
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])
    api_key = data.get("api_key") or os.environ.get("GEMINI_API_KEY")
    model_name = data.get("model_name", "gemini-1.5-flash")
    system_prompt = data.get("system_prompt")

    if not message:
        return jsonify({"error": "Xabar bo'sh bo'lishi mumkin emas"}), 400

    def generate():
        # Check if API key is provided
        if api_key and api_key.strip():
            formatted_messages = []
            for h in history[-8:]:
                formatted_messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
            formatted_messages.append({"role": "user", "content": message})

            reply, err = call_gemini_api(api_key.strip(), formatted_messages, model_name, system_prompt)
            if reply:
                # Stream the reply in pleasant chunks
                words = reply.split(" ")
                chunk = []
                for i, word in enumerate(words):
                    chunk.append(word)
                    if len(chunk) >= 3 or i == len(words) - 1:
                        yield f"data: {json.dumps({'chunk': ' '.join(chunk) + ' '})}\n\n"
                        chunk = []
                yield f"data: {json.dumps({'done': True})}\n\n"
                return

        # Fallback stream
        fallback_text = generate_smart_fallback(message, history)
        words = fallback_text.split(" ")
        chunk = []
        for i, word in enumerate(words):
            chunk.append(word)
            if len(chunk) >= 4 or i == len(words) - 1:
                yield f"data: {json.dumps({'chunk': ' '.join(chunk) + ' '})}\n\n"
                chunk = []
        yield f"data: {json.dumps({'done': True})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


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
        "version": "1.0.0",
        "description": "O'zbek tilidagi aqlli sun'iy intellekt platformasi",
        "timestamp": datetime.datetime.now().isoformat()
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
