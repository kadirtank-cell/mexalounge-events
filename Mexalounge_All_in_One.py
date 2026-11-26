<<<<<<< HEAD
import os
import re
import time
import json
import pickle
import sqlite3
import subprocess
import threading
import warnings
from pathlib import Path
import schedule
import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import cloudscraper
import pymysql
import discord
from discord import app_commands
from google.cloud import texttospeech
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from urllib.parse import urlparse

# BeautifulSoup uyarılarını bastırıyoruz
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Google Cloud JSON anahtar dosyasının yolu
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    r"C:\Users\kadir\Desktop\Radyo Botu\mexalounge-radio-0926e73fdef7.json"
)

# Blogger API yetki kapsamı
SCOPES = ['https://www.googleapis.com/auth/blogger']

# Discord Webhook URL'leri
WEBHOOK_URL = "https://discord.com/api/webhooks/1571511090221686975/1jZqd-8O4OyoW5NJABEzogARDvEByswt_g5KekXSLmVB7ntdoT_uUgB7W20swxXGEjaM"
EVENT_WEBHOOK_URL = "https://discord.com/api/webhooks/1571517049971286197/TP4yUgreitR1v4lYZjO4nDZ7CztNwOyCE2Re_pHWcSRSTAlcLcK1yRCXICaUyC3REmgl"
TOP20_WEBHOOK_URL = "https://discord.com/api/webhooks/1571520094088077423/JmseMit8wivblmJQYJV2RqII2r8yNP2L8COve_l19cOCHERo_Fazdl7XHBHjF4pG9Qcj"


# =============================================================================
## 1. BÖLÜM: GLOBAL EVENT RADAR (XCEED) & RADYODJ MYSQL & GİTHUB & DİSCORD OTOMASYONU
# =============================================================================

xceed_urls = [
    "https://xceed.me/en/barcelona/events",
    "https://xceed.me/en/roma/events",
    "https://xceed.me/en/brussels/events",
    "https://xceed.me/en/hamburg/events",
    "https://xceed.me/en/artist/carl-cox",
    "https://xceed.me/en/artist/charlotte-de-witte",
    "https://xceed.me/en/london/events",
    "https://xceed.me/en/artist/amelie-lens"
]

scraper_xceed = cloudscraper.create_scraper()

def send_top20_to_discord():
    """Top 20 listesini kontrol eder ve Discord webhook'una gönderir."""
    print("Top20 Discord gönderimi başladı...")

    if not os.path.exists("top20.json"):
        print("top20.json bulunamadı.")
        return

    with open("top20.json", "r", encoding="utf-8") as f:
        tracks = json.load(f)

    if len(tracks) == 0:
        print("top20.json boş.")
        return

    mesaj = "🏆 **MEXALOUNGE RADIO TOP 20** 🏆\n\n"

    for track in tracks:
        rank = track.get("rank", "?")
        artist = track.get("artist", "Unknown Artist")
        title = track.get("title", "Unknown Title")
        plays = track.get("play_count", 0)

        if rank == 1:
            prefix = "🥇"
        elif rank == 2:
            prefix = "🥈"
        elif rank == 3:
            prefix = "🥉"
        else:
            prefix = f"#{rank}"

        mesaj += (
            f"{prefix} **{artist}**\n"
            f"🎵 {title}\n"
            f"▶️ Plays: {plays}\n\n"
        )

    mesaj += "📻 Mexalounge Radio"

    response = requests.post(
        TOP20_WEBHOOK_URL,
        json={"content": mesaj}
    )

    print("Discord Status:", response.status_code)

    if response.status_code in [200, 204]:
        print("Top20 başarıyla gönderildi.")
    else:
        print(response.text)


def send_event_to_discord():
    """Global etkinlikleri kontrol eder ve yeni etkinliği Discord webhook'una bildirir."""
    print("Global Event kontrolü başladı...")

    if not os.path.exists("events.json"):
        print("events.json bulunamadı.")
        return

    with open("events.json", "r", encoding="utf-8") as f:
        events = json.load(f)

    if len(events) == 0:
        print("Etkinlik bulunamadı.")
        return

    event = events[0]

    title = event.get("title", "Unknown Event")
    date = event.get("date", "TBA")
    location = event.get("location", "GLOBAL")
    link = event.get("link", "")

    print("Etkinlik:", title)

    last_event_file = "last_discord_event.txt"
    previous_event = ""

    if os.path.exists(last_event_file):
        with open(last_event_file, "r", encoding="utf-8") as f:
            previous_event = f.read().strip()

    if link == previous_event:
        print("Bu etkinlik daha önce gönderilmiş.")
        return

    message = {
        "content":
        f"🌍 **New Global Event**\n\n"
        f"🎉 **{title}**\n"
        f"📍 {location}\n"
        f"📅 {date}\n\n"
        f"🔗 {link}"
    }

    response = requests.post(EVENT_WEBHOOK_URL, json=message)

    print("Discord Status:", response.status_code)

    if response.status_code in [200, 204]:
        with open(last_event_file, "w", encoding="utf-8") as f:
            f.write(link)
        print("Discord'a başarıyla gönderildi.")
    else:
        print(response.text)


def fetch_events():
    """Xceed üzerinden global elektronik müzik etkinliklerini tarar, events.json'a kaydeder ve Discord'a bildirir."""
    all_events = []
    print("\n--- Global Event Radar Taraması Başlıyor ---")

    for url in xceed_urls:
        try:
            print(f"Taranıyor: {url}")
            response = scraper_xceed.get(url, timeout=20)
            
            if response.status_code != 200:
                print(f"Bağlantı hatası code: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("a", href=True)
            found_count = 0

            url_parts = url.strip("/").split("/")
            extracted_name = "GLOBAL"
            if "artist" in url_parts and len(url_parts) > url_parts.index("artist") + 1:
                extracted_name = url_parts[url_parts.index("artist") + 1].replace("-", " ").upper()
            elif len(url_parts) > 4:
                extracted_name = url_parts[4].replace("-", " ").upper()

            for card in cards:
                href = card.get("href", "")
                if "/event/" not in href:
                    continue

                event_link = href if href.startswith("http") else "https://xceed.me" + href

                try:
                    title_elem = card.find("h3") or card.find("h4") or card.find("p")
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    if not title or len(title) < 3:
                        title = card.get_text(strip=True)

                    if len(title) < 3 or "GEÇMİŞ" in title.upper() or "YAKLAŞAN" in title.upper():
                        continue

                    date_text = ""
                    for text_item in card.stripped_strings:
                        if any(m in text_item.lower() for m in ["kas", "ara", "oca", "sub", "mar", "nis", "may", "haz", "tem", "ağu", "eyl", "okt", "2026"]):
                            date_text = text_item
                            break

                    if not date_text or len(date_text) < 3:
                        date_text = "TBA (SOON)"

                    img_elem = card.find("img")
                    img_url = img_elem.get("src") or img_elem.get("data-src") if img_elem else ""

                    event_data = {
                        "title": title[:65],
                        "date": date_text[:35],
                        "location": extracted_name,
                        "image": img_url,
                        "link": event_link,
                    }
                    
                    if event_data not in all_events and event_link not in [e["link"] for e in all_events]:
                        all_events.append(event_data)
                        found_count += 1

                except Exception:
                    continue

            print(f"Başarılı: {found_count} adet etkinlik çekildi.")
        except Exception as e:
            print(f"Hata oluştu {url}: {e}")

    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=4)
    print("events.json güncellendi.")


# --- KARA LİSTE (JİNGLE, REKLAM VE ANONSLARI ELEMEK İÇİN) ---
BLACKLIST_KEYWORDS = [
    "church-bells", "presentation-logo", "radio-for-all", "kamuspotu", "kamu spotu", 
    "radyo spotu", "spotu", "lösev", "tühsev", "darussafaka", "darüşşafaka", 
    "tev okula donus", "jingle", "intro", "tohum otizm vakfı", "türkiye spastik çocuklar vakfı", 
    "tkd kamu spotu", "canım kardeşim", "swepper", "mexalounge radio", "radio1", "radio2",
    "radio4", "radio3", "radio5", "presentation-logo-version-beat-way-up", "radio-for-all-trance-505926", 
    "Reklam-Teaser", "Mexalounge News", "News Teaser"
]

def build_blacklist_sql_condition():
    """MySQL sorguları için kara liste filtre koşullarını hazırlar."""
    conditions = []
    for word in BLACKLIST_KEYWORDS:
        w = word.lower()
        conditions.append(f"LOWER(title) NOT LIKE '%{w}%'")
        conditions.append(f"LOWER(artist) NOT LIKE '%{w}%'")
    return " AND ".join(conditions)


def send_now_playing():
    """Radyoda o an çalan şarkıyı kontrol eder ve değiştiyse Discord webhook'una bildirir."""
    print("--- Discord 'Now Playing' Kontrol Ediliyor ---")
    try:
        if not os.path.exists("history.json"):
            print("history.json bulunamadı.")
            return

        with open("history.json", "r", encoding="utf-8") as f:
            history = json.load(f)

        if len(history) == 0:
            print("history.json boş.")
            return

        last = history[0]

        artist = last["artist"]
        title = last["title"]
        time_ = last["time"]

        current_track = f"{artist} - {title}"

        last_track_file = "last_discord_track.txt"
        previous_track = ""

        if os.path.exists(last_track_file):
            with open(last_track_file, "r", encoding="utf-8") as f:
                previous_track = f.read().strip()

        if current_track == previous_track:
            print("Şarkı değişmemiş, Discord bildirimi atlandı.")
            return

        message = {
            "content":
            f"🎵 **Now Playing**\n\n"
            f"🎤 Artist: {artist}\n"
            f"🎶 Track: {title}\n"
            f"⏰ Time: {time_}\n\n"
            f"📻 Mexalounge Radio"
        }

        response = requests.post(WEBHOOK_URL, json=message)

        print("Discord Status:", response.status_code)

        if response.status_code in [200, 204]:
            with open(last_track_file, "w", encoding="utf-8") as f:
                f.write(current_track)
            print("Discord mesajı başarıyla gönderildi.")
        else:
            print("Discord hata yanıtı:", response.text)

    except Exception as e:
        print(f"⚠️ Discord webhook gönderim hatası: {e}")


