# CLAUDE.md — ReliefWeb RAG Sistemi

## Proje Amacı
İnsani yardım izleme-değerlendirme (M&E) ekibi için ReliefWeb içerikleri üzerinden
Türkçe/İngilizce çok dilli sohbet yapılabilen RAG sistemi.
Şu an yerel geliştirme aşamasındadır; deployment kararı proje olgunlaştıktan sonra verilecektir.

---

## Mimari

```
ReliefWeb API → Ingestion Pipeline → ChromaDB (yerel dosya)
                                            ↓
Kullanıcı → Chainlit UI (localhost:8000) → RAG Engine (LangChain) → Ollama Cloud LLM
                                                   ↑
                               Yerel Ollama (embedding, localhost:11434)
```

---

## Tech Stack

| Katman        | Teknoloji                       | Notlar                                     |
|---------------|---------------------------------|--------------------------------------------|
| LLM           | Ollama Cloud API                | https://ollama.com/v1 — `qwen3.5:397b-cloud` |
| Embedding     | Yerel Ollama — qwen3-embedding:8b | localhost:11434, 4096 dim, MTEB çok dilli #1 |
| Vector DB     | ChromaDB                        | Gömülü, dosya tabanlı — `./chroma_db/`     |
| Backend       | Python 3.12                     | Chainlit doğrudan RAG chain'i çağırır      |
| RAG Framework | LangChain                       | ConversationalRetrievalChain + MMR, agent-ready |
| Web UI        | Chainlit                        | Chat arayüzü, basit auth, kaynak gösterimi |

---

## Dosya Yerleşim İlkeleri

- **Kök dizin:** Giriş noktaları — `chainlit_app.py`, `config.py`, `requirements.txt`
- **`ingestion/`** — ReliefWeb'den veri çekme, parse etme, güncelleme mantığı
- **`rag/`** — embedding, retriever, LangChain zinciri
- **`tests/`** — pytest testleri, modül yapısını yansıtır (`test_ingestion.py` vb.)
- **`scripts/`** — CLI komutları (`ingest.py` vb.)
- **`chroma_db/`** — ChromaDB verileri, `.gitignore`'da olmalı

---

## Ortam Değişkenleri (.env)

```env
# Ollama Cloud (LLM)
OLLAMA_CLOUD_API_KEY=xxx
OLLAMA_CLOUD_BASE_URL=https://ollama.com/v1
OLLAMA_LLM_MODEL=qwen3.5:397b-cloud

# Ollama Local (Embedding)
OLLAMA_LOCAL_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=qwen3-embedding:8b

# ReliefWeb
RELIEFWEB_APPNAME=berk_sitrep-u6dANX1qkKQivDDN   # URL param olarak gönderilir: ?appname=...
RELIEFWEB_BASE_URL=https://api.reliefweb.int/v1

# ChromaDB
CHROMA_DB_PATH=./chroma_db
CHROMA_COLLECTION=reliefweb_docs
EMBED_DIM=4096                  # qwen3-embedding:8b — Ollama ve ChromaDB aynı değeri kullanır

# Chainlit
CHAINLIT_AUTH_SECRET=change_this_secret
CHAINLIT_USERS=user1:pass1,user2:pass2

# RAG
CHUNK_SIZE=800
CHUNK_OVERLAP=100
TOP_K_RETRIEVAL=5
INGEST_SCHEDULE_HOURS=12
```

---

## ReliefWeb API

```python
ENDPOINTS = {
    "reports":   "/reports",   # PDF/HTML — ana kaynak
    "updates":   "/updates",   # Haberler, durum güncellemeleri
    "disasters": "/disasters", # Afet profilleri
    "countries": "/countries", # Ülke profilleri
}

# Çekilecek alanlar — bunlar ChromaDB'ye metadata olarak kaydedilir
FIELDS = ["title", "body", "date.created", "source.name",
          "primary_country.name", "theme.name", "format.name", "file"]

# Yaygın tema değerleri (ReliefWeb taksonomisi — referans, zorunlu filtre değil)
THEMES = ["Food and Nutrition", "Health", "Shelter and NFI",
          "Water Sanitation Hygiene", "Protection", "Education",
          "Logistics and Telecommunications", "Coordination"]
```

**Ingestion kuralları:**
- `date.created`, `primary_country.name`, `theme.name` her chunk'a metadata olarak eklenir
- Sıralama: `date.created:desc` — en yeni belgeler önce işlenir
- Sayfalama: `offset + limit` döngüsü, limit max 1000

---

## RAG Zinciri

Sistem üç sorgu tipini ayırt etmeli ve buna göre retrieval yapmalı:

```python
# Aşama 1 — Sorgu önişleme (LLM ile)
# Kullanıcı sorgusundan yapısal filtreler çıkarılır:
# "İran'da son 1 ay" → {country: "Iran", date_from: "30 gün önce"}
# "gıda sektörü"     → {theme: "Food and Nutrition"}
# "başa çıkma stratejileri" → {} (semantik arama yeterli)

# Aşama 2 — Filtrelenmiş retrieval
retriever = chroma.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": 5,
        "filter": extracted_filters  # boşsa saf semantik arama
    }
)
```

**ChromaDB metadata şeması** (her chunk için):
```python
# ChromaDB doküman ID'si (tekrar işlemeyi önler): sha256(url)
# Metadata alanları (filtrelenebilir):
{
    "url":     "https://...",
    "title":   "...",
    "country": "Iran",
    "theme":   "Food and Nutrition",
    "date":    "2026-04-01",   # ISO format
    "source":  "WFP",
    "format":  "Situation Report",
}
```

**Bellek ve sistem promptu:**
```python
memory = ConversationBufferWindowMemory(k=5, return_messages=True)
```
```
Sen ReliefWeb veritabanındaki insani yardım belgelerini analiz eden asistansın.
YALNIZCA sağlanan belgelerden yararlan. Belgede olmayan bilgileri uydurma.
Kullanıcının dilinde yanıt ver (Türkçe veya İngilizce).
Tarih veya ülke filtresi uygulandıysa bunu yanıtın başında belirt.
Her yanıtın sonunda kullandığın kaynak URL ve tarihlerini listele.
```

---

## Geliştirme Kuralları

1. **API anahtarları** yalnızca `.env` içinde — asla kod veya commit'te
2. **`chroma_db/`** `.gitignore`'a ekle — vektör verisi repoya girmesin
3. **Ingestion idempotent**: `doc_id = sha256(url)` — aynı belge iki kez işlenmez
4. **Rate limiting**: ReliefWeb 429 → exponential backoff; Ollama timeout → retry x3
5. **Loglama**: Her modülde `logger = logging.getLogger(__name__)`
6. **Testler**: `tests/` altında `pytest`; ingestion, retriever ve chain için test yaz

---

## Bilinen Kısıtlamalar

- Embedding yerel çalışır — ingestion sırasında `ollama serve` ayakta olmalı
- qwen3-embedding:8b → ~4.7GB RAM; yetersizse `qwen3-embedding:4b` (2.5GB) kullan
- Görseller/infografikler doğrudan sorgulanamaz; başlık + açıklama metadata'sı index'lenir
- "Son 1 ay" gibi göreceli tarihler sorgu önişleme adımında mutlak tarihe çevrilmeli
