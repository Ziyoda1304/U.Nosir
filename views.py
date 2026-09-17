from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from collections import Counter
import os, re

from django.utils.safestring import mark_safe
from models import Biography, Work, Feedback

# O‘zbek tili uchun asosiy stopwords ro‘yxati
UZB_STOPWORDS = {
    "va", "bilan", "uchun", "ham", "esa", "lekin", "biroq", "yoki", "ammo", "yana","kim", "menga", "seni", "senga",
    "balki", "chunki", "shuning", "uchun", "dek", "day", "kabi", "na", "naq",
    "hatto", "hattoki", "shu", "bu", "u", "mana", "ana", "mana shu", "ana u",
    "faqat", "nafaqat", "barcha", "hamma", "har", "bir", "bor", "yo‘q", "edi", "hech",
    "ekan", "emish", "emas", "bo‘lib", "bo‘lgan", "qilgan", "etgan", "esa",
    "kelgan", "u", "sen", "men", "ketgan", "degan", "deb", "desam", "bo‘lsa", "o‘sha", "o‘zi"
}

# matnni tozalash va normalizatsiya

def _clean_text_meta(text: str) -> str:
    """She’r boshidagi sarlavhalarni (Muallif, Janr va h.k.) ehtiyotkorlik bilan o‘chiradi"""
    if not text:
        return ""
    
    lines = text.split('\n')
    cleaned_lines = []
    
    # Sarlavhada uchrashi aniq bo'lgan kalit so'zlar
    meta_keywords = ["muallif", "usmon", "nosir", "nomi", "yili", "janr", "mavjud emas"]
    
    for i, line in enumerate(lines):  #Qatorlarni raqamlash
        stripped = line.strip()         #Bo‘shliqlarni tozalash
        # Faqat matnning dastlabki 8 qatorini tekshiramiz
        if i < 8:
            is_meta = any(word in stripped.lower() for word in meta_keywords)
            is_star = stripped in ["*", "**", "***"]
            if is_meta or is_star or not stripped:
                continue
        
        cleaned_lines.append(line)
            
    return "\n".join(cleaned_lines)

_LETTERS = r"A-Za-zА-Яа-яЎўҒғҚқҲҳЁё"        #Harflarni aniqlash
_APOST = r"‘ʼʻ’'"
_token_re = re.compile(rf"[{_LETTERS}]+(?:[{_APOST}][{_LETTERS}]+)*")

def _normalize_token(t: str) -> str:
    """So'zni kichik harfga o'tkazish va tutuq belgilarini standartlash"""
    if not t: return ""
    t = t.lower().replace("'", "‘").replace("’", "‘").replace("ʼ", "‘").replace("ʻ", "‘")
    return re.sub(r"‘+", "‘", t)

# --- yordamchi funk/ ---

def _read_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:   #Xatolikni topish
        return ""

def _works_with_text():     #Asarlar bog‘lanishi
    items = []
    for w in Work.objects.all().order_by("title"):    #Eng yangi qo‘shilganlarini birinchi qilib saralash
        text = ""
        try:
            if w.txt_file and hasattr(w.txt_file, "path"):  # Faylning xotiradagi manzili mavjudligini tasdiqlash
                text = _read_text_file(w.txt_file.path)     #Fayl ichidagi matnni satr ko‘rinishida o‘qish
        except Exception:
            text = ""
#items.append: sarlavha va matnni lug‘at shaklida asosiy ro‘yxatga qo‘shish
        items.append({"title": w.title, "text": text.strip() or "Matn topilmadi."}) 
    return items