def fetch_radio_history():
    """RadyoDJ MySQL veritabanından son çalan parçaları çeker ve history.json'a kaydeder."""
    print("--- RadyoDJ Geçmiş Parçalar Güncelleniyor ---")
    try:
        db = pymysql.connect(
            host="127.0.0.1", user="root", password="", database="radiodj3",
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, connect_timeout=5
        )
        
        with db.cursor() as cursor:
            blacklist_filter = build_blacklist_sql_condition()
            query = f"""
                SELECT artist, title, date_played 
                FROM history 
                WHERE {blacklist_filter} 
                ORDER BY id DESC 
                LIMIT 10
            """
            cursor.execute(query)
            result = cursor.fetchall()
            
            tracks = []
            for row in result:
                tracks.append({
                    "artist": row["artist"] if row["artist"] else "Unknown Artist",
                    "title": row["title"] if row["title"] else "Unknown Title",
                    "time": str(row["date_played"]) if row["date_played"] else ""
                })
                
            with open("history.json", "w", encoding="utf-8") as f:
                json.dump(tracks, f, ensure_ascii=False, indent=4)
                
            print("history.json güncel ve filtrelenmiş RadyoDJ verileriyle yenilendi.")
        db.close()

        # Geçmiş güncellendikten hemen sonra Discord kontrolünü tetikle
        send_now_playing()

    except Exception as e:
        print(f"\n[!] MYSQL HATA YAKALANDI (History): {e}\n")


def fetch_top_tracks():
    """RadyoDJ MySQL veritabanından son 30 günün en çok çalan ilk 20 parçasını çeker."""
    print("--- Top 20 En Çok Çalan Şarkılar Güncelleniyor ---")
    try:
        db = pymysql.connect(
            host="127.0.0.1", user="root", password="", database="radiodj3",
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, connect_timeout=5
        )
        
        with db.cursor() as cursor:
            blacklist_filter = build_blacklist_sql_condition()
            query = f"""
                SELECT artist, title, COUNT(*) as play_count 
                FROM history 
                WHERE date_played >= NOW() - INTERVAL 30 DAY 
                AND {blacklist_filter} 
                GROUP BY artist, title 
                ORDER BY play_count DESC 
                LIMIT 20
            """
            cursor.execute(query)
            result = cursor.fetchall()
            
            top_tracks = []
            for rank, row in enumerate(result, start=1):
                top_tracks.append({
                    "rank": rank,
                    "artist": row["artist"] if row["artist"] else "Unknown Artist",
                    "title": row["title"] if row["title"] else "Unknown Title",
                    "play_count": row["play_count"]
                })
                
            with open("top20.json", "w", encoding="utf-8") as f:
                json.dump(top_tracks, f, ensure_ascii=False, indent=4)
                
            print("top20.json son 30 günlük filtrelenmiş verilerle güncellendi.")
        db.close()
    except Exception as e:
        print(f"\n[!] MYSQL HATA YAKALANDI (Top 20): {e}\n")


def push_to_github():
    """Dosyalar değiştiyse GitHub'a gönderir."""
    print("--- GitHub Güncellemesi Kontrol Ediliyor ---")
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )

        if not status.stdout.strip():
            print("✅ Değişiklik yok. GitHub push atlandı.")
            return

        print("📦 Değişiklik bulundu. GitHub'a gönderiliyor...")

        subprocess.run(
            ["git", "add", "history.json", "events.json", "top20.json"],
            check=True
        )

        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "Bot update: history, events, top20"
            ],
            check=True
        )

        subprocess.run(
            ["git", "push"],
            check=True
        )

        print("✅ GitHub başarıyla güncellendi.")

    except Exception as e:
        print(f"⚠️ GitHub güncelleme hatası: {e}")


def ithub_and_events_loop():
    """15 dakikalık aralıklarla Xceed, MySQL, GitHub senkronizasyonunu ve Discord bildirimlerini yürütür."""
    print("🔄 15 dakikalık Xceed/MySQL/GitHub döngü iş parçacığı başlatıldı.")
    
    son_sabah_tarihi = None
    son_aksam_tarihi = None
    son_top20_tarihi = None

    while True:
        try:
            start_time = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n=== [15dk Döngü] Başlangıç Zamanı (UTC): {start_time} ===")
            
            simdi_utc = time.gmtime()
            bugun = (simdi_utc.tm_year, simdi_utc.tm_mon, simdi_utc.tm_mday)
            saat = simdi_utc.tm_hour
            dakika = simdi_utc.tm_min

            # Sabah Haberi: UTC 08:00
            if saat == 8 and dakika < 15:
                if son_sabah_tarihi != bugun:
                    print("☀️ [UTC Zaman Penceresi] Sabah haberi (DJ Mag) tetikleniyor...")
                    sabah_haber_gorevi()
                    son_sabah_tarihi = bugun

            # Akşam Haberi: UTC 18:00
            if saat == 18 and dakika < 15:
                if son_aksam_tarihi != bugun:
                    print("🌙 [UTC Zaman Penceresi] Akşam haberi (DJ Rankings) tetikleniyor...")
                    aksam_haber_gorevi()
                    son_aksam_tarihi = bugun

            # Top 20 Discord Gönderimi: Her gün UTC 18:00'de
            if saat == 18 and dakika < 15:
                if son_top20_tarihi != bugun:
                    print("🏆 [UTC Zaman Penceresi] Top 20 Discord bildirimi tetikleniyor...")
                    fetch_top_tracks()      # Önce top20.json'u güncel verilerle yenile
                    send_top20_to_discord() # Sonra Discord'a gönder
                    son_top20_tarihi = bugun

            fetch_events()         # İçinde send_event_to_discord() çağrılır
            fetch_radio_history()  # İçinde send_now_playing() çağrılır
            fetch_top_tracks()
            push_to_github()
            
            print(f"[15dk Döngü] İşlem tamamlandı.")
        except Exception as e:
            print(f"15dk Döngü sırasında hata oluştu: {e}")

        total_seconds = 15 * 60
        while total_seconds > 0:
            mins, secs = divmod(total_seconds, 60)
            timer_format = f"{mins:02d}:{secs:02d}"
            print(f"⏳ Sonraki güncellemeye kalan süre: {timer_format}", end="\r")
            time.sleep(1)
            total_seconds -= 1
        print("\n")


# =============================================================================
## 2. BÖLÜM: BLOGGER OTOMATİK HABER BOTU (SABAH DJ MAG & AKŞAM DJ RANKINGS)
# =============================================================================

def get_blogger_service():
    """Blogger API bağlantısını ve yetkilendirme nesnesini döndürür."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("❌ HATA: 'credentials.json' dosyası bulunamadı!")
                return None
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('blogger', 'v3', credentials=creds)


def is_already_posted(service, blog_id, news_link):
    """Blogger'daki son postları kontrol ederek aynı haberin daha önce paylaşılıp paylaşılmadığını denetler."""
    try:
        posts = service.posts().list(blogId=blog_id, maxResults=20).execute()
        norm_news_link = news_link.rstrip('/')
        
        if 'items' in posts:
            for post in posts['items']:
                content = post.get('content', '')
                title = post.get('title', '')
                if norm_news_link in content or news_link in content:
                    print(f"ℹ️ [Kontrol] Bu haber daha önce paylaşılmış: '{title}'")
                    return True
    except Exception as e:
        print(f"⚠️ Post kontrolü sırasında hata oluştu: {e}")
    return False


