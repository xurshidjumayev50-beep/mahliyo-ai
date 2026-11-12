# 🌙 Mahliyo AI — Aqlli O'zbek Sun'iy Intellekti

<p align="center">
  <img src="static/images/logo.svg" width="90" alt="Mahliyo AI Logo" />
</p>

<p align="center">
  <b>Mahliyo</b> — OpenRouter orqali ilg'or sun'iy intellekt modellariga ulangan, o'zbek tilida tabiiy va ravon muloqot qiluvchi platforma.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue.svg" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/Flask-3.1-success.svg" alt="Flask" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg" alt="Docker" />
  <img src="https://img.shields.io/badge/Design-Midnight%20Blue-12153e.svg" alt="Theme" />
  <img src="https://img.shields.io/badge/O'zbek-Tili-3ccbb7.svg" alt="Uzbek" />
</p>

---

## ✨ Asosiy Xususiyatlari

- 🌌 **Premium Ko'k Midnight Dizayn:** Haqiqiy milliy naqshlar (geometric Islamic pattern) bilan bezatilgan shinam va zamonaviy ko'k UI interfeysi.
- ⚡ **Tezkor va Ravon Muloqot:** OpenRouter orqali turli chat va vision modellarini tanlash mumkin.
- 💬 **So'zma-so'z javoblar:** OpenRouter SSE oqimi matnni darhol ko'rsatadi; qidiruv, rasm va video ham OpenRouter orqali ishlaydi.
- 🔑 **OpenRouter API Kaliti:** Chat, qidiruv, tarjima, rasm va video uchun yagona server kaliti ishlatiladi.
- 📝 **Dasturlash Yordami:** Python, JavaScript, TypeScript, Java, C/C++, C#, Go, Rust, PHP, Ruby, Swift, Kotlin, SQL, HTML va CSS kodlarini yozish hamda tahlil qilish.
- 🗣️ **Ovozli O'qish (Text-to-Speech):** Mahliyo bergan javoblarni ovoz chiqarib o'qitish imkoniyati.
- 📷 **Rasmni Tahlil va Generatsiya Qilish:** JPEG, PNG yoki WebP rasmini yuborib savol bering yoki yangi rasm yaratishni so'rang.
- 🎬 **Video Generatsiya:** OpenRouter video modeli orqali video yarating va MP4 formatida yuklab oling.
- 📝 **Markdown va Kodlar Sintaksisi:** Kodlarni chiroyli ranglar bilan ajratib ko'rsatish va bir tugma bilan nusxa olish.
- 💾 **Suhbatlar Tarixi (Persistent History):** Barcha yozishmalar saqlanib qoladi va istalgan vaqtda qayta ochilishi mumkin.
- 🐳 **Docker & Docker Compose:** 1 ta buyruq bilan konteynerda ishga tushirishga to'liq tayyor.
- 💾 **Doimiy ma'lumotlar:** Suhbatlar va yaratilgan fayllar Docker volume'da saqlanadi.
- 📈 **Excel jadval yaratish:** OpenRouter tuzgan ma'lumotlar .xlsx faylga, sarlavha uslubi va jamlash/o'rtacha formulalari bilan yoziladi.

---

## 🚀 Loyihani Ishga Tushirish

### 1-Usul: Docker orqali (Tavsiya etiladi)

Loyiha papkasida quyidagi buyruqni bering:

```bash
# Docker konteynerni qurish va fonda ishga tushirish
docker compose up -d --build
```

Yoki oddiy Docker buyrug'i orqali:

```bash
docker build -t mahliyo-ai .
docker run -d -p 5000:5000 --name mahliyo-ai-container mahliyo-ai
```

Brauzerda oching: **`http://localhost:5000`**

---

### 2-Usul: Python orqali (Mahalliy)

1. **Virtual muhitni faollashtiring:**
```bash
python3 -m venv venv
source venv/bin/activate
```

2. **Kutubxonalarni o'rnating:**
```bash
pip install -r requirements.txt
```

3. **`.env` faylida `MAHLIYO_API_KEY` va `OPENROUTER_API_KEY` ni sozlang.** Ilova kalitini quyidagi buyruq bilan yarating:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

4. **FastAPI serverni yoqing:**
```bash
uvicorn api:api --host 0.0.0.0 --port 5000 --timeout-keep-alive 600
```

API hujjatlari `http://localhost:5000/docs` manzilida. API manzillari: `POST /v1/chat`, `POST /v1/generate/image`, `POST /v1/generate/video` va `GET /v1/health`. Yozish va generatsiya so'rovlari `X-API-Key` sarlavhasida `.env` dagi `MAHLIYO_API_KEY` ni talab qiladi; model API kaliti serverda `OPENROUTER_API_KEY` sifatida qoladi. Eski web interfeys `http://localhost:5000/` va `/api/*` yo'llarida ishlashda davom etadi.

Serverni birinchi marta ishga tushirishdan oldin `.env` faylida `SECRET_KEY` uchun tasodifiy, maxfiy qiymat belgilang. Uni yaratish uchun:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Oddiy matnli suhbatlar `POST /api/chat/stream` orqali OpenRouter SSE oqimida keladi. Qidiruv, rasm, video va spreadsheet mazmuni ham OpenRouter orqali ishlaydi; javob yozilayotganda **To'xtatish** tugmasi oqimni bekor qiladi.

