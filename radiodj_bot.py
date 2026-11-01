import time
import pymysql
import requests

# RadioDJ MySQL Veritabanı Bilgileri
DB_HOST = "127.0.0.1"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "mexalounge_database"

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1f6NdENkYgTlsCvkbjKrvZST9H7gn481I2dZFS8sX6uA/export?format=csv"

processed_requests = set()

def connect_db():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def init_last_request():
    """Bot ilk açıldığında tablodaki mevcut son satırı işlenmiş sayar, eski istekleri tekrar işlemez."""
    try:
        response = requests.get(SHEET_CSV_URL)
        lines = response.text.splitlines()
        if len(lines) > 1:
            last_row = lines[-1].split(',')
            if len(last_row) >= 5:
                timestamp = last_row[0].strip()
                email = last_row[1].strip()
                song_query = last_row[3].strip()
                request_id = f"{timestamp}_{email}_{song_query}"
                processed_requests.add(request_id)
                print(f"[BİLGİ] Mevcut son istek hafızaya alındı, atlanıyor: {song_query}")
    except Exception as e:
        print(f"Başlangıç kontrolü hatası: {e}")

def check_new_requests():
    try:
        response = requests.get(SHEET_CSV_URL)
        lines = response.text.splitlines()
        
        if len(lines) <= 1:
            return

        last_row = lines[-1].split(',')
        if len(last_row) < 5:
            return

        timestamp = last_row[0].strip()
        email = last_row[1].strip()
        listener_name = last_row[2].strip()
        song_query = last_row[3].strip()
        message = last_row[4].strip()

        request_id = f"{timestamp}_{email}_{song_query}"
        if request_id in processed_requests:
            return

        print(f"\n[YENİ İSTEK] Dinleyici: {listener_name} | Aranan Şarkı: {song_query} | Mesaj: {message}")
        
        connection = connect_db()
        with connection.cursor() as cursor:
            song = None
            
            # 1. "Sanatçı - Şarkı" formatı kontrolü
            if " - " in song_query:
                parts = song_query.split(" - ", 1)
                sql_split = "SELECT ID, artist, title, duration, album FROM songs WHERE artist LIKE %s AND title LIKE %s LIMIT 1"
                cursor.execute(sql_split, (f"%{parts[0].strip()}%", f"%{parts[1].strip()}%"))
                song = cursor.fetchone()

            # 2. Genel esnek arama
            if not song:
                sql = "SELECT ID, artist, title, duration, album FROM songs WHERE title LIKE %s OR artist LIKE %s LIMIT 1"
                cursor.execute(sql, (f"%{song_query}%", f"%{song_query}%"))
                song = cursor.fetchone()

            # 3. Kelime bazlı arama
            if not song:
                words = song_query.split()
                for word in words:
                    if len(word) > 2:
                        cursor.execute(sql, (f"%{word}%", f"%{word}%"))
                        song = cursor.fetchone()
                        if song:
                            break

            if song:
                song_id = song['ID']
                artist = song.get('artist', '')
                title = song.get('title', '')
                duration = song.get('duration', 0)
                album = song.get('album', '')
                
                print(f"-> Şarkı Arşivde Bulundu: {artist} - {title} (ID: {song_id})")

                # Doğrudan queuelist tablosuna yazdırıyoruz
                queue_sql = """
                    INSERT INTO queuelist (songID, ETA, duration, artist, title, album, swID, swPlay, vtID, vtPlay) 
                    VALUES (%s, NOW(), %s, %s, %s, %s, 0, 0, 0, 0)
                """
                cursor.execute(queue_sql, (song_id, duration, artist, title, album))
                connection.commit()
                print("-> Başarıyla RadioDJ queuelist Tablosuna Eklendi!")
            else:
                print(f"-> Arşivde bu şarkı bulunamadı: {song_query}")

        connection.close()
        processed_requests.add(request_id)

    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    print("RadioDJ queuelist Doğrudan Yazma Botu Başlatıldı...")
    init_last_request()
    print("Bot aktif! Yeni istekler dinleniyor...\n")
    while True:
        check_new_requests()
        time.sleep(10)