def haber_botu(index_url, ogun_etiketi):
    """Belirtilen kaynak siteden en güncel haberi çeker, mükerrer kontrolü yapar ve Blogger'da yayınlar."""
    print(f"\n==================================================")
    print(f"🕒 İşlem Zamanı (UTC): {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}")
    print(f"--- {ogun_etiketi} Haberi Kontrolü Başlıyor ---")
    print(f"[*] Hedef Kaynak: {index_url}")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(index_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"❌ Sayfaya ulaşılamadı. Kod: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        news_link = ""
        parsed_base = urlparse(index_url)
        base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        if "djmag.com" in index_url:
            candidates = soup.find_all(['div', 'article'], class_=lambda x: x and ('row' in x or 'item' in x or 'article' in x))
            for candidate in candidates:
                a_tag = candidate.find('a', href=True)
                if a_tag:
                    href = a_tag['href']
                    if ("/news/" in href or "/tech/" in href or "/features/" in href) and href != index_url:
                        news_link = href if href.startswith('http') else base_domain + href
                        break
            if not news_link:
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    if ("/news/" in href or "/tech/" in href) and href != index_url and "tag" not in href:
                        news_link = href if href.startswith('http') else base_domain + href
                        break
        
        elif "djrankings.org" in index_url:
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if "news=" in href or "article" in href or "post" in href:
                    news_link = href if href.startswith('http') else base_domain + href
                    break
            if not news_link:
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    if href != index_url and len(href) > 15 and not "tag" in href:
                        news_link = href if href.startswith('http') else base_domain + href
                        break

        if not news_link:
            print("❌ Güncel haber linki bulunamadı!")
            return
            
        print(f"✅ Yakalanan en güncel haber linki: {news_link}")
        
        service = get_blogger_service()
        if not service: return
        blogs = service.blogs().listByUser(userId='self').execute()
        blog_id = blogs['items'][0]['id']

        if is_already_posted(service, blog_id, news_link):
            print(f"⏭️ Bu haber zaten Blogger'da mevcut. Yeni haber bekleniyor, atlanıyor...")
            return

        print(f"[*] Haber detayları indiriliyor...")
        news_response = requests.get(news_link, headers=headers, timeout=15)
        if news_response.status_code != 200:
            print(f"❌ Haber detay sayfasına ulaşılamadı. Kod: {news_response.status_code}")
            return
            
        news_soup = BeautifulSoup(news_response.text, 'html.parser')

        title_elem = news_soup.find('h1') or news_soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else "Mexalounge Radio News"

        paragraflar = []
        for p in news_soup.find_all('p'):
            text = p.get_text(strip=True)
            if len(text) > 30 and not any(w in text.lower() for w in ["cookie", "subscribe", "all rights", "privacy", "thrust publishing"]):
                paragraflar.append(text)
                if len(paragraflar) == 2:
                    break
                    
        paragraf_html = "".join([f"<p>{p}</p>" for p in paragraflar]) if paragraflar else "<p>Latest updates from the electronic music world...</p>"

        img_url = ""
        og_img = news_soup.find('meta', property='og:image') or news_soup.find('meta', attrs={'name': 'twitter:image'})
        if og_img and og_img.get('content'):
            img_url = og_img['content']
        else:
            for img in news_soup.find_all('img'):
                src = img.get('src') or img.get('data-src', '')
                if src and not any(icon in src.lower() for icon in ["logo", "avatar", "icon", "banner", "footer"]):
                    img_url = src if src.startswith('http') else base_domain + src
                    break

        html_content = ""
        if img_url:
            html_content += f'<div style="text-align: center; margin-bottom: 20px;"><img src="{img_url}" style="max-width:100%; height:auto; border-radius: 8px;" /></div>'
        html_content += paragraf_html
        html_content += f'<br/><hr/><p><b>Source / Original Article:</b> <a href="{news_link}" target="_blank" rel="nofollow">Click here for the full story</a></p>'

        body = {'title': title, 'content': html_content}
        
        print(f"[*] Blogger'a gönderiliyor...")
        post = service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()
        print(f"🎉 YENİ HABER BAŞARIYLA YAYINLANDI: {post.get('url')}")

    except Exception as e:
        print(f"❌ İşlem sırasında hata oluştu: {e}")


def sabah_haber_gorevi():
    """Sabah yayınlanacak haber için DJ Mag kaynağını tetikler."""
    haber_botu("https://djmag.com/news", "SABAH (DJ Mag)")

def aksam_haber_gorevi():
    """Akşam yayınlanacak haber için DJ Rankings kaynağını tetikler."""
    haber_botu("https://djrankings.org/news", "AKŞAM (DJ Rankings)")


# =============================================================================
## 3. BÖLÜM: BBC HABERLERİ & GOOGLE CLOUD TTS SESLENDİRME
# =============================================================================

FILTRE_KAPLARI = [
    r"copyright",
    r"all rights reserved",
    r"not responsible for the content",
    r"external sites",
    r"external linking",
    r"read about our approach",
]

def metin_gecerli_mi(metin):
    """Haber metninde yasal uyarı veya telif kalıplarının olup olmadığını kontrol eder."""
    for kalip in FILTRE_KAPLARI:
        if re.search(kalip, metin, re.IGNORECASE):
            return False
    return True

def generate_google_cloud_news_mp3(url_listesi):
    """BBC haberlerini tarar, metinleri SSML formatına dönüştürür ve Google Cloud TTS ile MP3 bülten üretir."""
    output_filename = r"C:\Users\Kadir\Music\News\mexalounge_news.mp3"

    print("\n[*] [Zamanlayıcı Tetiklendi] Haber bülteni üretim süreci başlatılıyor...")
    print("[*] Google Cloud TTS istemcisi başlatılıyor...")
    client = texttospeech.TextToSpeechClient()

    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )

    toplam_linkler = []

    for url in url_listesi:
        print(f"[*] Hedef siteye bağlanılıyor: {url}")
        try:
            response = scraper.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"]

                if href.startswith("http") and href not in toplam_linkler:
                    if "/news/" in href or "world" in href or "us-canada" in href:
                        toplam_linkler.append(href)
                elif href.startswith("/") and len(href) > 5:
                    full_url = "https://www.bbc.com" + href
                    if full_url not in toplam_linkler:
                        toplam_linkler.append(full_url)
        except Exception as e:
            print(f"[-] {url} adresine bağlanırken hata oluştu: {e}")

    target_links = toplam_linkler[:15]

    if not target_links:
        print("[-] Hiçbir uygun haber bağlantısı bulunamadı.")
        return

    print(f"[+] Toplam tespit edilen {len(target_links)} haber taranıyor...")
    
    haber_parcalari = []

    for i, link in enumerate(target_links, 1):
        try:
            news_res = scraper.get(link, timeout=5)
            if news_res.status_code == 200:
                news_soup = BeautifulSoup(news_res.text, "html.parser")
                first_p = news_soup.find("p")
                if first_p and first_p.text.strip():
                    haber_metni = first_p.text.strip()
                    if metin_gecerli_mi(haber_metni):
                        haber_parcalari.append(haber_metni)
        except Exception as e:
            continue

    if not haber_parcalari:
        print("[-] Hiçbir geçerli haber metni alınamadı.")
        return

    ssml_content = "<speak>" + '<break time="1s"/>'.join(haber_parcalari) + "</speak>"

    print("[*] Google Cloud TTS ile SSML duraklamalı bülten üretiliyor...")

    synthesis_input = texttospeech.SynthesisInput(ssml=ssml_content)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-News-N",
        ssml_gender=texttospeech.SsmlVoiceGender.MALE,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    with open(output_filename, "wb") as out:
        out.write(response.audio_content)

    print(f"[+] BAŞARILI! Bülten güncellendi: {output_filename}\n")


# =============================================================================
## 4. BÖLÜM: DİSCORD /REQUEST KUYRUK BOTU & SHOUTOUT TTS WORKER
# =============================================================================

DISCORD_TTS_DIR = Path(r"C:\Users\kadir\Music\Sweepers\Sweeper")
DISCORD_TTS_KEY_PATH = DISCORD_TTS_DIR / "mexalounge-radio-515518-4a68ad4b09ad.json"

DISCORD_BOT_TOKEN = "MTU3NTU0MzgxODMyNDAxNzIyMg.GnS3R5.AKm4Gz1qDsUvN_dX1wM2c1NYr-Q66UqY6qvHZQ".strip()
GUILD_ID = "1434464501054443542"
COOLDOWN_SECONDS = int(os.getenv("REQUEST_COOLDOWN_SEC", "10"))
DB_PATH = Path(os.getenv("REQUEST_DB_PATH", str(DISCORD_TTS_DIR / "requests.db")))
TMP_DIR = Path(os.getenv("TTS_TMP_DIR", str(DISCORD_TTS_DIR / "tmp_mp3")))
OUTPUT_DIR = Path(os.getenv("TTS_OUTPUT_DIR", str(DISCORD_TTS_DIR)))
FIXED_FILENAME = os.getenv("TTS_FIXED_FILENAME", "latest_shoutout.mp3")
ENABLE_MESSAGE_FIELD = False

POLL_INTERVAL_SEC = float(os.getenv("TTS_POLL_INTERVAL", "2.5"))
VOICE_LANGUAGE = os.getenv("TTS_LANGUAGE_CODE", "en-US")
VOICE_NAME = os.getenv("TTS_VOICE_NAME", "en-US-Neural2-F")
SPEAKING_RATE = float(os.getenv("TTS_SPEAKING_RATE", "0.98"))
MAX_RETRIES = 3

BANNED_PATTERNS = [
    r"https?://",
    r"www\.",
    r"discord\.gg/",
    r"@everyone",
    r"@here",
]


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                retry_count INTEGER NOT NULL DEFAULT 0,
                error_msg TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_requests_status_id
            ON requests (status, id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_requests_user_created
            ON requests (user_id, created_at DESC)
        """)
        conn.commit()


def ensure_dirs() -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def check_cooldown(user_id: int, cooldown_seconds: int = 10) -> int:
    now = int(time.time())
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT created_at FROM requests
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return 0
    remaining = cooldown_seconds - (now - int(row["created_at"]))
    return max(0, remaining)


def is_duplicate_recent(user_id: int, name: str, city: str, message: str, window_seconds: int = 900) -> bool:
    cutoff = int(time.time()) - window_seconds
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id FROM requests
            WHERE user_id = ?
              AND name = ?
              AND city = ?
              AND message = ?
              AND created_at >= ?
            LIMIT 1
            """,
            (user_id, name, city, message, cutoff),
        ).fetchone()
    return row is not None


def create_request(user_id: int, username: str, name: str, city: str, message: str = "") -> int:
    now = int(time.time())
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO requests (
                user_id, username, name, city, message, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (user_id, username, name, city, message, now, now),
        )
        conn.commit()
        return int(cur.lastrowid)


def clean_field(text: str | None, max_len: int) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[:max_len]


def has_spam_pattern(text: str) -> bool:
    low = text.lower()
    for pat in BANNED_PATTERNS:
        if re.search(pat, low):
            return True
    if re.search(r"(.)\1{7,}", text):
        return True
    return False