Yozish maydoni yonidagi **🌐 Internet** tugmasi Google Search grounding'ni yoqadi yoki o'chiradi; tanlov brauzer xotirasida saqlanadi. Yoqilganda oddiy chat javoblari manbalarni ko'rsatadi. Rasm va slayd/Word/Excel yaratish oqimlari internet qidiruvidan foydalanmaydi.

### Akkauntlar va mehmon rejimi

Sidebar pastidagi **Kirish** orqali email va parol bilan akkaunt yarating yoki tizimga kiring. Akkaunt suhbatlari SQLite bazasida foydalanuvchiga bog'lab saqlanadi; tizimga kirmagan foydalanuvchilar avvalgidek mehmon rejimida ishlaydi va suhbatlari brauzerning mahalliy xotirasida qoladi. Parollar Werkzeug orqali xeshlanadi, login urinishlari IP bo'yicha cheklanadi. Google orqali kirish keyingi bosqichda qo'shiladi.

`/api/auth/register`, `/api/auth/login`, `/api/auth/logout` va `/api/auth/me` autentifikatsiya endpointlari hisoblanadi. `/api/conversations` endpointlari faqat joriy akkaunt suhbatlariga yoki mehmon rejimida akkauntga biriktirilmagan eski suhbatlarga ruxsat beradi.

Sidebar'dagi **Tarjima** paneli matnni avtomatik aniqlash yoki O'zbek lotin, O'zbek kirill, Ingliz, Rus va Turk tillari orasida tarjima qiladi. `POST /api/translate` endpointi 5 000 belgidan uzun matnni bo'laklarga ajratadi; tarjima uchun serverdagi `OPENROUTER_API_KEY` ishlatiladi.

---

## 🔑 API Kalitlarini Sozlash

Mahliyo ilovasining barcha foydalanuvchilar uchun umumiy kunlik AI so'rovi limiti `DAILY_AI_LIMIT` bilan belgilanadi; standart qiymati `10000`. Hisob UTC bo'yicha yuritiladi va har kuni 00:00 UTC da yangilanadi. Bu ilova ichidagi limit; OpenRouter krediti va model rate-limitlarini oshirmaydi.

1. API kalitini [OpenRouter](https://openrouter.ai/keys) sahifasidan oling va `.env` faylidagi `OPENROUTER_API_KEY` qiymatiga kiriting. U chat, qidiruv, tarjima, rasm va video uchun ishlatiladi.
2. `OPENROUTER_MODEL`, `OPENROUTER_VISION_MODEL`, `OPENROUTER_IMAGE_MODEL` va `OPENROUTER_VIDEO_MODEL` orqali modellarni tanlang. Model mavjudligi, imkoniyatlari va narxi OpenRouter katalogiga bog'liq; rasm/video yaratish OpenRouter kreditini sarflashi mumkin.
3. Kalitni faqat loyiha papkasidagi `.env` faylida saqlang. `.env.example` faqat namuna; maxfiy kalitni unga, Git'ga yoki brauzer xotirasiga qo'shmang. Docker Compose konteynerga `.env` qiymatlarini uzatadi.
```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openrouter/free
OPENROUTER_VISION_MODEL=openrouter/free
OPENROUTER_IMAGE_MODEL=google/gemini-3.1-flash-image
OPENROUTER_VIDEO_MODEL=google/veo-3.1-lite
CHAT_PROVIDER=openrouter
```

Kalitlarni o'zgartirgandan keyin Docker Compose'ni qayta ishga tushiring: `docker compose up -d`. Xavfsizlik uchun kodga kalit yozmang va terminal buyrug'i argumenti sifatida bermang.

Video yaratish OpenRouter asinxron job, polling va content endpointlaridan foydalanadi; tayyor MP4 bir necha daqiqa olishi mumkin. Barcha model so'rovlari OpenRouter krediti va tanlangan model tarifiga bo'ysunadi. Kalit oshkor bo'lgan bo'lsa, OpenRouter'da bekor qilib yangisini yarating.

---

## 📁 Loyiha Tuzilishi

```text
mahliyo-ai/
├── app.py                 # Flask server va API boshqaruvi
├── requirements.txt       # Python kutubxonalari
├── Dockerfile             # Docker konteyner fayli
├── docker-compose.yml     # Docker Compose konfiguratsiyasi
├── .dockerignore          # Docker istisnolari
├── .gitignore             # Git istisnolari
├── .env.example           # Muhit o'zgaruvchilari namunasi
├── static/
│   ├── css/
│   │   └── style.css      # Midnight ko'k va yalpiz rangli dizayn
│   ├── js/
│   │   └── app.js         # Muloqot, chat streaming va sozlamalar mantiqi
│   └── images/
│       ├── logo.svg       # Mahliyo yarim oy logotipi
│       └── pattern.svg    # Fon uchun geometrik naqsh
└── templates/
    └── index.html         # Asosiy veb sahifa
```

---

## 🌐 Muallif va Repozitoriy

- **Loyiha nomi:** Mahliyo AI
- **GitHub:** [https://github.com/xurshidjumayev50-beep](https://github.com/xurshidjumayev50-beep)
- **Versiya:** 1.4.0
