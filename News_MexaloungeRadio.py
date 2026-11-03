import os
import re
import time
from bs4 import BeautifulSoup
import cloudscraper
from google.cloud import texttospeech
import schedule

# Google Cloud JSON anahtar dosyasının yolu
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    r"C:\Users\kadir\Desktop\Radyo Botu\mexalounge-radio-0926e73fdef7.json"
)

# Filtrelenecek (atılacak) yasal ve kurumsal kalıplar (case-insensitive)
FILTRE_KAPLARI = [
    r"copyright",
    r"all rights reserved",
    r"not responsible for the content",
    r"external sites",
    r"external linking",
    r"read about our approach",
]


def metin_gecerli_mi(metin):
  """Yasal uyarı veya telif içeren metinleri filtreler."""
  for kalip in FILTRE_KAPLARI:
    if re.search(kalip, metin, re.IGNORECASE):
      return False
  return True


def generate_google_cloud_news_mp3(url_listesi):
  output_filename = r"C:\Users\Kadir\Desktop\Radyo Botu\mexalounge_news.mp3"

  print("\n[*] [Zamanlayıcı Tetiklendi] Haber bülteni üretim süreci başlatılıyor...")
  print("[*] Google Cloud TTS istemcisi başlatılıyor...")
  client = texttospeech.TextToSpeechClient()

  scraper = cloudscraper.create_scraper(
      browser={"browser": "chrome", "platform": "windows", "desktop": True}
  )

  toplam_linkler = []

  # Verilen tüm URL'leri tara ve linkleri topla
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

  # Toplamda hedefimiz en fazla 15 haber seçmek
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

          # Yasal uyarı ve telif filtrelemesi
          if metin_gecerli_mi(haber_metni):
            haber_parcalari.append(haber_metni)
    except Exception as e:
      continue

  if not haber_parcalari:
    print("[-] Hiçbir geçerli haber metni alınamadı.")
    return

  # SSML formatı ile haberler arasına 1 saniyelik duraklama ekleme
  ssml_content = "<speak>" + '<break time="1s"/>'.join(haber_parcalari) + "</speak>"

  print("[*] Google Cloud TTS ile SSML duraklamalı bülten üretiliyor...")

  synthesis_input = texttospeech.SynthesisInput(ssml=ssml_content)

  voice = texttospeech.VoiceSelectionParams(
      language_code="en-US",
      name="en-US-Neural2-D",  # Tok radyo spikeri erkek sesi
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


if __name__ == "__main__":
  hedef_siteler = [
      "https://www.bbc.com/news/world/europe",
      "https://www.bbc.com/news/us-canada",
  ]

  # Belirtilen saatler için zamanlayıcı tanımlamaları
  calisma_saatleri = ["07:55", "11:55", "15:55", "19:55", "23:55"]

  for saat in calisma_saatleri:
    schedule.every().day.at(saat).do(generate_google_cloud_news_mp3, hedef_siteler)

  print("[*] Bot çalıştırıldı. Belirtilen saatleri bekliyor (Uyku modunda)...")
  print(f"[*] Aktif Çalışma Saatleri: {', '.join(calisma_saatleri)}")

  # Kodun sürekli çalışarak saatleri kontrol etmesini sağlayan döngü
  while True:
    schedule.run_pending()
    time.sleep(1)