class RadioRequestModal(discord.ui.Modal, title="Mexalounge Radio — Shoutout"):
    name_input = discord.ui.TextInput(
        label="Name",
        placeholder="e.g. Alex",
        required=True,
        min_length=1,
        max_length=35,
    )
    city_input = discord.ui.TextInput(
        label="City",
        placeholder="e.g. Amsterdam",
        required=True,
        min_length=1,
        max_length=40,
    )
    message_input = discord.ui.TextInput(
        label="Message (Optional)",
        placeholder="e.g. Greetings from Amsterdam",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=160,
    )

    def __init__(self) -> None:
        super().__init__()
        if not ENABLE_MESSAGE_FIELD:
            self.remove_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        name = clean_field(self.name_input.value, 35)
        city = clean_field(self.city_input.value, 40)
        message = clean_field(self.message_input.value, 160) if ENABLE_MESSAGE_FIELD else ""

        if not name or not city:
            await interaction.response.send_message(
                "Please fill in both **Name** and **City**.",
                ephemeral=True,
            )
            return

        remaining = check_cooldown(interaction.user.id, COOLDOWN_SECONDS)
        if remaining > 0:
            mins, secs = divmod(remaining, 60)
            time_str = f"{mins}m {secs}s" if mins else f"{secs}s"
            await interaction.response.send_message(
                f"Please wait **{time_str}** before sending another shoutout.",
                ephemeral=True,
            )
            return

        if has_spam_pattern(f"{name} {city} {message}"):
            await interaction.response.send_message(
                "Links, mentions, or repetitive spam patterns are not allowed. Please try again.",
                ephemeral=True,
            )
            return

        if is_duplicate_recent(interaction.user.id, name, city, message):
            await interaction.response.send_message(
                "You have already submitted this exact shoutout recently.",
                ephemeral=True,
            )
            return

        req_id = create_request(
            user_id=interaction.user.id,
            username=str(interaction.user),
            name=name,
            city=city,
            message=message,
        )

        msg_line = f"\n**Message:** {message}" if (ENABLE_MESSAGE_FIELD and message) else ""
        await interaction.response.send_message(
            f"Your shoutout has been added to the **Mexalounge Radio** queue (#{req_id})! 🎧\n"
            f"**Name:** {name}\n**City:** {city}{msg_line}",
            ephemeral=False,
        )


class MexaloungeBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        init_db()
        if GUILD_ID.isdigit():
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


discord_bot = MexaloungeBot()


@discord_bot.tree.command(name="request", description="Send a live shoutout to Mexalounge Radio")
async def request_cmd(interaction: discord.Interaction) -> None:
    await interaction.response.send_modal(RadioRequestModal())


def run_discord_bot() -> None:
    if not DISCORD_BOT_TOKEN:
        print("⚠️ DISCORD_BOT_TOKEN boş, Discord /request botu başlatılmadı.")
        return
    try:
        print("🤖 Discord /request botu başlatılıyor...")
        discord_bot.run(DISCORD_BOT_TOKEN)
    except Exception as e:
        print(f"❌ Discord bot hatası: {e}")


def sanitize_for_speech(text: str) -> str:
    cleaned = re.sub(r"[^\w\s\-'.,!?]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned).strip()


def build_shoutout_text(name: str, city: str, message: str = "") -> str:
    safe_name = sanitize_for_speech(name) or "a listener"
    safe_city = sanitize_for_speech(city) or "around the world"
    safe_msg = sanitize_for_speech(message)

    if safe_msg:
        return (
            f"Greetings to {safe_name} listening from {safe_city}. "
            f"They say: {safe_msg}. Thanks for tuning in to Mexalounge Radio."
        )
    return (
        f"Greetings to {safe_name} listening from {safe_city}. "
        f"Thanks for tuning in to Mexalounge Radio."
    )


def claim_latest_pending() -> sqlite3.Row | None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT * FROM requests
            WHERE status = 'pending'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            conn.commit()
            return None

        cur = conn.execute(
            """
            UPDATE requests
            SET status = 'processing', updated_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (now, row["id"]),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
        return row


def mark_shoutout_done(req_id: int, output_path: Path) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE requests
            SET status = 'done', error_msg = NULL, updated_at = ?
            WHERE id = ?
            """,
            (now, req_id),
        )
        conn.commit()
    print(f"[DONE] #{req_id} -> {output_path}")


def mark_shoutout_retry_or_failed(req_id: int, current_retry: int, err_text: str) -> None:
    now = int(time.time())
    next_retry = current_retry + 1
    new_status = "pending" if next_retry <= MAX_RETRIES else "failed"
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE requests
            SET status = ?, retry_count = ?, error_msg = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_status, next_retry, err_text[:500], now, req_id),
        )
        conn.commit()
    print(f"[ERR] #{req_id} (attempt {next_retry}/{MAX_RETRIES}) -> {new_status}: {err_text}")


def queue_shoutout_in_radiodj(song_id: int = 2054, playlist_pid: int = 0) -> None:
    """
    2054 ID'li 'Latest Shoutout' kaydını 'playlists_list' tablosunda
    ilgili pID altında ord=0 (ilk sıraya) yerleştirir ve mevcut ord değerlerini kaydırır.
    """
    try:
        db = pymysql.connect(
            host="127.0.0.1",
            user="root",
            password="",
            database="radiodj3",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
        )
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT ID
                FROM songs
                WHERE ID = %s
                LIMIT 1
                """,
                (song_id,),
            )
            song = cursor.fetchone()
            if not song:
                print(f"[RADYODJ QUEUE ERR] songs tablosunda ID={song_id} bulunamadı.")
                db.close()
                return

            # Aynı shoutout daha önce bu pID listesinde varsa temizle
            cursor.execute(
                "DELETE FROM playlists_list WHERE pID = %s AND sID = %s",
                (playlist_pid, song_id),
            )

            # Sıraları bozmadan yeniden 1, 2, 3... olarak diz ki 0 en başa açılsın
            cursor.execute(
                """
                SELECT ID FROM playlists_list
                WHERE pID = %s
                ORDER BY ord ASC, ID ASC
                """,
                (playlist_pid,),
            )
            rows = cursor.fetchall()
            for idx, r in enumerate(rows, start=1):
                cursor.execute(
                    "UPDATE playlists_list SET ord = %s WHERE ID = %s",
                    (idx, r["ID"]),
                )

            # Shoutout'u ord = 0 olarak en başa ekle
            cursor.execute(
                """
                INSERT INTO playlists_list (
                    pID, sID, cstart, cnext, cend, fin, fout,
                    swID, swplay, vtID, vtplay, swfirst, ord
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    playlist_pid,
                    song["ID"],
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    -100,
                    0,
                    -100,
                    0,
                    0,
                ),
            )

        db.commit()
        db.close()
        print(f"[RADYODJ QUEUE] Song #{song_id} 'playlists_list' (pID={playlist_pid}, ord=0) içine eklendi.")
    except Exception as e:
        print(f"[RADYODJ QUEUE ERR] {e}")


def run_shoutout_worker() -> None:
    init_db()
    ensure_dirs()
    tts_client = texttospeech.TextToSpeechClient()
    final_path = OUTPUT_DIR / FIXED_FILENAME
    print(f"Mexalounge Radio TTS Worker started (Voice: {VOICE_NAME}).")
    print(f"DB: {DB_PATH.resolve()} | Target File: {final_path.resolve()}")

    while True:
        row = None
        try:
            row = claim_latest_pending()
            if not row:
                time.sleep(POLL_INTERVAL_SEC)
                continue

            req_id = int(row["id"])
            spoken_text = build_shoutout_text(
                name=row["name"],
                city=row["city"],
                message=row["message"] or "",
            )

            synthesis_input = texttospeech.SynthesisInput(text=spoken_text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=VOICE_LANGUAGE,
                name=VOICE_NAME,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=SPEAKING_RATE,
            )
            response = tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )

            tmp_path = TMP_DIR / FIXED_FILENAME
            tmp_path.write_bytes(response.audio_content)
            if not tmp_path.exists() or tmp_path.stat().st_size == 0:
                raise RuntimeError("Generated MP3 file is empty.")

            os.replace(tmp_path, final_path)
            mark_shoutout_done(req_id, final_path)
            queue_shoutout_in_radiodj(2054)

        except Exception as exc:
            if row is not None:
                mark_shoutout_retry_or_failed(int(row["id"]), int(row["retry_count"]), str(exc))
            time.sleep(POLL_INTERVAL_SEC)


# =============================================================================
## 5. BÖLÜM: ANA ÇALIŞTIRMA VE ZAMANLAYICI (ENTEGRE SİSTEM)
# =============================================================================

if __name__ == "__main__":
    print("🚀 Mexalounge Entegre Bot Sistemi Başlatılıyor (Tamamen UTC Modu + Top20 Discord Entegrasyonlu)...")

    # 1. Adım: Xceed / MySQL / GitHub / Discord döngüsünü arka planda başlat
    t = threading.Thread(target=ithub_and_events_loop, daemon=True)
    t.start()

    # Discord /request botunu ve Shoutout TTS worker'ı arka planda başlat
    threading.Thread(target=run_discord_bot, daemon=True).start()
    threading.Thread(target=run_shoutout_worker, daemon=True).start()

    # 2. Adım: BBC Sesli Bülten Zamanlayıcısını Ayarla (UTC Saatleri)
    hedef_siteler = [
        "https://www.bbc.com/news/world/europe",
        "https://www.bbc.com/news/us-canada",
    ]
    calisma_saatleri_bbc = ["03:50", "07:50", "11:50", "15:50", "19:50"]

    for saat in calisma_saatleri_bbc:
        schedule.every().day.at(saat).do(generate_google_cloud_news_mp3, hedef_siteler)

    print("[*] Tüm zamanlayıcılar aktif. UTC saatleri bekleniyor...")
    print(f"[*] Sesli Bülten Saatleri (UTC): {', '.join(calisma_saatleri_bbc)}")
    print(f"[*] Haber Paylaşım Saatleri (UTC): Sabah 08:00 (DJ Mag), Akşam 18:00 (DJ Rankings)")
    print(f"[*] Top 20 Discord Bildirim Saati (UTC): Her gün 18:00")

    # 3. Adım: Ana akışta schedule kütüphanesini sürekli çalıştırarak zamanlanmış görevleri takip et
    while True:
        schedule.run_pending()
