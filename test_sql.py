import pymysql

print("PyMySQL test başlatılıyor...")

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
    print("BAĞLANTI BAŞARILI! Veritabanına ulaşıldı.")
    
    # Test sorgusu yapalım
    with db.cursor() as cursor:
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"MySQL Sürümü: {version}")
        
    db.close()
except Exception as e:
    print(f"\n[!] HATA YAKALANDI: {e}")

input("\nTest bitti. Kapatmak için ENTER'a basın...")