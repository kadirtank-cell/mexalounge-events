import json
import time
import subprocess
import cloudscraper
from bs4 import BeautifulSoup
import pymysql

# --- 1. BÖLÜM: GLOBAL EVENT RADAR (XCEED SCRAPER) ---
urls = [
    "https://xceed.me/en/barcelona/events",
    "https://xceed.me/en/roma/events",
    "https://xceed.me/en/brussels/events",
    "https://xceed.me/en/hamburg/events",
    "https://xceed.me/en/artist/carl-cox",
    "https://xceed.me/en/artist/charlotte-de-witte",
    "https://xceed.me/en/london/events",
    "https://xceed.me/en/artist/amelie-lens"
]

scraper = cloudscraper.create_scraper()

def fetch_events():
    all_events = []
    print("\n--- Global Event Radar Taraması Başlıyor ---")

    for url in urls:
        try:
            print(f"Taranıyor: {url}")
            response = scraper.get(url, timeout=20)
            
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


# --- 2. BÖLÜM: RADYODJ MYSQL GEÇMİŞ PARÇALAR ---
def fetch_radio_history():
    print("--- RadyoDJ Geçmiş Parçalar Güncelleniyor ---")
    try:
        db = pymysql.connect(
            host="127.0.0.1",
            user="root",
            password="",
            database="mexalounge_database",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5
        )
        
        with db.cursor() as cursor:
            query = "SELECT artist, title, date_played FROM history ORDER BY id DESC LIMIT 10"
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
                
            print("history.json güncel RadyoDJ verileriyle yenilendi.")
            
        db.close()

    except Exception as e:
        print(f"\n[!] MYSQL HATA YAKALANDI: {e}\n")


# --- 3. BÖLÜM: OTOMATİK GİT PUSH ---
def push_to_github():
    print("--- GitHub Güncellemesi Başlatılıyor ---")
    try:
        subprocess.run(["git", "add", "history.json", "events.json"], check=True)
        subprocess.run(["git", "commit", "-m", "Otomatik JSON guncellemesi (Bot)"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Başarıyla GitHub'a yüklendi!")
    except Exception as e:
        print(f"⚠️ Git gönderim uyarısı (Değişiklik olmayabilir): {e}")


# --- 4. BÖLÜM: 15 DAKİKALIK DÖNGÜ (MAIN) ---
if __name__ == "__main__":
    print("Mexalounge Otomatik Senkronizasyon Botu Başlatıldı (15 dakikada bir çalışacak)...")
    
    # 15 dakika = 15 * 60 = 900 saniye
    INTERVAL_SECONDS = 15 * 60 

    while True:
        try:
            start_time = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n=== Döngü Başlangıç Zamanı: {start_time} ===")
            
            fetch_events()
            fetch_radio_history()
            push_to_github()
            
            print(f" İşlem tamamlandı. Sonraki çalıştırılma 15 dakika sonra...")
        except Exception as e:
            print(f"Döngü sırasında hata oluştu: {e}")

        # 15 dakika beklet
        time.sleep(INTERVAL_SECONDS)