=======
import os
import re
import time
import json
import pickle
import sqlite3
import subprocess
import threading
import warnings
from pathlib import Path
import schedule
import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import cloudscraper
import pymysql
import discord
from discord import app_commands
from google.cloud import texttospeech
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from urllib.parse import urlparse

# BeautifulSoup uyarılarını bastırıyoruz
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Google Cloud JSON anahtar dosyasının yolu
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    r"C:\Users\kadir\Desktop\Radyo Botu\mexalounge-radio-0926e73fdef7.json"
)

# Blogger API yetki kapsamı
SCOPES = ['https://www.googleapis.com/auth/blogger']

# Discord Webhook URL'leri
WEBHOOK_URL = "https://discord.com/api/webhooks/1571511090221686975/1jZqd-8O4OyoW5NJABEzogARDvEByswt_g5KekXSLmVB7ntdoT_uUgB7W20swxXGEjaM"
EVENT_WEBHOOK_URL = "https://discord.com/api/webhooks/1571517049971286197/TP4yUgreitR1v4lYZjO4nDZ7CztNwOyCE2Re_pHWcSRSTAlcLcK1yRCXICaUyC3REmgl"
TOP20_WEBHOOK_URL = "https://discord.com/api/webhooks/1571520094088077423/JmseMit8wivblmJQYJV2RqII2r8yNP2L8COve_l19cOCHERo_Fazdl7XHBHjF4pG9Qcj"


# =============================================================================
## 1. BÖLÜM: GLOBAL EVENT RADAR (XCEED) & RADYODJ MYSQL & GİTHUB & DİSCORD OTOMASYONU
# =============================================================================

xceed_urls = [
    "https://xceed.me/en/barcelona/events",
    "https://xceed.me/en/roma/events",
    "https://xceed.me/en/brussels/events",
    "https://xceed.me/en/hamburg/events",
    "https://xceed.me/en/artist/carl-cox",
    "https://xceed.me/en/artist/charlotte-de-witte",
    "https://xceed.me/en/london/events",
    "https://xceed.me/en/artist/amelie-lens"
]

scraper_xceed = cloudscraper.create_scraper()

def send_top20_to_discord():
    """Top 20 listesini kontrol eder ve Discord webhook'una gönderir."""
    print("Top20 Discord gönderimi başladı...")

    if not os.path.exists("top20.json"):
        print("top20.json bulunamadı.")
        return

    with open("top20.json", "r", encoding="utf-8") as f:
        tracks = json.load(f)

    if len(tracks) == 0:
        print("top20.json boş.")
        return

    mesaj = "🏆 **MEXALOUNGE RADIO TOP 20** 🏆\n\n"

    for track in tracks:
        rank = track.get("rank", "?")
        artist = track.get("artist", "Unknown Artist")
        title = track.get("title", "Unknown Title")
        plays = track.get("play_count", 0)

        if rank == 1:
            prefix = "🥇"
        elif rank == 2:
            prefix = "🥈"
        elif rank == 3:
            prefix = "🥉"
        else:
            prefix = f"#{rank}"

        mesaj += (
            f"{prefix} **{artist}**\n"
            f"🎵 {title}\n"
            f"▶️ Plays: {plays}\n\n"
        )

    mesaj += "📻 Mexalounge Radio"

    response = requests.post(
        TOP20_WEBHOOK_URL,
        json={"content": mesaj}
    )

    print("Discord Status:", response.status_code)

    if response.status_code in [200, 204]:
        print("Top20 başarıyla gönderildi.")
    else:
        print(response.text)


def send_event_to_discord():
    """Global etkinlikleri kontrol eder ve yeni etkinliği Discord webhook'una bildirir."""
    print("Global Event kontrolü başladı...")

    if not os.path.exists("events.json"):
        print("events.json bulunamadı.")
        return

    with open("events.json", "r", encoding="utf-8") as f:
        events = json.load(f)

    if len(events) == 0:
        print("Etkinlik bulunamadı.")
        return

    event = events[0]

    title = event.get("title", "Unknown Event")
    date = event.get("date", "TBA")
    location = event.get("location", "GLOBAL")
    link = event.get("link", "")

    print("Etkinlik:", title)

    last_event_file = "last_discord_event.txt"
    previous_event = ""

    if os.path.exists(last_event_file):
        with open(last_event_file, "r", encoding="utf-8") as f:
            previous_event = f.read().strip()

    if link == previous_event:
        print("Bu etkinlik daha önce gönderilmiş.")
        return

    message = {
        "content":
        f"🌍 **New Global Event**\n\n"
        f"🎉 **{title}**\n"
        f"📍 {location}\n"
        f"📅 {date}\n\n"
        f"🔗 {link}"
    }

    response = requests.post(EVENT_WEBHOOK_URL, json=message)

    print("Discord Status:", response.status_code)

    if response.status_code in [200, 204]:
        with open(last_event_file, "w", encoding="utf-8") as f:
            f.write(link)
        print("Discord'a başarıyla gönderildi.")
    else:
        print(response.text)


def fetch_events():
    """Xceed üzerinden global elektronik müzik etkinliklerini tarar, events.json'a kaydeder ve Discord'a bildirir."""
    all_events = []
    print("\n--- Global Event Radar Taraması Başlıyor ---")

    for url in xceed_urls:
        try:
            print(f"Taranıyor: {url}")
            response = scraper_xceed.get(url, timeout=20)
            
            if response.status_code != 200:
                print(f"Bağlantı hatası code: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("a", href=True)
            found_count = 0

            url_parts = url.strip("/").split("/")
            extracted_name = "GLOBAL"
            if "artist" in url_parts and len(url_parts) > url_parts.index("artist") + 1:
                extracted_name = url_parts[url_parts.index("artist") + 1].replace("-", " ").upper()
            elif len(url_parts) > 4:
                extracted_name = url_parts[4].replace("-", " ").upper()

            for card in cards:
                href = card.get("href", "")
                if "/event/" not in href:
                    continue

                event_link = href if href.startswith("http") else "https://xceed.me" + href

                try:
                    title_elem = card.find("h3") or card.find("h4") or card.find("p")
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    if not title or len(title) < 3:
                        title = card.get_text(strip=True)

                    if len(title) < 3 or "GEÇMİŞ" in title.upper() or "YAKLAŞAN" in title.upper():
                        continue

                    date_text = ""
                    for text_item in card.stripped_strings:
                        if any(m in text_item.lower() for m in ["kas", "ara", "oca", "sub", "mar", "nis", "may", "haz", "tem", "ağu", "eyl", "okt", "2026"]):
                            date_text = text_item
                            break

                    if not date_text or len(date_text) < 3:
                        date_text = "TBA (SOON)"

                    img_elem = card.find("img")
                    img_url = img_elem.get("src") or img_elem.get("data-src") if img_elem else ""

                    event_data = {
                        "title": title[:65],
                        "date": date_text[:35],
                        "location": extracted_name,
                        "image": img_url,
                        "link": event_link,
                    }
                    
                    if event_data not in all_events and event_link not in [e["link"] for e in all_events]:
                        all_events.append(event_data)
                        found_count += 1

                except Exception:
                    continue

            print(f"Başarılı: {found_count} adet etkinlik çekildi.")
        except Exception as e:
            print(f"Hata oluştu {url}: {e}")

    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=4)
    print("events.json güncellendi.")


# --- KARA LİSTE (JİNGLE, REKLAM VE ANONSLARI ELEMEK İÇİN) ---
BLACKLIST_KEYWORDS = [
    "church-bells", "presentation-logo", "radio-for-all", "kamuspotu", "kamu spotu", 
    "radyo spotu", "spotu", "lösev", "tühsev", "darussafaka", "darüşşafaka", 
    "tev okula donus", "jingle", "intro", "tohum otizm vakfı", "türkiye spastik çocuklar vakfı", 
    "tkd kamu spotu", "canım kardeşim", "swepper", "mexalounge radio", "radio1", "radio2",
    "radio4", "radio3", "radio5", "presentation-logo-version-beat-way-up", "radio-for-all-trance-505926", 
    "Reklam-Teaser", "Mexalounge News", "News Teaser"
]

def build_blacklist_sql_condition():
    """MySQL sorguları için kara liste filtre koşullarını hazırlar."""
    conditions = []
    for word in BLACKLIST_KEYWORDS:
        w = word.lower()
        conditions.append(f"LOWER(title) NOT LIKE '%{w}%'")
        conditions.append(f"LOWER(artist) NOT LIKE '%{w}%'")
    return " AND ".join(conditions)


def send_now_playing():
    """Radyoda o an çalan şarkıyı kontrol eder ve değiştiyse Discord webhook'una bildirir."""
    print("--- Discord 'Now Playing' Kontrol Ediliyor ---")
    try:
        if not os.path.exists("history.json"):
            print("history.json bulunamadı.")
            return

        with open("history.json", "r", encoding="utf-8") as f:
            history = json.load(f)

        if len(history) == 0:
            print("history.json boş.")
            return

        last = history[0]

        artist = last["artist"]
        title = last["title"]
        time_ = last["time"]

        current_track = f"{artist} - {title}"

        last_track_file = "last_discord_track.txt"
        previous_track = ""

        if os.path.exists(last_track_file):
            with open(last_track_file, "r", encoding="utf-8") as f:
                previous_track = f.read().strip()

        if current_track == previous_track:
            print("Şarkı değişmemiş, Discord bildirimi atlandı.")
            return

        message = {
            "content":
            f"🎵 **Now Playing**\n\n"
            f"🎤 Artist: {artist}\n"
            f"🎶 Track: {title}\n"
            f"⏰ Time: {time_}\n\n"
            f"📻 Mexalounge Radio"
        }

        response = requests.post(WEBHOOK_URL, json=message)

        print("Discord Status:", response.status_code)

        if response.status_code in [200, 204]:
            with open(last_track_file, "w", encoding="utf-8") as f:
                f.write(current_track)
            print("Discord mesajı başarıyla gönderildi.")
        else:
            print("Discord hata yanıtı:", response.text)

    except Exception as e:
        print(f"⚠️ Discord webhook gönderim hatası: {e}")


