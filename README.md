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
- ⚡ **Tezkor va Ravon Muloqot:** Google Gemini 1.5 Flash / Pro va Gemini 2.0 modellari bilan to'liq integratsiya.
- 🧠 **Aqlli Lokal Rejim (Built-in Fallback):** Agar API kalit kiritilmagan bo'lsa ham, Mahliyo eng muhim mavzularda (slaydlar, arizalar, kod tahlili, sodda tushuntirishlar) avtomatik aqlli javob bera oladi.
- 📝 **Markdown va Kodlar Sintaksisi:** Python, JS, C++, SQL va boshqa tillardagi kodlarni chiroyli ranglar bilan ajratib ko'rsatish va 1 tugma bilan nusxa olish.
- 🗣️ **Ovozli O'qish (Text-to-Speech):** Mahliyo bergan javoblarni ovoz chiqarib o'qitish imkoniyati.
- 📁 **Fayl va Rasmlar Biriktirish:** Savollarga hujjat va rasmlarni ilova qilish imkoniyati.
- 💾 **Suhbatlar Tarixi (Persistent History):** Barcha yozishmalar saqlanib qoladi va istalgan vaqtda qayta ochilishi mumkin.
- 🐳 **Docker & Docker Compose:** 1 ta buyruq bilan konteynerda ishga tushirishga to'liq tayyor.

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
gunicorn --bind 0.0.0.0:5000 app:app
```

---

## 🔑 Gemini API Kalitini Sozlash

1. [Google AI Studio](https://aistudio.google.com/app/apikey) sahifasidan bepul API kalit oling.
2. Saytda chap pastdagi **"Kirish"** yoki tepadagi ⚙️ **Sozlamalar** tugmasini bosing.
3. Kalitni joylashtiring va **"Saqlash"** tugmasini bosing.
4. Yoki `.env` fayliga yozing:
```env
GEMINI_API_KEY=AIzaSy...
```

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
- **Versiya:** 1.0.0
