import os
import re
import time
import json
import subprocess
import threading
from bs4 import BeautifulSoup
import cloudscraper
import pymysql
from google.cloud import texttospeech
import schedule

# Google Cloud JSON anahtar dosyasının yolu
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    r"C:\Users\kadir\Desktop\Radyo Botu\mexalounge-radio-0926e73fdef7.json"
)

# ==========================================
# --- 1. BÖLÜM: GLOBAL EVENT RADAR (XCEED) ---
# ==========================================
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

def fetch_events():
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


# --- KARA LİSTE (İSTENMEYEN KELİME VE İFADELER) ---
BLACKLIST_KEYWORDS = [
    "church-bells", "presentation-logo", "radio-for-all", "kamuspotu", "kamu spotu", 
    "radyo spotu", "spotu", "lösev", "tühsev", "darussafaka", "darüşşafaka", 
    "tev okula donus", "jingle", "intro", "tohum otizm vakfı", "türkiye spastik çocuklar vakfı", 
    "tkd kamu spotu", "canım kardeşim", "swepper", "mexalounge radio", "radio1", "radio2",
    "radio4", "radio3", "radio5", "presentation-logo-version-beat-way-up", "radio-for-all-trance-505926"
]

def build_blacklist_sql_condition():
    conditions = []
    for word in BLACKLIST_KEYWORDS:
        w = word.lower()
        conditions.append(f"LOWER(title) NOT LIKE '%{w}%'")
        conditions.append(f"LOWER(artist) NOT LIKE '%{w}%'")
    return " AND ".join(conditions)


# --- 2. BÖLÜM: RADYODJ MYSQL GEÇMİŞ PARÇALAR ---
def fetch_radio_history():
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
    except Exception as e:
        print(f"\n[!] MYSQL HATA YAKALANDI (History): {e}\n")


# --- 2.1 BÖLÜM: TOP 20 LİSTESİ (SON 7 GÜN) ---
def fetch_top_tracks():
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
                WHERE date_played >= NOW() - INTERVAL 7 DAY 
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
                
            print("top20.json son 7 günlük filtrelenmiş verilerle güncellendi.")
        db.close()
    except Exception as e:
        print(f"\n[!] MYSQL HATA YAKALANDI (Top 20): {e}\n")


# --- 3. BÖLÜM: OTOMATİK GİT PUSH ---
def push_to_github():
    print("--- GitHub Güncellemesi Başlatılıyor ---")
    try:
        subprocess.run(["git", "add", "history.json", "events.json", "top20.json"], check=True)
        subprocess.run(["git", "commit", "-m", "Filtrelenmis JSON (history, events, top20) guncellemesi (Bot)"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Başarıyla GitHub'a yüklendi!")
    except Exception as e:
        print(f"⚠️ Git gönderim uyarısı (Değişiklik olmayabilir): {e}")


# --- 15 DAKİKALIK DÖNGÜ FONKSİYONU ---
def ithub_and_events_loop():
    print("🔄 15 dakikalık Xceed/MySQL/GitHub döngü iş parçacığı başlatıldı.")
    while True:
        try:
            start_time = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n=== [15dk Döngü] Başlangıç Zamanı: {start_time} ===")
            
            fetch_events()
            fetch_radio_history()
            fetch_top_tracks()
            push_to_github()
            
            print(f"[15dk Döngü] İşlem tamamlandı. Sonraki çalıştırılma 15 dakika sonra...")
        except Exception as e:
            print(f"15dk Döngü sırasında hata oluştu: {e}")

        time.sleep(15 * 60)


# ==========================================
# --- 4. BÖLÜM: BBC HABERLERİ & SESLENDİRME ---
# ==========================================
FILTRE_KAPLARI = [
    r"copyright",
    r"all rights reserved",
    r"not responsible for the content",
    r"external sites",
    r"external linking",
    r"read about our approach",
]

def metin_gecerli_mi(metin):
  for kalip in FILTRE_KAPLARI:
    if re.search(kalip, metin, re.IGNORECASE):
      return False
  return True

def generate_google_cloud_news_mp3(url_listesi):
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


# ==========================================
# --- ANA ÇALIŞTIRMA (BİRLEŞTİRİLMİŞ) ---
# ==========================================
if __name__ == "__main__":
    print("🚀 Mexalounge Entegre Bot Sistemi Başlatılıyor...")

    # 1. Adım: Xceed / MySQL / GitHub döngüsünü arka planda (Ayrı bir iş parçacığında - Thread) başlat
    t = threading.Thread(target=ithub_and_events_loop, daemon=True)
    t.start()

    # 2. Adım: BBC Haber Zamanlayıcısını ayarla (07:55, 11:55, 15:55, 19:55, 23:55)
    hedef_siteler = [
        "https://www.bbc.com/news/world/europe",
        "https://www.bbc.com/news/us-canada",
    ]

    calisma_saatleri = ["07:55", "11:55", "15:55", "19:55", "23:55"]

    for saat in calisma_saatleri:
      schedule.every().day.at(saat).do(generate_google_cloud_news_mp3, hedef_siteler)

    print("[*] Haber zamanlayıcısı aktif. Belirtilen saatler bekleniyor...")
    print(f"[*] Haber Saatleri: {', '.join(calisma_saatleri)}")

    # 3. Adım: Ana akışta schedule kütüphanesini sürekli döndürerek haber saatlerini takip et
    while True:
      schedule.run_pending()
      time.sleep(1)