def fetch_radio_history():
    """RadyoDJ MySQL veritabanından son çalan parçaları çeker ve history.json'a kaydeder."""
    print("--- RadyoDJ Geçmiş Parçalar Güncelleniyor ---")
    try:
        db = pymysql.connect(
            host="127.0.0.1", user="root", password="", database="radiodj3",
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, connect_timeout=5
        )
        
        with db.cursor() as cursor:
            blacklist_filter = build_blacklist_sql_condition()
            query = f"""
                SELECT artist, title, date_played 
                FROM history 
                WHERE {blacklist_filter} 
                ORDER BY id DESC 
                LIMIT 10
            """
            cursor.execute(query)
            result = cursor.fetchall()
            
            tracks = []
            for row in result:
                tracks.append({
                    "artist": row["artist"] if row["artist"] else "Unknown Artist",
                    "title": row["title"] if row["title"] else "Unknown Title",
                    "time": str(row["date_played"]) if row["date_played"] else ""
                })
                
            with open("history.json", "w", encoding="utf-8") as f:
                json.dump(tracks, f, ensure_ascii=False, indent=4)
                
            print("history.json güncel ve filtrelenmiş RadyoDJ verileriyle yenilendi.")
        db.close()

        # Geçmiş güncellendikten hemen sonra Discord kontrolünü tetikle
        send_now_playing()

    except Exception as e:
        print(f"\n[!] MYSQL HATA YAKALANDI (History): {e}\n")


def fetch_top_tracks():
    """RadyoDJ MySQL veritabanından son 30 günün en çok çalan ilk 20 parçasını çeker."""
    print("--- Top 20 En Çok Çalan Şarkılar Güncelleniyor ---")
    try:
        db = pymysql.connect(
            host="127.0.0.1", user="root", password="", database="radiodj3",
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, connect_timeout=5
        )
        
        with db.cursor() as cursor:
            blacklist_filter = build_blacklist_sql_condition()
            query = f"""
                SELECT artist, title, COUNT(*) as play_count 
                FROM history 
                WHERE date_played >= NOW() - INTERVAL 30 DAY 
                AND {blacklist_filter} 
                GROUP BY artist, title 
                ORDER BY play_count DESC 
                LIMIT 20
            """
            cursor.execute(query)
            result = cursor.fetchall()
            
            top_tracks = []
            for rank, row in enumerate(result, start=1):
                top_tracks.append({
                    "rank": rank,
                    "artist": row["artist"] if row["artist"] else "Unknown Artist",
                    "title": row["title"] if row["title"] else "Unknown Title",
                    "play_count": row["play_count"]
                })
                
            with open("top20.json", "w", encoding="utf-8") as f:
                json.dump(top_tracks, f, ensure_ascii=False, indent=4)
                
            print("top20.json son 30 günlük filtrelenmiş verilerle güncellendi.")
        db.close()
    except Exception as e:
        print(f"\n[!] MYSQL HATA YAKALANDI (Top 20): {e}\n")


def push_to_github():
    """Dosyalar değiştiyse GitHub'a gönderir."""
    print("--- GitHub Güncellemesi Kontrol Ediliyor ---")
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )

        if not status.stdout.strip():
            print("✅ Değişiklik yok. GitHub push atlandı.")
            return

        print("📦 Değişiklik bulundu. GitHub'a gönderiliyor...")

        subprocess.run(
            ["git", "add", "history.json", "events.json", "top20.json"],
            check=True
        )

        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "Bot update: history, events, top20"
            ],
            check=True
        )

        subprocess.run(
            ["git", "push"],
            check=True
        )

        print("✅ GitHub başarıyla güncellendi.")

    except Exception as e:
        print(f"⚠️ GitHub güncelleme hatası: {e}")


def ithub_and_events_loop():
    """15 dakikalık aralıklarla Xceed, MySQL, GitHub senkronizasyonunu ve Discord bildirimlerini yürütür."""
    print("🔄 15 dakikalık Xceed/MySQL/GitHub döngü iş parçacığı başlatıldı.")
    
    son_sabah_tarihi = None
    son_aksam_tarihi = None
    son_top20_tarihi = None

    while True:
        try:
            start_time = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n=== [15dk Döngü] Başlangıç Zamanı (UTC): {start_time} ===")
            
            simdi_utc = time.gmtime()
            bugun = (simdi_utc.tm_year, simdi_utc.tm_mon, simdi_utc.tm_mday)
            saat = simdi_utc.tm_hour
            dakika = simdi_utc.tm_min

            # Sabah Haberi: UTC 08:00
            if saat == 8 and dakika < 15:
                if son_sabah_tarihi != bugun:
                    print("☀️ [UTC Zaman Penceresi] Sabah haberi (DJ Mag) tetikleniyor...")
                    sabah_haber_gorevi()
                    son_sabah_tarihi = bugun

            # Akşam Haberi: UTC 18:00
            if saat == 18 and dakika < 15:
                if son_aksam_tarihi != bugun:
                    print("🌙 [UTC Zaman Penceresi] Akşam haberi (DJ Rankings) tetikleniyor...")
                    aksam_haber_gorevi()
                    son_aksam_tarihi = bugun

            # Top 20 Discord Gönderimi: Her gün UTC 18:00'de
            if saat == 18 and dakika < 15:
                if son_top20_tarihi != bugun:
                    print("🏆 [UTC Zaman Penceresi] Top 20 Discord bildirimi tetikleniyor...")
                    fetch_top_tracks()      # Önce top20.json'u güncel verilerle yenile
                    send_top20_to_discord() # Sonra Discord'a gönder
                    son_top20_tarihi = bugun

            fetch_events()         # İçinde send_event_to_discord() çağrılır
            fetch_radio_history()  # İçinde send_now_playing() çağrılır
            fetch_top_tracks()
            push_to_github()
            
            print(f"[15dk Döngü] İşlem tamamlandı.")
        except Exception as e:
            print(f"15dk Döngü sırasında hata oluştu: {e}")

        total_seconds = 15 * 60
        while total_seconds > 0:
            mins, secs = divmod(total_seconds, 60)
            timer_format = f"{mins:02d}:{secs:02d}"
            print(f"⏳ Sonraki güncellemeye kalan süre: {timer_format}", end="\r")
            time.sleep(1)
            total_seconds -= 1
        print("\n")


# =============================================================================
## 2. BÖLÜM: BLOGGER OTOMATİK HABER BOTU (SABAH DJ MAG & AKŞAM DJ RANKINGS)
# =============================================================================

def get_blogger_service():
    """Blogger API bağlantısını ve yetkilendirme nesnesini döndürür."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("❌ HATA: 'credentials.json' dosyası bulunamadı!")
                return None
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('blogger', 'v3', credentials=creds)


def is_already_posted(service, blog_id, news_link):
    """Blogger'daki son postları kontrol ederek aynı haberin daha önce paylaşılıp paylaşılmadığını denetler."""
    try:
        posts = service.posts().list(blogId=blog_id, maxResults=20).execute()
        norm_news_link = news_link.rstrip('/')
        
        if 'items' in posts:
            for post in posts['items']:
                content = post.get('content', '')
                title = post.get('title', '')
                if norm_news_link in content or news_link in content:
                    print(f"ℹ️ [Kontrol] Bu haber daha önce paylaşılmış: '{title}'")
                    return True
    except Exception as e:
        print(f"⚠️ Post kontrolü sırasında hata oluştu: {e}")
    return False


