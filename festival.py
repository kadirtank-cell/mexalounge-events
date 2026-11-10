from datetime import datetime
import json
import requests

# RA GraphQL Endpoint adresi
GRAPHQL_URL = "https://ra.co/graphql"

# İstek için gerekli Header'lar (Cloudflare/Bot engeline takılmamak için standart tarayıcı başlıkları)
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://ra.co/events/festivals",
}


def fetch_festivals():
  # Bugünün tarihini ISO formatında alıyoruz (Filtreleme için)
  now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")

  # Yakaladığın GraphQL payload yapısı ve sorgusu
  payload = {
      "operationName": "GET_DEFAULT_EVENTS_LISTING",
      "variables": {
          "indices": ["EVENT"],
          "pageSize": 20,
          "page": 1,
          "aggregations": ["COUNTRY", "YEAR"],
          "filters": [
              {"type": "EVENTTYPE", "value": "festival"},
              {
                  "type": "DATERANGE",
                  "value": json.dumps({"gte": now_iso}),
              },
          ],
          "sortOrder": "ASCENDING",
          "sortField": "EVENTDATE",
          "baseFilters": [
              {"type": "EVENTTYPE", "value": "festival"},
              {
                  "type": "DATERANGE",
                  "value": json.dumps({"gte": now_iso}),
              },
          ],
      },
      "query": """
            query GET_DEFAULT_EVENTS_LISTING($indices: [Index], $pageSize: Int, $page: Int, $filters: [Filter], $sortField: EventSortField, $sortOrder: SortOrder, $baseFilters: [Filter], $aggregations: [Aggregation]) {
              eventListings(
                indices: $indices
                pageSize: $pageSize
                page: $page
                filters: $filters
                sortField: $sortField
                sortOrder: $sortOrder
                baseFilters: $baseFilters
                aggregations: $aggregations
              ) {
                data {
                  item {
                    __typename
                    ... on Event {
                      title
                      date
                      startTime
                      contentUrl
                      interestedCount
                      images {
                        filename
                      }
                      venue {
                        name
                      }
                      area {
                        country {
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
        """,
  }

  try:
    print("Resident Advisor'dan festival verileri çekiliyor...")
    response = requests.post(
        GRAPHQL_URL, json=payload, headers=HEADERS, timeout=15
    )
    response.raise_for_status()
    data = response.json()

    # Gelen verinin içinden etkinlik listesini güvenli bir şekilde alıyoruz
    festivals_raw = data.get("data", {}).get("eventListings", {}).get("data", [])
    processed_festivals = []
    today = datetime.utcnow().date()

    for entry in festivals_raw:
      item = entry.get("item", {})
      if not item:
        continue

      title = item.get("title")
      date_str = item.get("date")  # Örnek: 2026-12-03T00:00:00.000Z
      country = (
          item.get("area", {}).get("country", {}).get("name") or "Bilinmiyor"
      )

      # Görsel URL'sini oluşturma
      images = item.get("images", [])
      image_filename = images[0].get("filename") if images else ""
      if image_filename:
        if image_filename.startswith("http"):
          image_url = image_filename
        else:
          image_url = f"https://images.ra.co/{image_filename}"
      else:
        image_url = ""

      # Tarih ve Kalan Gün Hesaplama
      if date_str:
        festival_date_obj = datetime.strptime(
            date_str.split("T")[0], "%Y-%m-%d"
        ).date()
        days_left = (festival_date_obj - today).days
        formatted_date = festival_date_obj.strftime("%Y-%m-%d")
      else:
        days_left = 0
        formatted_date = ""

      # İstenen JSON formatına uygun sözlük (dict) ekleme
      processed_festivals.append({
          "festival": title,
          "country": country,
          "date": formatted_date,
          "days_left": days_left,
          "image": image_url,
      })

    return processed_festivals

  except requests.exceptions.RequestException as e:
    print(f"API isteği sırasında hata oluştu: {e}")
    return []
  except Exception as e:
    print(f"Veri işlenirken beklenmeyen bir hata oluştu: {e}")
    return []


def main():
  festivals = fetch_festivals()

  if festivals:
    output_file = "festival.json"
    with open(output_file, "w", encoding="utf-8") as f:
      json.dump(festivals, f, indent=2, ensure_ascii=False)
    print(
        f"Başarılı! {len(festivals)} festival '{output_file}' dosyasına"
        " kaydedildi."
    )
  else:
    print("Hiç festival verisi alınamadı, dosya güncellenmedi.")


if __name__ == "__main__":
  main()
# Son guncelleme
