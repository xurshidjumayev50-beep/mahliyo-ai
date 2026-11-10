# 🌙 Mahliyo AI — Aqlli O'zbek Sun'iy Intellekti

<p align="center">
  <img src="static/images/logo.svg" width="90" alt="Mahliyo AI Logo" />
</p>

<p align="center">
  <b>Mahliyo</b> — Gemini va ChatGPT kabi ilg'or imkoniyatlarga ega, o'zbek tilida tabiiy va ravon muloqot qiluvchi zamonaviy sun'iy intellekt platformasi.
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
- ⚡ **Tezkor va Ravon Muloqot:** Google Gemini 3.5 Flash integratsiyasi; foydalanuvchi yozgan tilda javob beradi.
- 💬 **So'zma-so'z javoblar:** Oddiy chat Gemini SSE oqimi orqali matnni darhol ko'rsatadi; rasm va fayl yaratish amallari mavjud endpointdan foydalanadi.
- 🔑 **Gemini API Kaliti:** Oddiy AI suhbati, rasm tahlili va rasm yaratish uchun Google AI Studio kaliti talab qilinadi. Kalitsiz ham slayd va Word fayllarini tayyorlash hamda mavzu bo'yicha savollarga javob berish mumkin.
- 📝 **Dasturlash Yordami:** Python, JavaScript, TypeScript, Java, C/C++, C#, Go, Rust, PHP, Ruby, Swift, Kotlin, SQL, HTML va CSS kodlarini yozish hamda tahlil qilish.
- 🗣️ **Ovozli O'qish (Text-to-Speech):** Mahliyo bergan javoblarni ovoz chiqarib o'qitish imkoniyati.
- 📷 **Rasmni Tahlil va Generatsiya Qilish:** JPEG, PNG yoki WebP rasmini yuborib savol bering yoki yangi rasm yaratishni so'rang.
- 🎬 **Video Generatsiya:** Gemini API kaliti orqali Veo 3.1 yordamida 8 soniyalik video yarating va MP4 formatida yuklab oling.
- 📝 **Markdown va Kodlar Sintaksisi:** Kodlarni chiroyli ranglar bilan ajratib ko'rsatish va bir tugma bilan nusxa olish.
- 💾 **Suhbatlar Tarixi (Persistent History):** Barcha yozishmalar saqlanib qoladi va istalgan vaqtda qayta ochilishi mumkin.
- 🐳 **Docker & Docker Compose:** 1 ta buyruq bilan konteynerda ishga tushirishga to'liq tayyor.
- 💾 **Doimiy ma'lumotlar:** Suhbatlar va yaratilgan fayllar Docker volume'da saqlanadi.
- 📈 **Excel jadval yaratish:** Gemini tuzgan ma'lumotlar .xlsx faylga, sarlavha uslubi va jamlash/o'rtacha formulalari bilan yoziladi.

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

3. **Serverni yoqing:**
```bash
python app.py
```
Yoki Gunicorn orqali:
```bash
gunicorn --bind 0.0.0.0:5000 --timeout 600 app:app
```

Serverni birinchi marta ishga tushirishdan oldin `.env` faylida `SECRET_KEY` uchun tasodifiy, maxfiy qiymat belgilang. Uni yaratish uchun:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Oddiy matnli suhbatlar `POST /api/chat/stream` orqali OpenRouter SSE oqimida keladi; OpenRouter ishlamasa, server Gemini'ga qaytadi. Rasm, slayd, Word va qo'llab-quvvatlanmaydigan javoblar uchun brauzer avtomatik `POST /api/chat` endpointiga qaytadi; javob yozilayotganda **To'xtatish** tugmasi oqimni bekor qiladi.

Yozish maydoni yonidagi **🌐 Internet** tugmasi Google Search grounding'ni yoqadi yoki o'chiradi; tanlov brauzer xotirasida saqlanadi. Yoqilganda oddiy chat javoblari manbalarni ko'rsatadi. Rasm va slayd/Word/Excel yaratish oqimlari internet qidiruvidan foydalanmaydi.

### Akkauntlar va mehmon rejimi

Sidebar pastidagi **Kirish** orqali email va parol bilan akkaunt yarating yoki tizimga kiring. Akkaunt suhbatlari SQLite bazasida foydalanuvchiga bog'lab saqlanadi; tizimga kirmagan foydalanuvchilar avvalgidek mehmon rejimida ishlaydi va suhbatlari brauzerning mahalliy xotirasida qoladi. Parollar Werkzeug orqali xeshlanadi, login urinishlari IP bo'yicha cheklanadi. Google orqali kirish keyingi bosqichda qo'shiladi.

`/api/auth/register`, `/api/auth/login`, `/api/auth/logout` va `/api/auth/me` autentifikatsiya endpointlari hisoblanadi. `/api/conversations` endpointlari faqat joriy akkaunt suhbatlariga yoki mehmon rejimida akkauntga biriktirilmagan eski suhbatlarga ruxsat beradi.

Sidebar'dagi **Tarjima** paneli matnni avtomatik aniqlash yoki O'zbek lotin, O'zbek kirill, Ingliz, Rus va Turk tillari orasida tarjima qiladi. `POST /api/translate` endpointi 5 000 belgidan uzun matnni bo'laklarga ajratadi; tarjima uchun serverdagi `GEMINI_API_KEY` ishlatiladi.

---

## 🔑 API Kalitlarini Sozlash

1. Oddiy matnli chat uchun [OpenRouter](https://openrouter.ai/keys) sahifasidan API kalit oling. `.env` faylida `OPENROUTER_API_KEY` qiymatini belgilang. Model `OPENROUTER_MODEL` orqali tanlanadi va faqat `:free` bilan tugaydigan model ishlatiladi.
2. Gemini kalitini [Google AI Studio](https://aistudio.google.com/app/apikey) sahifasidan oling. Gemini kaliti OpenRouter ishlamagan paytdagi chat fallback'i, rasm tahlili/yaratish, Veo video yaratish, qidiruv, tarjima va hujjat/jadval yaratish uchun kerak.
3. Ikkala kalitni ham loyiha papkasidagi `.env` faylida saqlang. Yangi nusxada `.env.example` faylidan foydalaning; `.env` Git'ga qo'shilmaydi va Docker konteyneriga muhit o'zgaruvchisi sifatida uzatiladi. Sayt sozlamalaridagi Gemini kaliti ham qo'shimcha usul sifatida ishlaydi.
```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
GEMINI_API_KEY=AIzaSy...
```

Kalitlarni o'zgartirgandan keyin Docker Compose'ni qayta ishga tushiring: `docker compose up -d`. Xavfsizlik uchun kodga kalit yozmang va terminal buyrug'i argumenti sifatida bermang.

Rasm/video yaratish uchun Gemini API kaliti shart. Rasm modeli (`gemini-3.1-flash-lite-image`) va video modeli (`veo-3.1-generate-preview`) Google API kvotasi, hisob mavjudligi va tarif shartlariga muvofiq ishlaydi. Video yaratish bir necha daqiqa olishi mumkin. Agar kalit chat yoki terminalda oshkor bo'lgan bo'lsa, Google AI Studio'da bekor qiling va yangisini yarating.

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