def haber_botu(index_url, ogun_etiketi):
    """Belirtilen kaynak siteden en güncel haberi çeker, mükerrer kontrolü yapar ve Blogger'da yayınlar."""
    print(f"\n==================================================")
    print(f"🕒 İşlem Zamanı (UTC): {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}")
    print(f"--- {ogun_etiketi} Haberi Kontrolü Başlıyor ---")
    print(f"[*] Hedef Kaynak: {index_url}")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(index_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"❌ Sayfaya ulaşılamadı. Kod: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        news_link = ""
        parsed_base = urlparse(index_url)
        base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        if "djmag.com" in index_url:
            candidates = soup.find_all(['div', 'article'], class_=lambda x: x and ('row' in x or 'item' in x or 'article' in x))
            for candidate in candidates:
                a_tag = candidate.find('a', href=True)
                if a_tag:
                    href = a_tag['href']
                    if ("/news/" in href or "/tech/" in href or "/features/" in href) and href != index_url:
                        news_link = href if href.startswith('http') else base_domain + href
                        break
            if not news_link:
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    if ("/news/" in href or "/tech/" in href) and href != index_url and "tag" not in href:
                        news_link = href if href.startswith('http') else base_domain + href
                        break
        
        elif "djrankings.org" in index_url:
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if "news=" in href or "article" in href or "post" in href:
                    news_link = href if href.startswith('http') else base_domain + href
                    break
            if not news_link:
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    if href != index_url and len(href) > 15 and not "tag" in href:
                        news_link = href if href.startswith('http') else base_domain + href
                        break

        if not news_link:
            print("❌ Güncel haber linki bulunamadı!")
            return
            
        print(f"✅ Yakalanan en güncel haber linki: {news_link}")
        
        service = get_blogger_service()
        if not service: return
        blogs = service.blogs().listByUser(userId='self').execute()
        blog_id = blogs['items'][0]['id']

        if is_already_posted(service, blog_id, news_link):
            print(f"⏭️ Bu haber zaten Blogger'da mevcut. Yeni haber bekleniyor, atlanıyor...")
            return

        print(f"[*] Haber detayları indiriliyor...")
        news_response = requests.get(news_link, headers=headers, timeout=15)
        if news_response.status_code != 200:
            print(f"❌ Haber detay sayfasına ulaşılamadı. Kod: {news_response.status_code}")
            return
            
        news_soup = BeautifulSoup(news_response.text, 'html.parser')

        title_elem = news_soup.find('h1') or news_soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else "Mexalounge Radio News"

        paragraflar = []
        for p in news_soup.find_all('p'):
            text = p.get_text(strip=True)
            if len(text) > 30 and not any(w in text.lower() for w in ["cookie", "subscribe", "all rights", "privacy", "thrust publishing"]):
                paragraflar.append(text)
                if len(paragraflar) == 2:
                    break
                    
        paragraf_html = "".join([f"<p>{p}</p>" for p in paragraflar]) if paragraflar else "<p>Latest updates from the electronic music world...</p>"

        img_url = ""
        og_img = news_soup.find('meta', property='og:image') or news_soup.find('meta', attrs={'name': 'twitter:image'})
        if og_img and og_img.get('content'):
            img_url = og_img['content']
        else:
            for img in news_soup.find_all('img'):
                src = img.get('src') or img.get('data-src', '')
                if src and not any(icon in src.lower() for icon in ["logo", "avatar", "icon", "banner", "footer"]):
                    img_url = src if src.startswith('http') else base_domain + src
                    break

        html_content = ""
        if img_url:
            html_content += f'<div style="text-align: center; margin-bottom: 20px;"><img src="{img_url}" style="max-width:100%; height:auto; border-radius: 8px;" /></div>'
        html_content += paragraf_html
        html_content += f'<br/><hr/><p><b>Source / Original Article:</b> <a href="{news_link}" target="_blank" rel="nofollow">Click here for the full story</a></p>'

        body = {'title': title, 'content': html_content}
        
        print(f"[*] Blogger'a gönderiliyor...")
        post = service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()
        print(f"🎉 YENİ HABER BAŞARIYLA YAYINLANDI: {post.get('url')}")

    except Exception as e:
        print(f"❌ İşlem sırasında hata oluştu: {e}")


def sabah_haber_gorevi():
    """Sabah yayınlanacak haber için DJ Mag kaynağını tetikler."""
    haber_botu("https://djmag.com/news", "SABAH (DJ Mag)")

def aksam_haber_gorevi():
    """Akşam yayınlanacak haber için DJ Rankings kaynağını tetikler."""
    haber_botu("https://djrankings.org/news", "AKŞAM (DJ Rankings)")


# =============================================================================
## 3. BÖLÜM: BBC HABERLERİ & GOOGLE CLOUD TTS SESLENDİRME
# =============================================================================

FILTRE_KAPLARI = [
    r"copyright",
    r"all rights reserved",
    r"not responsible for the content",
    r"external sites",
    r"external linking",
    r"read about our approach",
]

def metin_gecerli_mi(metin):
    """Haber metninde yasal uyarı veya telif kalıplarının olup olmadığını kontrol eder."""
    for kalip in FILTRE_KAPLARI:
        if re.search(kalip, metin, re.IGNORECASE):
            return False
    return True

def generate_google_cloud_news_mp3(url_listesi):
    """BBC haberlerini tarar, metinleri SSML formatına dönüştürür ve Google Cloud TTS ile MP3 bülten üretir."""
    output_filename = r"C:\Users\Kadir\Music\News\mexalounge_news.mp3"

    print("\n[*] [Zamanlayıcı Tetiklendi] Haber bülteni üretim süreci başlatılıyor...")
    print("[*] Google Cloud TTS istemcisi başlatılıyor...")
    client = texttospeech.TextToSpeechClient()

    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )

    toplam_linkler = []

    for url in url_listesi:
        print(f"[*] Hedef siteye bağlanılıyor: {url}")
        try:
            response = scraper.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"]

                if href.startswith("http") and href not in toplam_linkler:
                    if "/news/" in href or "world" in href or "us-canada" in href:
                        toplam_linkler.append(href)
                elif href.startswith("/") and len(href) > 5:
                    full_url = "https://www.bbc.com" + href
                    if full_url not in toplam_linkler:
                        toplam_linkler.append(full_url)
        except Exception as e:
            print(f"[-] {url} adresine bağlanırken hata oluştu: {e}")

    target_links = toplam_linkler[:15]

    if not target_links:
        print("[-] Hiçbir uygun haber bağlantısı bulunamadı.")
        return

    print(f"[+] Toplam tespit edilen {len(target_links)} haber taranıyor...")
    
    haber_parcalari = []

    for i, link in enumerate(target_links, 1):
        try:
            news_res = scraper.get(link, timeout=5)
            if news_res.status_code == 200:
                news_soup = BeautifulSoup(news_res.text, "html.parser")
                first_p = news_soup.find("p")
                if first_p and first_p.text.strip():
                    haber_metni = first_p.text.strip()
                    if metin_gecerli_mi(haber_metni):
                        haber_parcalari.append(haber_metni)
        except Exception as e:
            continue

    if not haber_parcalari:
        print("[-] Hiçbir geçerli haber metni alınamadı.")
        return

    ssml_content = "<speak>" + '<break time="1s"/>'.join(haber_parcalari) + "</speak>"

    print("[*] Google Cloud TTS ile SSML duraklamalı bülten üretiliyor...")

    synthesis_input = texttospeech.SynthesisInput(ssml=ssml_content)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-News-N",
        ssml_gender=texttospeech.SsmlVoiceGender.MALE,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    with open(output_filename, "wb") as out:
        out.write(response.audio_content)

    print(f"[+] BAŞARILI! Bülten güncellendi: {output_filename}\n")


# =============================================================================
## 4. BÖLÜM: DİSCORD /REQUEST KUYRUK BOTU & SHOUTOUT TTS WORKER
# =============================================================================

DISCORD_TTS_DIR = Path(r"C:\Users\kadir\Music\Sweepers\Sweeper")
DISCORD_TTS_KEY_PATH = DISCORD_TTS_DIR / "mexalounge-radio-515518-4a68ad4b09ad.json"

DISCORD_BOT_TOKEN = "MTU3NTU0MzgxODMyNDAxNzIyMg.GvateP.85ESRnxAeecuQsIbAoAFf0bVYVT7K0UkKnBbtQ".strip()
GUILD_ID = "1434464501054443542"
COOLDOWN_SECONDS = int(os.getenv("REQUEST_COOLDOWN_SEC", "10"))
DB_PATH = Path(os.getenv("REQUEST_DB_PATH", str(DISCORD_TTS_DIR / "requests.db")))
TMP_DIR = Path(os.getenv("TTS_TMP_DIR", str(DISCORD_TTS_DIR / "tmp_mp3")))
OUTPUT_DIR = Path(os.getenv("TTS_OUTPUT_DIR", str(DISCORD_TTS_DIR)))
FIXED_FILENAME = os.getenv("TTS_FIXED_FILENAME", "latest_shoutout.mp3")
ENABLE_MESSAGE_FIELD = False

POLL_INTERVAL_SEC = float(os.getenv("TTS_POLL_INTERVAL", "2.5"))
VOICE_LANGUAGE = os.getenv("TTS_LANGUAGE_CODE", "en-US")
VOICE_NAME = os.getenv("TTS_VOICE_NAME", "en-US-Neural2-F")
SPEAKING_RATE = float(os.getenv("TTS_SPEAKING_RATE", "0.98"))
MAX_RETRIES = 3

BANNED_PATTERNS = [
    r"https?://",
    r"www\.",
    r"discord\.gg/",
    r"@everyone",
    r"@here",
]


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                retry_count INTEGER NOT NULL DEFAULT 0,
                error_msg TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_requests_status_id
            ON requests (status, id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_requests_user_created
            ON requests (user_id, created_at DESC)
        """)
        conn.commit()


def ensure_dirs() -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def check_cooldown(user_id: int, cooldown_seconds: int = 10) -> int:
    now = int(time.time())
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT created_at FROM requests
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return 0
    remaining = cooldown_seconds - (now - int(row["created_at"]))
    return max(0, remaining)


def is_duplicate_recent(user_id: int, name: str, city: str, message: str, window_seconds: int = 900) -> bool:
    cutoff = int(time.time()) - window_seconds
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id FROM requests
            WHERE user_id = ?
              AND name = ?
              AND city = ?
              AND message = ?
              AND created_at >= ?
            LIMIT 1
            """,
            (user_id, name, city, message, cutoff),
        ).fetchone()
    return row is not None


def create_request(user_id: int, username: str, name: str, city: str, message: str = "") -> int:
    now = int(time.time())
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO requests (
                user_id, username, name, city, message, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (user_id, username, name, city, message, now, now),
        )
        conn.commit()
        return int(cur.lastrowid)


def clean_field(text: str | None, max_len: int) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[:max_len]


def has_spam_pattern(text: str) -> bool:
    low = text.lower()
    for pat in BANNED_PATTERNS:
        if re.search(pat, low):
            return True
    if re.search(r"(.)\1{7,}", text):
        return True
    return False


