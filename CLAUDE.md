# CLAUDE.md — ReliefWeb RAG Sistemi

## Proje Amacı
İnsani yardım izleme-değerlendirme (M&E) ekibi için ReliefWeb içerikleri üzerinden
Türkçe/İngilizce çok dilli sohbet yapılabilen RAG sistemi. Şu an yerel geliştirme aşamasında;
deployment kararı proje olgunlaştıktan sonra verilecek.

---

## Mimari

```
ReliefWeb API → Ingestion Pipeline → Pinecone (serverless vektör DB)
                                            ↓
Kullanıcı → Vue 3 Frontend → FastAPI (localhost:8001) → RAG Engine (LangChain LCEL)
                                          ↓                        ↓
                  Gemini embedding (gemini-embedding-001, 3072 boyut)    Gemini (chat yanıtı)
                  + query processor (gemini-2.5-flash)
```

- **Chat yanıtı:** Google Gemini `gemini-2.5-flash` (OpenAI-uyumlu endpoint).
- **Query processor + embedding:** Google Gemini (`gemini-2.5-flash` + `gemini-embedding-001`).
- **Vector DB:** Pinecone serverless (`reliefweb-docs`).

---

## Tech Stack

| Katman | Teknoloji | Notlar |
|--------|-----------|--------|
| Chat LLM | Google Gemini `gemini-2.5-flash` | OpenAI-uyumlu endpoint |
| Query processor LLM | Google Gemini `gemini-2.5-flash` | Filtre çıkarma (json_mode) + rule-based fallback |
| Embedding | Google Gemini `gemini-embedding-001` | 3072 boyut |
| Vector DB | Pinecone serverless | Bulut; `reliefweb-docs` index |
| Backend | Python 3.12 / FastAPI | REST + SSE; Vue statik sunumu; port **8001** |
| RAG Framework | LangChain LCEL | Düz `prompt \| llm \| StrOutputParser`; history route'da manuel beslenir |
| Web UI | Vue 3 + Vite | Chat arayüzü, SSE streaming, kaynak gösterimi |

---

## Dosya Yerleşim İlkeleri

- **Kök:** giriş noktaları — `config.py`, `requirements.txt`, `MEMORY.md`
- **`api/`** — FastAPI app + route'lar (`chat.py`, `health.py`)
- **`frontend/`** — Vue 3 SPA (`src/`), Vite build (`dist/`), `src/utils/parseSSE.js`
- **`ingestion/`** — `client.py`, `parser.py`, `chunker.py`, `store.py`,
  `pipeline.py`, `file_loader.py` (HTML strip + PDF), `scheduler.py` (APScheduler)
- **`rag/`** — `embeddings.py`, `retriever.py`, `chain.py`, `query_processor.py`, `history.py`
- **`tests/`** — pytest, modül yapısını yansıtır
- **`scripts/`** — CLI (`ingest.py`, `setup_pinecone.py`)

---

## Ortam Değişkenleri (.env)

```env
# Google Gemini (chat + sorgu işleme + embedding — OpenAI-uyumlu endpoint)
GEMINI_API_KEY=xxx
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_LLM_MODEL=gemini-2.5-flash      # chat yanıtı
GEMINI_QUERY_MODEL=gemini-2.5-flash    # filtre çıkarma
GEMINI_EMBED_MODEL=gemini-embedding-001

# Pinecone (serverless vektör DB)
PINECONE_API_KEY=xxx
PINECONE_INDEX=reliefweb-docs
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
PINECONE_NAMESPACE=

# ReliefWeb
RELIEFWEB_APPNAME=xxx           # URL param: ?appname=...  (Bearer auth YOK)
RELIEFWEB_BASE_URL=https://api.reliefweb.int/v2

# Embedding
EMBED_DIM=3072                  # gemini-embedding-001 → 3072
EMBED_BATCH_SIZE=32

# RAG retrieval
CHUNK_SIZE=1500                 # karakter (recursive ~1500 char splitter)
CHUNK_OVERLAP=200
TOP_K_RETRIEVAL=5
MMR_FETCH_K=20
MMR_LAMBDA=0.5
RERANK_BY_DATE=True
DATE_DECAY_FACTOR=0.3

# Session / API / Ingestion
HISTORY_WINDOW_K=5
SESSION_MAX_MEMORY=1000
REDIS_URL=                      # boşsa in-memory (LRU eviction)
CORS_ORIGINS=http://localhost:5173,http://localhost:8001
API_HOST=127.0.0.1
API_PORT=8001
FETCH_PDF_CONTENT=False         # PDF eklerini indir+parse et (yavaş, opsiyonel)
INGEST_SCHEDULE_HOURS=12
INGEST_WATERMARK_PATH=./.last_ingest.json
INGEST_LOOKBACK_YEARS=3         # --date-from yoksa manuel ingest tazelik tabanı (0 = sınır yok)
```

---

## ReliefWeb API

