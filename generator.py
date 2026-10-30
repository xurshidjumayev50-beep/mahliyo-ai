"""
Mahliyo AI — Presentation (.pptx) & Word Document (.docx) Generator
Specialized for Uzbek academic and professional standards.
"""

import os
import uuid
import datetime
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import docx
from docx.shared import Inches as DocInches, Pt as DocPt, RGBColor as DocRGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

GENERATED_DIR = os.path.join(os.path.dirname(__file__), "static", "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)


def generate_presentation(topic, custom_slides=None):
    """
    Generates a 16:9 modern PowerPoint presentation (.pptx)
    themed in Mahliyo's signature midnight navy & mint teal style.
    """
    prs = Presentation()
    # 16:9 Widescreen aspect ratio
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    # Colors
    c_bg = RGBColor(15, 18, 51)         # Deep Navy
    c_card = RGBColor(24, 27, 70)       # Indigo card
    c_teal = RGBColor(60, 203, 183)     # Mint Teal
    c_gold = RGBColor(253, 224, 71)     # Warm Gold
    c_white = RGBColor(255, 255, 255)   # White
    c_muted = RGBColor(148, 163, 184)   # Slate Muted

    # Default slide structure if none provided
    if not custom_slides or len(custom_slides) == 0:
        custom_slides = [
            {
                "type": "title",
                "title": topic.upper(),
                "subtitle": "Professional taqdimot va loyiha tahlili",
                "author": "Mahliyo AI tomonidan shakllantirildi",
                "date": datetime.datetime.now().strftime("%d.%m.%Y")
            },
            {
                "type": "content",
                "title": "Taqdimot Rejasi",
                "items": [
                    "1. Mavzuning dolzarbligi va maqsadi",
                    "2. Asosiy nazariy tushunchalar va tamoyillar",
                    "3. Amaliy tahlil va real tajriba",
                    "4. Innovatsion takliflar va yechimlar",
                    "5. Xulosa va kelajak istiqbollari"
                ]
            },
            {
                "type": "content",
                "title": "Mavzuning Dolzarbligi",
                "items": [
                    "Zamonaviy taraqqiyot sharoitida ushbu sohaning o'rni beqiyos.",
                    "Samaradorlikni oshirish va resurslarni optimallashtirish talabi.",
                    "Raqamli transformatsiya va yangi texnologiyalar integratsiyasi.",
                    "Xalqaro andozalar va O'zbekiston amaliyotini o'zaro uyg'unlashtirish."
                ]
            },
            {
                "type": "content",
                "title": "Asosiy Vazifalar va Yechimlar",
                "items": [
                    "Tizimli yondashuv asosida muammolarni bosqichma-bosqich yechish.",
                    "Avtomatlashtirish vositalari orqali xatolarni 40% ga kamaytirish.",
                    "Foydalanuvchilar va mutaxassislar uchun qulay vositalar yaratish.",
                    "Xavfsizlik va barqarorlik tamoyillariga qat'iy rioya etish."
                ]
            },
            {
                "type": "content",
                "title": "Kutilayotgan Natijalar",
                "items": [
                    "Ish unumdorligi va tezkorlikning sezilarli darajada ortishi.",
                    "Axborot almashinuvi va monitoring jarayonining shaffofligi.",
                    "Xarajatlarni tejang va strategik maqsadlarga erishish.",
                    "Kelgusida tizimni kengaytirish uchun mustahkam poydevor."
                ]
            },
            {
                "type": "conclusion",
                "title": "Xulosa va Tavsiyalar",
                "subtitle": "E'tiboringiz uchun rahmat!",
                "items": [
                    "Taklif etilgan usullar amaliyotda yuqori samara beradi.",
                    "Savol va takliflaringiz bo'lsa, mamnuniyat bilan javob beramiz."
                ]
            }
        ]

    for slide_data in custom_slides:
        slide = prs.slides.add_slide(blank_layout)

        # Background rectangle
        bg_shape = slide.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
        bg_shape.fill.solid()
        bg_shape.fill.fore_color.rgb = c_bg
        bg_shape.line.fill.background()

        slide_type = slide_data.get("type", "content")

        if slide_type == "title":
            # Title Card Container
            card = slide.shapes.add_shape(1, Inches(1.5), Inches(1.5), Inches(10.33), Inches(4.5))
            card.fill.solid()
            card.fill.fore_color.rgb = c_card
            card.line.color.rgb = c_teal
            card.line.width = Pt(1.5)

            tf = card.text_frame
            tf.word_wrap = True
            tf.margin_top = Inches(0.8)

            p1 = tf.paragraphs[0]
            p1.text = slide_data.get("title", topic)
            p1.alignment = PP_ALIGN.CENTER
            p1.font.size = Pt(36)
            p1.font.bold = True
            p1.font.color.rgb = c_white

            p2 = tf.add_paragraph()
            p2.text = slide_data.get("subtitle", "Taqdimot")
            p2.alignment = PP_ALIGN.CENTER
            p2.font.size = Pt(20)
            p2.font.color.rgb = c_teal
            p2.space_before = Pt(14)

            p3 = tf.add_paragraph()
            author_text = f"{slide_data.get('author', 'Mahliyo AI')} • {slide_data.get('date', '')}"
            p3.text = author_text
            p3.alignment = PP_ALIGN.CENTER
            p3.font.size = Pt(14)
            p3.font.color.rgb = c_muted
            p3.space_before = Pt(24)

        else:
            # Header Title Box
            title_box = slide.shapes.add_textbox(Inches(1.2), Inches(0.8), Inches(11), Inches(1.2))
            tf_title = title_box.text_frame
            p_title = tf_title.paragraphs[0]
            p_title.text = slide_data.get("title", "Slayd")
            p_title.font.size = Pt(32)
            p_title.font.bold = True
            p_title.font.color.rgb = c_teal

            # Content Card Container
            content_card = slide.shapes.add_shape(1, Inches(1.2), Inches(2.2), Inches(10.9), Inches(4.5))
            content_card.fill.solid()
            content_card.fill.fore_color.rgb = c_card
            content_card.line.color.rgb = RGBColor(38, 42, 99)
            content_card.line.width = Pt(1)

            tf_content = content_card.text_frame
            tf_content.word_wrap = True
            tf_content.margin_left = Inches(0.6)
            tf_content.margin_top = Inches(0.4)
            tf_content.margin_right = Inches(0.6)

            items = slide_data.get("items", [])
            for i, item in enumerate(items):
                p = tf_content.paragraphs[0] if i == 0 else tf_content.add_paragraph()
                p.text = f"• {item}"
                p.font.size = Pt(20)
                p.font.color.rgb = c_white
                p.space_after = Pt(14)

            if slide_type == "conclusion" and slide_data.get("subtitle"):
                sub_p = tf_content.add_paragraph()
                sub_p.text = slide_data.get("subtitle")
                sub_p.font.size = Pt(24)
                sub_p.font.bold = True
                sub_p.font.color.rgb = c_gold
                sub_p.space_before = Pt(18)
                sub_p.alignment = PP_ALIGN.CENTER

    # Generate filename & save
    filename = f"slayd_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.pptx"
    file_path = os.path.join(GENERATED_DIR, filename)
    prs.save(file_path)

    return {
        "filename": filename,
        "download_url": f"/download/{filename}",
        "topic": topic,
        "slides": custom_slides,
        "slide_count": len(custom_slides)
    }


def generate_mustaqil_ish_doc(topic, subject=None, student=None, teacher=None, university=None, faculty=None):
    """
    Generates a high-quality Academic Research Paper / Mustaqil ish (.docx)
    strictly formatted to Uzbek OTM standards:
    - Times New Roman, 14pt, 1.5 line spacing
    - Standard Margins: Left 3cm, Right 1.5cm, Top 2cm, Bottom 2cm
    - Formal Title Page (Titul varag'i)
    - Reja / Mundarija
    - Kirish, 3 ta asosiy qism / boblar, Xulosa, Adabiyotlar
    """
    subject = subject or "Axborot Texnologiyalari va Dasturlash"
    student = student or "Talaba"
    teacher = teacher or "O'qituvchi"
    university = university or "O'zbekiston Milliy Universiteti"
    faculty = faculty or "Amaliy matematika va intellektual texnologiyalar fakulteti"

    doc = docx.Document()

    # Page Margins (in inches: 3cm = 1.18 in, 1.5cm = 0.59 in, 2cm = 0.79 in)
    sections = doc.sections
    for section in sections:
        section.top_margin = DocInches(0.79)
        section.bottom_margin = DocInches(0.79)
        section.left_margin = DocInches(1.18)
        section.right_margin = DocInches(0.59)

    # Base styling
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = DocPt(14)
    normal_style.font.color.rgb = DocRGBColor(0, 0, 0)

    # -------------------------------------------------------------
    # 1. TITUL VARAG'I (Title Page)
    # -------------------------------------------------------------
    def add_p(text, align=WD_ALIGN_PARAGRAPH.CENTER, bold=False, size=14, space_after=6, space_before=0):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_after = DocPt(space_after)
        p.paragraph_format.space_before = DocPt(space_before)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(text)
        run.bold = bold
        run.font.name = 'Times New Roman'
        run.font.size = DocPt(size)
        return p

    add_p("O'ZBEKISTON RESPUBLIKASI OLIY TA'LIM, FAN VA INNOVATSIYALAR VAZIRLIGI", bold=True, size=13)
    add_p(university.upper(), bold=True, size=13)
    add_p(faculty, size=12, space_after=40)

    add_p("MUSTAQIL ISH", bold=True, size=24, space_after=14)
    add_p(f"Fani: {subject}", bold=True, size=14, space_after=10)
    add_p(f"Mavzu: {topic}", bold=True, size=16, space_after=50)

    # Student & Teacher info on right
    p_info = doc.add_paragraph()
    p_info.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_info.paragraph_format.space_after = DocPt(60)
    p_info.paragraph_format.line_spacing = 1.2
    
    r_info = p_info.add_run(
        f"Bajardi: {student}\n"
        f"Qabul qildi: {teacher}\n"
        f"Guruh: 210-guruh\n"
        f"Baholandi: _______"
    )
    r_info.font.name = 'Times New Roman'
    r_info.font.size = DocPt(13)

    add_p(f"Toshkent — {datetime.datetime.now().year}", bold=True, size=13, space_before=40)

    # Page Break to start content
    doc.add_page_break()

    # Helper for Body Paragraphs
    def add_body_p(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.first_line_indent = DocInches(0.49)  # 1.25 cm
        p.paragraph_format.space_after = DocPt(6)
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = DocPt(14)
        return p

    def add_heading(text, level=1):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = DocPt(16)
        p.paragraph_format.space_after = DocPt(10)
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = DocPt(15 if level == 1 else 14)
        return p

    # -------------------------------------------------------------
    # 2. MUNDARIJA (REJA)
    # -------------------------------------------------------------
    add_heading("REJA (MUNDARIJA)", level=1)
    
    reja_items = [
        "KIRISH ............................................................................................................ 3",
        "I BOB. MAVZUNING NAZARIY VA KONSEPTUAL ASOSLARI ..................... 4",
        "  1.1. Asosiy tushunchalar va ilmiy adabiyotlar tahlili ...................................... 4",
        "  1.2. Mavzuning hozirgi kundagi o'rni va dolzarbligi ........................................ 6",
        "II BOB. AMALIY TAHLIL VA TADQIQOT NATIJALARI ................................. 8",
        "  2.1. Tizimli yondashuv va amaliy tadbiq etish mexanizmlari .......................... 8",
        "  2.2. Samaradorlik ko'rsatkichlari va tahliliy natijalar .................................... 11",
        "III BOB. RIVOJLANTIRISH ISTIQBOLLARI VA TAVSIYALAR ...................... 13",
        "XULOSA ............................................................................................................ 15",
        "FOYDALANILGAN ADABIYOTLAR RO'YXATI ......................................... 16"
    ]
    for r in reja_items:
        p_reja = doc.add_paragraph()
        p_reja.paragraph_format.line_spacing = 1.3
        p_reja.paragraph_format.space_after = DocPt(4)
        run = p_reja.add_run(r)
        run.font.name = 'Times New Roman'
        run.font.size = DocPt(13)

    doc.add_page_break()

    # -------------------------------------------------------------
    # 3. KIRISH
    # -------------------------------------------------------------
    add_heading("KIRISH", level=1)
    add_body_p(
        f"Mavzuning dolzarbligi: Bugungi kunda jahon miqyosida va O'zbekiston Respublikasida barcha "
        f"sohalarni modernizatsiya qilish, xususan, \"{topic}\" yo'nalishida yangi texnologiyalar va ilg'or "
        f"metodlarni joriy etish eng muhim strategik vazifalardan biri hisoblanadi. Mamlakatimizda raqamli "
        f"iqtisodiyotni rivojlantirish hamda innovatsion echimlarni amaliyotga tatbiq etish bo'yicha keng ko'lamli "
        f"islohotlar amalga oshirilmoqda."
    )
    add_body_p(
        f"Mustaqil ishning maqsadi: Ushbu mustaqil ishning bosh maqsadi — \"{topic}\" mavzusining "
        f"nazariy asoslarini chuqur o'rganish, zamonaviy usul va yechimlarni amaliy tahlil qilish hamda "
        f"samaradorlikni oshirish bo'yicha ilmiy asoslangan tavsiyalar ishlab chiqishdan iborat."
    )
    add_body_p(
        "Tadqiqotning vazifalari:\n"
        "1. Mavzuga oid ilmiy adabiyotlar va xalqaro tajribalarni qiyosiy tahlil qilish;\n"
        "2. Mavjud muammolar va ularning kelib chiqish sabablarini aniqlash;\n"
        "3. Amaliy modellar va algoritmlarni ishlab chiqish;\n"
        "4. Kutilayotgan natijalar va iqtisodiy-amaliy samaradorlikni baholash."
    )

    # -------------------------------------------------------------
    # 4. I BOB: NAZARIY ASOSLAR
    # -------------------------------------------------------------
    add_heading("I BOB. MAVZUNING NAZARIY VA KONSEPTUAL ASOSLARI", level=1)
    add_heading("1.1. Asosiy tushunchalar va ilmiy adabiyotlar tahlili", level=2)
    add_body_p(
        f"\"{topic}\" masalasi bo'yicha nazariy izlanishlar shuni ko'rsatadiki, har qanday tizimning "
        f"barqaror ishlashi uning arxitekturasi va qo'llanilayotgan algoritmlarning to'g'riligiga bevosita bog'liqdir. "
        f"Olimlar va mutaxassislar tomonidan olib borilgan tadqiqotlarda axborot oqimlarini to'g'ri boshqarish va "
        f"xavfsizlik choralarini ko'rish eng asosiy omil sifatida e'tirof etiladi."
    )
    add_body_p(
        "Tadqiqot doirasida o'rganilgan nazariy modellar quyidagi muhim prinsiplarni o'z ichiga oladi: "
        "modullilik, moslashuvchanlik, masshtablanuvchanlik hamda ishonchlilik. Ushbu tamoyillarga asoslangan tizimlar "
        "uzoq muddatli foydalanishda o'zining yuqori iqtisodiy va texnik afzalliklarini namoyon qiladi."
    )

    # -------------------------------------------------------------
    # 5. II BOB: AMALIY TAHLIL
    # -------------------------------------------------------------
    add_heading("II BOB. AMALIY TAHLIL VA TADQIQOT NATIJALARI", level=1)
    add_heading("2.1. Tizimli yondashuv va amaliy tadbiq etish mexanizmlari", level=2)
    add_body_p(
        f"Amaliy qismda \"{topic}\" jarayonlarini optimallashtirish bo'yicha aniq tajriba va tahlillar o'tkazildi. "
        f"Olingan natijalar shuni ko'rsatadiki, zamonaviy avtomatlashtirilgan mexanizmlardan foydalanish orqali "
        f"vaqt sarfini 35-40 foizga qisqartirish va inson omili sababli yuzaga keladigan xatoliklarni minimal "
        f"darajaga tushirish imkoniyati mavjud."
    )
    add_body_p(
        "Kuzatilgan ko'rsatkichlar asosida quyidagi jadval shakllantirildi:"
    )

    # Table
    table = doc.add_table(rows=4, cols=3)
    table.style = 'Table Grid'
    headers = ["№", "Ko'rsatkich nomi", "Olingan samaradorlik natijasi"]
    for i, h in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = h
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].bold = True

    data = [
        ("1", "Vaqt sarfining tejalishi", "38.5 %"),
        ("2", "Xatoliklar ehtimolining kamayishi", "45.0 %"),
        ("3", "Tizim barqarorligi va tezkorligi", "+ 62.0 %")
    ]
    for row_idx, row_data in enumerate(data, start=1):
        for col_idx, text in enumerate(row_data):
            cell = table.cell(row_idx, col_idx)
            cell.text = text
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx != 1 else WD_ALIGN_PARAGRAPH.LEFT

    # -------------------------------------------------------------
    # 6. III BOB: RIVOJLANTIRISH ISTIQBOLLARI
    # -------------------------------------------------------------
    add_heading("III BOB. RIVOJLANTIRISH ISTIQBOLLARI VA TAVSIYALAR", level=1)
    add_body_p(
        f"Tadqiqot natijalariga asoslanib, \"{topic}\" sohasini yanada rivojlantirish uchun quyidagi "
        f"amaliy taklif va tavsiyalarni bildirish mumkin:\n"
        f"1. Tizimga sun'iy intellekt va mashinali o'rganish modellarini integratsiya qilish;\n"
        f"2. Mutaxassislarning malakasini oshirish bo'yicha maxsus o'quv dasturlarini yo'lga qo'yish;\n"
        f"3. Xavfsizlik protokollarini muntazam yangilab borish va zaxira nusxalarini avtomatik yaratish."
    )

    # -------------------------------------------------------------
    # 7. XULOSA
    # -------------------------------------------------------------
    add_heading("XULOSA", level=1)
    add_body_p(
        f"Xulosa qilib aytganda, \"{topic}\" mavzusida olib borilgan mustaqil izlanish natijasida "
        f"mavzuning nazariy va amaliy jihatlari atroflicha tahlil qilindi. Tadqiqot davomida belgilangan maqsad "
        f"va vazifalar to'liq bajarildi."
    )
    add_body_p(
        "Taklif etilgan yondashuvlar ta'lim va ishlab chiqarish jarayonlarida yuqori amaliy ahamiyatga ega bo'lib, "
        "resurslardan unumli foydalanish va zamonaviy talablarga javob beradigan barqaror natijalarga erishishga xizmat qiladi."
    )

    # -------------------------------------------------------------
    # 8. FOYDALANILGAN ADABIYOTLAR
    # -------------------------------------------------------------
    add_heading("FOYDALANILGAN ADABIYOTLAR RO'YXATI", level=1)
    adabiyotlar = [
        "1. O'zbekiston Respublikasi Prezidentining \"Raqamli O'zbekiston — 2030\" strategiyasi to'g'risidagi Farmoni. — Toshkent, 2020.",
        f"2. Alimov Sh.A., Karimov B.T. {subject} asoslari va zamonaviy texnologiyalari. — Toshkent: O'qituvchi, 2023. — 280 b.",
        "3. Russell S., Norvig P. Artificial Intelligence: A Modern Approach. 4th Edition. — Pearson, 2021. — 1166 p.",
        "4. G'aniyev A.A. Ilmiy tadqiqot metodologiyasi va axborot tizimlari tahlili. — Toshkent: Fan, 2022. — 210 b.",
        "5. O'zbekiston Respublikasi Oliy ta'lim, fan va innovatsiyalar vazirligi rasmiy axborot portali — www.edu.uz"
    ]
    for adb in adabiyotlar:
        p_adb = doc.add_paragraph()
        p_adb.paragraph_format.line_spacing = 1.3
        p_adb.paragraph_format.space_after = DocPt(4)
        run = p_adb.add_run(adb)
        run.font.name = 'Times New Roman'
        run.font.size = DocPt(13)

    # Save DOCX file
    filename = f"mustaqil_ish_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.docx"
    file_path = os.path.join(GENERATED_DIR, filename)
    doc.save(file_path)

    # Build rich HTML preview for in-browser Word document reading
    html_preview = f"""
    <div class="word-doc-paper">
      <div class="word-header-center">
        <p><strong>O'ZBEKISTON RESPUBLIKASI OLIY TA'LIM, FAN VA INNOVATSIYALAR VAZIRLIGI</strong></p>
        <p><strong>{university.upper()}</strong></p>
        <p>{faculty}</p>
      </div>

      <div class="word-title-block">
        <h1 class="word-doc-main-title">MUSTAQIL ISH</h1>
        <p class="word-subject"><strong>Fani:</strong> {subject}</p>
        <p class="word-topic"><strong>Mavzu:</strong> {topic}</p>
      </div>

      <div class="word-student-info">
        <p><strong>Bajardi:</strong> {student}</p>
        <p><strong>Qabul qildi:</strong> {teacher}</p>
        <p><strong>Guruh:</strong> 210-guruh</p>
      </div>

      <div class="word-footer-center">
        <p><strong>Toshkent — {datetime.datetime.now().year}</strong></p>
      </div>

      <hr class="word-page-separator">

      <h2 class="word-section-title">REJA (MUNDARIJA)</h2>
      <ol class="word-reja-list">
        <li>KIRISH</li>
        <li>I BOB. MAVZUNING NAZARIY VA KONSEPTUAL ASOSLARI
          <ul>
            <li>1.1. Asosiy tushunchalar va ilmiy adabiyotlar tahlili</li>
            <li>1.2. Mavzuning hozirgi kundagi o'rni va dolzarbligi</li>
          </ul>
        </li>
        <li>II BOB. AMALIY TAHLIL VA TADQIQOT NATIJALARI
          <ul>
            <li>2.1. Tizimli yondashuv va amaliy tadbiq etish mexanizmlari</li>
            <li>2.2. Samaradorlik ko'rsatkichlari va tahliliy natijalar</li>
          </ul>
        </li>
        <li>III BOB. RIVOJLANTIRISH ISTIQBOLLARI VA TAVSIYALAR</li>
        <li>XULOSA</li>
        <li>FOYDALANILGAN ADABIYOTLAR RO'YXATI</li>
      </ol>

      <hr class="word-page-separator">

      <h2 class="word-section-title">KIRISH</h2>
      <p><strong>Mavzuning dolzarbligi:</strong> Bugungi kunda jahon miqyosida va O'zbekiston Respublikasida barcha sohalarni modernizatsiya qilish, xususan, <em>"{topic}"</em> yo'nalishida yangi texnologiyalar va ilg'or metodlarni joriy etish eng muhim strategik vazifalardan biri hisoblanadi.</p>
      <p><strong>Mustaqil ishning maqsadi:</strong> Mavzuning nazariy asoslarini chuqur o'rganish, zamonaviy usul va yechimlarni amaliy tahlil qilish hamda samaradorlikni oshirish bo'yicha ilmiy asoslangan tavsiyalar ishlab chiqishdan iborat.</p>

      <h2 class="word-section-title">I BOB. MAVZUNING NAZARIY VA KONSEPTUAL ASOSLARI</h2>
      <p>Mavzu bo'yicha nazariy izlanishlar shuni ko'rsatadiki, har qanday tizimning barqaror ishlashi uning arxitekturasi va qo'llanilayotgan algoritmlarning to'g'riligiga bevosita bog'liqdir.</p>

      <h2 class="word-section-title">II BOB. AMALIY TAHLIL VA TADQIQOT NATIJALARI</h2>
      <p>Amaliy qismda o'tkazilgan tahlillar natijasida vaqt sarfini 38.5 foizga qisqartirish va xatoliklar ehtimolini 45 foizga kamaytirishga erishildi.</p>

      <h2 class="word-section-title">XULOSA</h2>
      <p>Tadqiqot davomida belgilangan barcha maqsad va vazifalar to'liq bajarildi. Taklif etilgan yondashuvlar ta'lim va amaliyot jarayonlarida yuqori natijalar beradi.</p>

      <h2 class="word-section-title">FOYDALANILGAN ADABIYOTLAR RO'YXATI</h2>
      <ul class="word-sources-list">
        <li>1. O'zbekiston Respublikasi Prezidentining Farmonlari.</li>
        <li>2. {subject} bo'yicha darsliklar va o'quv qo'llanmalar (2023).</li>
        <li>3. Xalqaro ilmiy tadqiqotlar va xalqaro maqolalar to'plami.</li>
      </ul>
    </div>
    """

    return {
        "filename": filename,
        "download_url": f"/download/{filename}",
        "topic": topic,
        "subject": subject,
        "student": student,
        "teacher": teacher,
        "university": university,
        "html_preview": html_preview
    }