class RadioRequestModal(discord.ui.Modal, title="Mexalounge Radio — Shoutout"):
    name_input = discord.ui.TextInput(
        label="Name",
        placeholder="e.g. Alex",
        required=True,
        min_length=1,
        max_length=35,
    )
    city_input = discord.ui.TextInput(
        label="City",
        placeholder="e.g. Amsterdam",
        required=True,
        min_length=1,
        max_length=40,
    )
    message_input = discord.ui.TextInput(
        label="Message (Optional)",
        placeholder="e.g. Greetings from Amsterdam",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=160,
    )

    def __init__(self) -> None:
        super().__init__()
        if not ENABLE_MESSAGE_FIELD:
            self.remove_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        name = clean_field(self.name_input.value, 35)
        city = clean_field(self.city_input.value, 40)
        message = clean_field(self.message_input.value, 160) if ENABLE_MESSAGE_FIELD else ""

        if not name or not city:
            await interaction.response.send_message(
                "Please fill in both **Name** and **City**.",
                ephemeral=True,
            )
            return

        remaining = check_cooldown(interaction.user.id, COOLDOWN_SECONDS)
        if remaining > 0:
            mins, secs = divmod(remaining, 60)
            time_str = f"{mins}m {secs}s" if mins else f"{secs}s"
            await interaction.response.send_message(
                f"Please wait **{time_str}** before sending another shoutout.",
                ephemeral=True,
            )
            return

        if has_spam_pattern(f"{name} {city} {message}"):
            await interaction.response.send_message(
                "Links, mentions, or repetitive spam patterns are not allowed. Please try again.",
                ephemeral=True,
            )
            return

        if is_duplicate_recent(interaction.user.id, name, city, message):
            await interaction.response.send_message(
                "You have already submitted this exact shoutout recently.",
                ephemeral=True,
            )
            return

        req_id = create_request(
            user_id=interaction.user.id,
            username=str(interaction.user),
            name=name,
            city=city,
            message=message,
        )

        msg_line = f"\n**Message:** {message}" if (ENABLE_MESSAGE_FIELD and message) else ""
        await interaction.response.send_message(
            f"Your shoutout has been added to the **Mexalounge Radio** queue (#{req_id})! 🎧\n"
            f"**Name:** {name}\n**City:** {city}{msg_line}",
            ephemeral=False,
        )


class MexaloungeBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        init_db()
        if GUILD_ID.isdigit():
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


discord_bot = MexaloungeBot()


@discord_bot.tree.command(name="request", description="Send a live shoutout to Mexalounge Radio")
async def request_cmd(interaction: discord.Interaction) -> None:
    await interaction.response.send_modal(RadioRequestModal())


def run_discord_bot() -> None:
    if not DISCORD_BOT_TOKEN:
        print("⚠️ DISCORD_BOT_TOKEN boş, Discord /request botu başlatılmadı.")
        return
    try:
        print("🤖 Discord /request botu başlatılıyor...")
        discord_bot.run(DISCORD_BOT_TOKEN)
    except Exception as e:
        print(f"❌ Discord bot hatası: {e}")


def sanitize_for_speech(text: str) -> str:
    cleaned = re.sub(r"[^\w\s\-'.,!?]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned).strip()


def build_shoutout_text(name: str, city: str, message: str = "") -> str:
    safe_name = sanitize_for_speech(name) or "a listener"
    safe_city = sanitize_for_speech(city) or "around the world"
    safe_msg = sanitize_for_speech(message)

    if safe_msg:
        return (
            f"Greetings to {safe_name} listening from {safe_city}. "
            f"They say: {safe_msg}. Thanks for tuning in to Mexalounge Radio."
        )
    return (
        f"Greetings to {safe_name} listening from {safe_city}. "
        f"Thanks for tuning in to Mexalounge Radio."
    )


def claim_latest_pending() -> sqlite3.Row | None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT * FROM requests
            WHERE status = 'pending'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            conn.commit()
            return None

        cur = conn.execute(
            """
            UPDATE requests
            SET status = 'processing', updated_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (now, row["id"]),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
        return row


def mark_shoutout_done(req_id: int, output_path: Path) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE requests
            SET status = 'done', error_msg = NULL, updated_at = ?
            WHERE id = ?
            """,
            (now, req_id),
        )
        conn.commit()
    print(f"[DONE] #{req_id} -> {output_path}")


def mark_shoutout_retry_or_failed(req_id: int, current_retry: int, err_text: str) -> None:
    now = int(time.time())
    next_retry = current_retry + 1
    new_status = "pending" if next_retry <= MAX_RETRIES else "failed"
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE requests
            SET status = ?, retry_count = ?, error_msg = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_status, next_retry, err_text[:500], now, req_id),
        )
        conn.commit()
    print(f"[ERR] #{req_id} (attempt {next_retry}/{MAX_RETRIES}) -> {new_status}: {err_text}")


def queue_shoutout_in_radiodj(song_id: int = 2054, playlist_pid: int = 0) -> None:
    """
    2054 ID'li 'Latest Shoutout' kaydını 'playlists_list' tablosunda
    ilgili pID altında ord=0 (ilk sıraya) yerleştirir ve mevcut ord değerlerini kaydırır.
    """
    try:
        db = pymysql.connect(
            host="127.0.0.1",
            user="root",
            password="",
            database="radiodj3",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
        )
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT ID
                FROM songs
                WHERE ID = %s
                LIMIT 1
                """,
                (song_id,),
            )
            song = cursor.fetchone()
            if not song:
                print(f"[RADYODJ QUEUE ERR] songs tablosunda ID={song_id} bulunamadı.")
                db.close()
                return

            # Aynı shoutout daha önce bu pID listesinde varsa temizle
            cursor.execute(
                "DELETE FROM playlists_list WHERE pID = %s AND sID = %s",
                (playlist_pid, song_id),
            )

            # Sıraları bozmadan yeniden 1, 2, 3... olarak diz ki 0 en başa açılsın
            cursor.execute(
                """
                SELECT ID FROM playlists_list
                WHERE pID = %s
                ORDER BY ord ASC, ID ASC
                """,
                (playlist_pid,),
            )
            rows = cursor.fetchall()
            for idx, r in enumerate(rows, start=1):
                cursor.execute(
                    "UPDATE playlists_list SET ord = %s WHERE ID = %s",
                    (idx, r["ID"]),
                )

            # Shoutout'u ord = 0 olarak en başa ekle
            cursor.execute(
                """
                INSERT INTO playlists_list (
                    pID, sID, cstart, cnext, cend, fin, fout,
                    swID, swplay, vtID, vtplay, swfirst, ord
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    playlist_pid,
                    song["ID"],
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    -100,
                    0,
                    -100,
                    0,
                    0,
                ),
            )

        db.commit()
        db.close()
        print(f"[RADYODJ QUEUE] Song #{song_id} 'playlists_list' (pID={playlist_pid}, ord=0) içine eklendi.")
    except Exception as e:
        print(f"[RADYODJ QUEUE ERR] {e}")


def run_shoutout_worker() -> None:
    init_db()
    ensure_dirs()
    tts_client = texttospeech.TextToSpeechClient()
    final_path = OUTPUT_DIR / FIXED_FILENAME
    print(f"Mexalounge Radio TTS Worker started (Voice: {VOICE_NAME}).")
    print(f"DB: {DB_PATH.resolve()} | Target File: {final_path.resolve()}")

    while True:
        row = None
        try:
            row = claim_latest_pending()
            if not row:
                time.sleep(POLL_INTERVAL_SEC)
                continue

            req_id = int(row["id"])
            spoken_text = build_shoutout_text(
                name=row["name"],
                city=row["city"],
                message=row["message"] or "",
            )

            synthesis_input = texttospeech.SynthesisInput(text=spoken_text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=VOICE_LANGUAGE,
                name=VOICE_NAME,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=SPEAKING_RATE,
            )
            response = tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )

            tmp_path = TMP_DIR / FIXED_FILENAME
            tmp_path.write_bytes(response.audio_content)
            if not tmp_path.exists() or tmp_path.stat().st_size == 0:
                raise RuntimeError("Generated MP3 file is empty.")

            os.replace(tmp_path, final_path)
            mark_shoutout_done(req_id, final_path)
            queue_shoutout_in_radiodj(2054)

        except Exception as exc:
            if row is not None:
                mark_shoutout_retry_or_failed(int(row["id"]), int(row["retry_count"]), str(exc))
            time.sleep(POLL_INTERVAL_SEC)


# =============================================================================
## 5. BÖLÜM: ANA ÇALIŞTIRMA VE ZAMANLAYICI (ENTEGRE SİSTEM)
# =============================================================================

if __name__ == "__main__":
    print("🚀 Mexalounge Entegre Bot Sistemi Başlatılıyor (Tamamen UTC Modu + Top20 Discord Entegrasyonlu)...")

    # 1. Adım: Xceed / MySQL / GitHub / Discord döngüsünü arka planda başlat
    t = threading.Thread(target=ithub_and_events_loop, daemon=True)
    t.start()

    # Discord /request botunu ve Shoutout TTS worker'ı arka planda başlat
    threading.Thread(target=run_discord_bot, daemon=True).start()
    threading.Thread(target=run_shoutout_worker, daemon=True).start()

    # 2. Adım: BBC Sesli Bülten Zamanlayıcısını Ayarla (UTC Saatleri)
    hedef_siteler = [
        "https://www.bbc.com/news/world/europe",
        "https://www.bbc.com/news/us-canada",
    ]
    calisma_saatleri_bbc = ["03:50", "07:50", "11:50", "15:50", "19:50"]

    for saat in calisma_saatleri_bbc:
        schedule.every().day.at(saat).do(generate_google_cloud_news_mp3, hedef_siteler)

    print("[*] Tüm zamanlayıcılar aktif. UTC saatleri bekleniyor...")
    print(f"[*] Sesli Bülten Saatleri (UTC): {', '.join(calisma_saatleri_bbc)}")
    print(f"[*] Haber Paylaşım Saatleri (UTC): Sabah 08:00 (DJ Mag), Akşam 18:00 (DJ Rankings)")
    print(f"[*] Top 20 Discord Bildirim Saati (UTC): Her gün 18:00")

    # 3. Adım: Ana akışta schedule kütüphanesini sürekli çalıştırarak zamanlanmış görevleri takip et
    while True:
        schedule.run_pending()
>>>>>>> c784bd5 (Update Mexalounge_All_in_One and gitignore)
        time.sleep(1)