`ingestion/client.py` → `ENDPOINT_CONFIG` 3 endpoint tanımlar: `reports` (ana kaynak),
`disasters`, `countries`. (`/updates` ReliefWeb'de yok; `/reports` güncellemeleri kapsar.)

Çekilen alanlar metadata olur: `title, body, date.created, source.name,
primary_country.name, theme.name, format.name, file`. Sıralama `date.created:desc`.

**Ingestion kuralları:**
- `doc_id = sha256(kanonik reliefweb.int/report/{id})` — dosya URL'si değişse bile sabit kalır
- Upsert öncesi eski chunk'lar silinir (`delete_document_chunks`) → yetim chunk kalmaz
- Embedding'ler dokümanlar arası toplu (`EMBED_BATCH_SIZE`), upsert tek seferde
- 429/5xx → exponential backoff; 4xx → hemen başarısız (retry yok)
- Ülke adları normalize edilir ("Iran (Islamic Republic of)" → retriever `$in` ile eşler)
- `scheduler.py` — APScheduler + watermark (`INGEST_WATERMARK_PATH`, varsayılan `./.last_ingest.json`) ile incremental

---

## RAG Pipeline

**Query processor** (`rag/query_processor.py`): LLM-first filtre çıkarma (`json_mode` +
`QueryFilters` Pydantic) → başarısızsa rule-based fallback (`_COUNTRY_MAP`/`_THEME_MAP`/
`_DOCTYPE_MAP` + regex). dict-based cache (512 giriş, `None` cache'lenmez), LLM timeout 5s.
"şu anda / güncel / latest" gibi belirsiz ifadeler date filtresi ÜRETMEZ; `date_from`
bugün/gelecek ise reddedilir.

**Retriever** (`rag/retriever.py`): Pinecone MMR
(`k=TOP_K_RETRIEVAL`, `fetch_k=MMR_FETCH_K`, `lambda_mult=MMR_LAMBDA`). `_build_pinecone_filter`
→ `$eq`/`$in`; country `$in` (kısa+tam ad).
**Tarih filtresi:** Pinecone'da sunucu tarafında sayısal `date_ts` `$gte`; `apply_date_filter`
ek savunmacı katman.
`rerank_by_recency` → MMR + üstel recency blend.

**Chain** (`rag/chain.py`): düz LCEL `prompt | llm | StrOutputParser`. Gemini `ChatOpenAI`.
History route'da `get_session_history` ile alınır,
`chat_history` olarak geçilir, yanıt sonrası kaydedilir (RunnableWithMessageHistory YOK).

**Metadata şeması (her chunk, Pinecone):**
```python
{"doc_id", "url", "title", "country", "iso3", "theme", "themes" (varsa; tüm sektör
 temaları), "language", "glide" (bağlı/ilgili afetin GLIDE kodu), "disaster_type"
 (yalnız doctype=disaster; primary_type.name → yoksa type[0].name fallback),
 "date" (YYYY-MM-DD), "date_ts" (sayısal YYYYMMDD, Pinecone $gte için), "source",
 "format", "doctype"}  # doc_id orphan cleanup için kullanılır
```

**Endpoint'ler** (`api/routes/chat.py`): `POST /chat/stream` (SSE, token-by-token) +
`POST /chat` (non-streaming). Boş retrieval → LLM'e gitmeden net "belge bulunamadı" mesajı.
Selamlaşma → retrieval atlanır. Mesaj doğrulama: boş/4000+ karakter reddedilir.

---

## Oturum Sürekliliği

- **Her oturum başında `MEMORY.md` dosyasını oku.** Projenin güncel durumu, veri durumu ve
  sıradaki adımlar oradadır. "Nerede kalmıştık?" sorusunun cevabı bu dosyadır.
- **Önemli ilerlemeden sonra `MEMORY.md`'yi güncel tut.** Tarihçe biriktirme — güncel durumu
  yansıt (eskiyen satırları değiştir/sil), son güncelleme tarihini güncelle.

---

## Geliştirme Kuralları

1. **API anahtarları** yalnızca `.env` içinde — asla kod veya commit'te.
2. **Ingestion idempotent**: kanonik URL `doc_id` + upsert öncesi orphan temizliği.
3. **Rate limiting**: ReliefWeb 429/5xx → backoff; 4xx → retry yok; Gemini → retry x3.
4. **Loglama**: her modülde `logger = logging.getLogger(__name__)`.
5. **Testler**: `tests/` altında pytest; değişiklikten sonra `python -m pytest tests/ -q`.

---

## Bilinen Kısıtlamalar

- Görseller/infografikler doğrudan sorgulanamaz; başlık + açıklama metadata'sı index'lenir.
- Session history varsayılan in-memory (restart'ta silinir); `REDIS_URL` ile kalıcı yapılabilir.
- Pipeline resume kısmi (watermark var, uzun kesinti tam test edilmedi).
- CORS şu an localhost origin'leri — production'da `CORS_ORIGINS` daraltılmalı.
- PDF içerik ingestion opsiyonel (`FETCH_PDF_CONTENT=False`); varsayılan sadece HTML `body`.
- Pinecone serverless metadata-filtreli silme desteklemez; orphan temizliği chunk-id prefix (`{doc_id}_`) list+delete ile yapılır.
- Gemini embedding OpenAI-uyumlu endpoint üzerinden çalışır; `task_type` (`RETRIEVAL_DOCUMENT`/`QUERY`) ayrımı yok (küçük kalite ödünü).
- Hesap silme (DELETE /auth/me) in-memory chat history pencerelerini temizler; REDIS_URL ile kalıcı history kullanılıyorsa Redis'teki pencereler TTL dolana dek kalır (bugünkü deploy in-memory).
