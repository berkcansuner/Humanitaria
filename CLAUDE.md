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
Kullanıcı → Vue 3 Frontend → FastAPI (localhost:8000) → RAG Engine (LangChain) → Ollama Cloud LLM
                                                              ↑
                                          Yerel Ollama (embedding, localhost:11434)
```

---

## Tech Stack

| Katman        | Teknoloji                       | Notlar                                     |
|---------------|---------------------------------|--------------------------------------------|
| LLM           | Ollama Cloud API                | https://ollama.com/v1 — `qwen3.5:397b-cloud` |
| Embedding     | Yerel Ollama — qwen3-embedding:8b | localhost:11434, **4096 dim**, MTEB çok dilli #1 |
| Vector DB     | ChromaDB                        | Gömülü, dosya tabanlı — `./chroma_db/`     |
| Backend       | Python 3.12 / FastAPI           | REST API + Vue statik dosya sunumu          |
| RAG Framework | LangChain LCEL                   | RunnableWithMessageHistory + MMR retriever (session-based) |
| Web UI        | Vue 3 + Vite                    | Chat arayüzü, kaynak gösterimi              |

---

## Dosya Yerleşim İlkeleri

- **Kök dizin:** Giriş noktaları — `config.py`, `requirements.txt`
- **`api/`** — FastAPI uygulaması, route'lar (`chat.py`, `health.py`)
- **`frontend/`** — Vue 3 SPA (`src/`), Vite build (`dist/`)
- **`ingestion/`** — ReliefWeb'den veri çekme, parse etme, güncelleme mantığı
- **`rag/`** — embedding, retriever, LangChain zinciri, query processor
- **`tests/`** — pytest testleri, modül yapısını yansıtır
- **`scripts/`** — CLI komutları (`ingest.py` vb.)
- **`chroma_db/`** — ChromaDB verileri, `.gitignore`'da

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
RELIEFWEB_BASE_URL=https://api.reliefweb.int/v2

# ChromaDB
CHROMA_DB_PATH=./chroma_db
CHROMA_COLLECTION=reliefweb_docs
EMBED_DIM=4096                  # qwen3-embedding:8b → 4096 dim; 4b varyantı → 2560

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
    "reports":   "/reports",   # PDF/HTML — ana kaynak (şu an sadece bu kullanılıyor)
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
# Aşama 1 — Sorgu önişleme (rule-based, LLM upgrade planlanıyor)
# Kullanıcı sorgusundan yapısal filtreler çıkarılır:
# "İran'da son 1 ay" → {country: "Iran", date: {"$gte": "2026-04-07"}}
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

**LLM ve sistem promptu:**
```python
llm = ChatOpenAI(model="qwen3.5:397b-cloud", base_url="https://ollama.com/v1", streaming=True)
chain = prompt | llm | StrOutputParser()  # LCEL zinciri
wrapped = RunnableWithMessageHistory(chain, get_session_history, ...)
# Türkçe system prompt: sadece sağlanan belgeleri kullan, kullanıcının dilinde yanıt ver
```

**Sorgu önişleme (LLM-first, rule-based fallback):**
```python
# 1. LLM (json_mode) ile filtre çıkarma → QueryFilters Pydantic modeli
# 2. LLM başarısız → rule-based fallback (_COUNTRY_MAP, _THEME_MAP, _DOCTYPE_MAP, regex)
# 3. Sonuçlar LRU cache (256 giriş) ile cache'lenir
```

**Streaming:**
- `POST /chat/stream` — SSE endpoint, token-by-token yanıt
- Frontend `fetch + ReadableStream` ile SSE parse eder
- `POST /chat` — backward-compatible non-streaming endpoint

---

## Oturum Sürekliliği

- **Her oturum başında `MEMORY.md` dosyasını oku.** Projenin güncel durumu, veri durumu ve
  sıradaki adımlar oradadır. "Nerede kalmıştık?" sorusunun cevabı bu dosyadır.
- **Önemli ilerlemeden sonra `MEMORY.md`'yi güncel tut.** Tarihçe biriktirme — güncel durumu
  yansıt (eskiyen satırları değiştir/sil), son güncelleme tarihini güncelle.

---

## Geliştirme Kuralları

1. **API anahtarları** yalnızca `.env` içinde — asla kod veya commit'te
2. **`chroma_db/`** `.gitignore`'da — vektör verisi repoya girmesin
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
- Session history in-memory only — server restart tüm oturumları temizler
- `RunnableWithMessageHistory` deprecated (LangGraph migration gelecekte planlanıyor)
- Query processor LLM-first (rule-based fallback) — LLM timeout → 5 saniye limit
- `/updates` endpoint'i ReliefWeb API'de mevcut değil — `/reports` zaten güncellemeleri kapsıyor
- Streaming SSE mevcut (`POST /chat/stream`) — frontend token-by-token render eder