def _split_sentences(text: str):
    if not text: return []
    text = text.replace("\r", " ").replace("\n", " ")
    parts = re.split(r'(?<=[.!?…])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def index(request):
    biography = Biography.objects.first()   #Bazadan eng birinchi biografiya ma'lumotini oladi
    works_data = _works_with_text()         #Oldingi funksiyani chaqirib, asarlar ro‘yxatini tayyorlaydi
    txt_path = os.path.join(settings.MEDIA_ROOT, "she_r.txt")   #Media papkasidagi she_r.txt fayliga boradigan yo'lni yasaydi
    she_r_text = _read_text_file(txt_path).strip()  #Shu faylni o‘qiydi va chetidagi bo‘shliqlarni olib tashlaydi
    return render(request, "index.html", {
        "biography": biography, 
        "works_data": works_data, 
        "she_r_text": she_r_text
    })    

def qidiruv(request):
    q = (request.GET.get("q") or "").strip()    #Sayt qidiruv paneliga yozilgan so‘zni qabul qilib oladi
    works_data = _works_with_text() #Barcha asarlar va ularning matnlarini xotiraga yuklaydi
    results, total_hits = [], 0

    if q:
        #Regulyar ifoda yordamida qidiruv qolipini yaratadi
        #(?<![{_LETTERS}]): Qidirilayotgan so‘zning oldida boshqa harf yo‘qligini tekshiradi
        #(?![{_LETTERS}]):	Qidirilayotgan so‘zning ketidan boshqa harf kelmasligini tekshiradi.
        pattern = re.compile(rf"(?<![{_LETTERS}]){re.escape(q)}(?![{_LETTERS}])", re.IGNORECASE)  
        for w in works_data:
            cleaned = _clean_text_meta(w["text"])   #Matndagi texnik belgilarni tozalab, faqat asosiy qismni qoldiradi
            # Gaplarni bo'yash uchun snippet tayyorlash
            sentences = _split_sentences(cleaned)   #Tozalangan yaxlit matnni alohida gaplarga bo‘lib chiqadi
            found_sentences = []
            for s in sentences:
                if pattern.search(s):   #Har bir gap ichidan foydalanuvchi qidirgan so‘zni qidiradi
                    #Topilgan so‘zni <mark> tegi ichiga oladi (bu HTML'da so‘zning orqasini sarg‘ish rangga bo‘yaydi)
                    #m.group(0): matn ichida aynan qanday yozilgan bo'sa (masalan, "Sen" yoki "sen"), o'shani o'zgarishsiz saqlab qoladi
                    painted = pattern.sub(lambda m: f'<mark class="hit">{m.group(0)}</mark>', s)
                    found_sentences.append(painted)
                if len(found_sentences) >= 3: break #Bitta asardan ko‘pi bilan 3 ta namuna gap oladi 
            
            hits = len(pattern.findall(cleaned))    #Matn ichida qidirilayotgan so‘z necha marta takrorlanganini aniqlaydi
            if hits > 0:    #Agar so‘z kamida bir marta topilgan bo‘lsa, ushbu asarni natijalar ro‘yxatiga qo‘shadi
                results.append({
                    "title": w["title"], 
                    "hits": hits,
                    #HTML teglarni (masalan, <mark>) xavfsiz deb belgilaydi, aks holda brauzer ularni oddiy matn deb o‘ylaydi.
                    "snippet": mark_safe("<br>".join(found_sentences))
                })
                total_hits += hits  #Butun sayt bo‘yicha topilgan barcha so‘zlar sonini umumiy hisoblab boradi.
        results.sort(key=lambda x: x["hits"], reverse=True) #Natijalarni so‘z eng ko‘p uchragan asardan boshlab kamayish tartibida saralaydi

    return render(request, "qidiruv.html", {
        "q": q, "results": results, 
        "total_hits": total_hits, "works_count": len(works_data)
    })

def kwic(request):
    """Kalit so‘zni matn konteksti (chap, o‘ng yoki ikkala) bilan ko‘rsatish"""
    q = (request.GET.get("q") or "").strip()
    taraf = request.GET.get("taraf") or "ikkala"  # HTML dan kelayotgan taraf parametri
    window = 60 
    works_data = _works_with_text()
    lines = []

    if q:
        # So'z chegarasini hisobga olgan regex
        pattern = re.compile(rf"(?<![{_LETTERS}]){re.escape(q)}(?![{_LETTERS}])", re.IGNORECASE)
        
        for w in works_data:
            # Sarlavhalarsiz matndan qidiramiz
            search_text = _clean_text_meta(w["text"])
            
            for m in pattern.finditer(search_text):
                start, end = m.start(), m.end()
                
                # Chap va o'ng kontekstni qirqib olamiz
                #Topilgan so‘zdan chapga qarab ma’lum masofani (window) belgilaydi.
                # max(0, ...) qismi matn boshidan o‘tib ketmaslikni (manfiy indeksga tushmaslikni) ta’minlaydi
                #Matnning boshidan to topilgan so‘z boshlanguncha bo‘lgan qismni (chap tomonni) qirqib oladi
                # Topilgan so‘z tugagan joydan (end) o‘ngga qarab ma’lum masofani (o‘ng tomonni) qirqib oladi
                #Qirqib olingan matn bo‘laklari ichidagi yangi qatorga o‘tish belgilarini bo‘sh joy (probel) bilan almashtiradi
                left_part = search_text[max(0, start-window):start].replace("\n", " ")
                right_part = search_text[end:end+window].replace("\n", " ")
                
                # Foydalanuvchi tanlagan "taraf"ga qarab kontekstni shakllantiramiz
                display_left = ""
                display_right = ""
                
                if taraf == "chap":
                    display_left = left_part
                    display_right = ""  # O'ng tomon bo'sh
                elif taraf == "ong":
                    display_left = ""   # Chap tomon bo'sh
                    display_right = right_part
                else:  # "ikkala" bo'lganda
                    display_left = left_part
                    display_right = right_part
                
                lines.append({
                    "title": w["title"],
                    "left": display_left,
                    "word": m.group(),
                    "right": display_right
                })
                
    return render(request, "kwic.html", {
        "lines": lines, 
        "q": q, 
        "taraf": taraf
    })

def collocation(request):
    """Sizda yo'qolgan funksiya - yonma so'zlar statistikasi"""
    q = (request.GET.get("q") or "").strip()
    works_data = _works_with_text()
    neighbors = []
    
    if q:
        norm_q = _normalize_token(q)
        for w in works_data:
            # Sarlavhalarsiz matndan so'zlarni ajratamiz
            words = [_normalize_token(t) for t in _token_re.findall(_clean_text_meta(w["text"]))]
            for i, word in enumerate(words):
                if word == norm_q:
                    if i > 0: neighbors.append(words[i-1])
                    if i < len(words)-1: neighbors.append(words[i+1])
    
    collocations = Counter(neighbors).most_common(20)
    return render(request, "collocation.html", {"q": q, "collocations": collocations})

def ngram(request):
    n = int(request.GET.get("n", 2))
    works_data = _works_with_text()
    full_text = " ".join([_clean_text_meta(w["text"]) for w in works_data])
    words = [_normalize_token(t) for t in _token_re.findall(full_text)]
    grams = zip(*[words[i:] for i in range(n)])
    result = Counter(grams).most_common(20)
    return render(request, "ngram.html", {"n": n, "result": result})

def statistika(request):
    works_data = _works_with_text()
    all_text = "\n".join([_clean_text_meta(w["text"]) for w in works_data if w["text"] != "Matn topilmadi."])
    tokens = [_normalize_token(t) for t in _token_re.findall(all_text)]
    total_tokens = len(tokens)
    top_words = Counter(tokens).most_common(20)
    return render(request, "statistika.html", {
        "works_count": len(works_data), 
        "total_tokens": total_tokens, 
        "top_words": top_words
    })

def statistika(request):
    """Stopwordslarsiz umumiy so‘zlar statistikasi"""
    works_data = _works_with_text()
    all_text = "\n".join([_clean_text_meta(w["text"]) for w in works_data if w["text"] != "Matn topilmadi."])

    # Matnni so'zlarga ajratish va normalizatsiya qilish
    tokens = [_normalize_token(t) for t in _token_re.findall(all_text)]
    
    # Filtr: faqat stopwords ro'yxatida bo'lmagan so'zlarni olamiz
    filtered_tokens = [t for t in tokens if t and t not in UZB_STOPWORDS]
    
    total_tokens = len(filtered_tokens)
    top_words = Counter(filtered_tokens).most_common(20)

    return render(request, "statistika.html", {
        "works_count": len(works_data),
        "total_tokens": total_tokens,
        "top_words": top_words
    })

def aloqa(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        msg = request.POST.get("message", "").strip()
        if name and msg:
            Feedback.objects.create(name=name, email=request.POST.get("email"), message=msg)
            messages.success(request, "Xabaringiz yuborildi. Rahmat!")  #Muvaffaqiyatli yakun-->success
            return redirect("aloqa")
    return render(request, "aloqa.html")
