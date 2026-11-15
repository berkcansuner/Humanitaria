# CLAUDE.md — ReliefWeb RAG Sistemi

## Proje Amacı
ReliefWeb içerikleri üzerinden Türkçe/İngilizce çok dilli sohbet yapılabilen RAG sistemi.
**Birincil kullanıcı:** insani yardım sektöründeki izleme-değerlendirme (M&E) çalışanları;
**ikincil:** analistler, araştırmacılar ve gazeteciler. Çatışmada M&E ihtiyacı önceliklidir
(ürün bağlamı: `PRODUCT.md`). Şu an yerel geliştirme aşamasında;
deployment kararı proje olgunlaştıktan sonra verilecek.

---

## Mimari

```
ReliefWeb API → Ingestion Pipeline → Postgres + pgvector (Supabase; chunks + documents)
                                            ↓
Kullanıcı → Vue 3 Frontend → FastAPI (localhost:8001) → RAG Engine (LangChain LCEL)
                                          ↓                        ↓
                  Gemini embedding (gemini-embedding-001, 768 boyut)     Gemini (chat yanıtı)
                  + query processor (gemini-2.5-flash)
```

- **Chat yanıtı:** Google Gemini `gemini-2.5-flash` (OpenAI-uyumlu endpoint).
- **Query processor + embedding:** Google Gemini (`gemini-2.5-flash` + `gemini-embedding-001`).
- **Vector DB:** Postgres + pgvector (prod: Supabase, `chunks` tablosu, `halfvec(768)` + HNSW).
- **Reranker:** Pinecone Inference (`bge-reranker-v2-m3`) — Pinecone'da VERİ TUTULMAZ, yalnız rerank API'si.

---

## Tech Stack

| Katman | Teknoloji | Notlar |
|--------|-----------|--------|
| Chat LLM | Google Gemini `gemini-2.5-flash` | OpenAI-uyumlu endpoint |
| Query processor LLM | Google Gemini `gemini-2.5-flash` | Filtre çıkarma (json_mode) + rule-based fallback |
| Embedding | Google Gemini `gemini-embedding-001` | 768 boyut (API'de kırpılır) |
| Vector DB | Postgres + pgvector | Supabase; `chunks` (halfvec + HNSW) + `documents` |
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
- **`analytics/`** — teknik izleme raporu: `hapi_client.py` (HDX HAPI fetch),
  `indicators.py` (indikatör→endpoint eşleme), `datasets.py` (HAPI→zaman serisi),
  `stat_tests.py` (saf istatistik: trend/karşılaştırma/bölge/korelasyon),
  `charts.py` (matplotlib→base64), `technical_report.py` (orkestratör), `countries.py` (ISO3)
- **`tests/`** — pytest, modül yapısını yansıtır
- **`scripts/`** — CLI (`ingest.py`, `eval_rag.py`)

---

## Ortam Değişkenleri (.env)

```env
# Google Gemini (chat + sorgu işleme + embedding — OpenAI-uyumlu endpoint)
GEMINI_API_KEY=xxx
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_LLM_MODEL=gemini-2.5-flash      # chat yanıtı
GEMINI_QUERY_MODEL=gemini-2.5-flash    # filtre çıkarma
GEMINI_EMBED_MODEL=gemini-embedding-001

# Veritabanı: app tabloları + vektör index'i (pgvector). Boş = yerel SQLite (vektör araması YOK)
DATABASE_URL=

# Pinecone — yalnız hosted reranker (Pinecone Inference)
PINECONE_API_KEY=xxx

# ReliefWeb
RELIEFWEB_APPNAME=xxx           # URL param: ?appname=...  (Bearer auth YOK)
RELIEFWEB_BASE_URL=https://api.reliefweb.int/v2

# Embedding
EMBED_DIM=768                   # gemini-embedding-001, API'de 768'e kırpılır (chunks.embedding halfvec(768))
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
CORS_ORIGINS=http://localhost:5173,http://localhost:8001
API_HOST=127.0.0.1
API_PORT=8001
FETCH_PDF_CONTENT=False         # PDF eklerini indir+parse et (yavaş, opsiyonel)
INGEST_SCHEDULE_HOURS=12
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
- `scheduler.py` — APScheduler + watermark (DB `ingest_state` tablosu; Render diski geçici) ile incremental.
  Artımlı çalışma eskiden yeniye işler; başarısız batch ya da limitte kesilen çalışma watermark'ı
  o belgenin `date.created` değerinde tutar (sonraki çalışma oradan devam eder)

---

## RAG Pipeline

**Query processor** (`rag/query_processor.py`): LLM-first filtre çıkarma (`json_mode` +
`QueryFilters` Pydantic) → başarısızsa rule-based fallback (`_COUNTRY_MAP`/`_THEME_MAP`/
`_DOCTYPE_MAP` + regex). dict-based cache (512 giriş, `None` cache'lenmez), LLM timeout 5s.
"şu anda / güncel / latest" gibi belirsiz ifadeler date filtresi ÜRETMEZ; `date_from`
bugün/gelecek ise reddedilir.

**Retriever** (`rag/retriever.py`): pgvector cosine araması (`fetch_k`, HNSW + `iterative_scan`)
→ Python'da MMR (`k`, `MMR_LAMBDA`). `build_sql_filter` → beyaz listeli kolonlar + bind parametreleri;
country `= ANY` (kısa+tam ad), theme `theme = :t OR :t = ANY(themes)`.
**Tarih filtresi:** SQL'de sayısal `date_ts` aralığı; `apply_date_filter` ek savunmacı katman.
`rerank_by_recency` → MMR + üstel recency blend.

**Chain** (`rag/chain.py`): düz LCEL `prompt | llm | StrOutputParser`. Gemini `ChatOpenAI`.
History route'da `get_session_history` ile alınır,
`chat_history` olarak geçilir, yanıt sonrası kaydedilir (RunnableWithMessageHistory YOK).

**Metadata şeması (her chunk; `chunks.metadata` JSONB, filtre alanları ayrıca kolon):**
```python
{"doc_id", "url", "title", "country", "iso3", "theme", "themes" (varsa; tüm sektör
 temaları), "language", "glide" (bağlı/ilgili afetin GLIDE kodu), "disaster_type"
 (yalnız doctype=disaster; primary_type.name → yoksa type[0].name fallback),
 "date" (YYYY-MM-DD), "date_ts" (sayısal YYYYMMDD, SQL tarih aralığı için), "source",
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
6. **Tasarım değişiklikleri geri alınabilir olmalı**: her UI/tasarım işi kendi branch'inde,
   her mantıksal adım ayrı commit (alakasız işle birleştirme yok); değişiklikten önce ve sonra
   ekran görüntüsü alınır. Kullanıcı sonradan beğenmezse adım tek başına `git revert` edilebilmeli.
   Onaylanan comp'lar `.impeccable/mocks/` altında saklanır.

---

## Bilinen Kısıtlamalar

- Görseller/infografikler doğrudan sorgulanamaz; başlık + açıklama metadata'sı index'lenir.
- Sohbet geçmişi penceresi in-memory (LRU); restart sonrası `messages` tablosundan yeniden yüklenir.
- Pipeline resume kısmi (watermark var, uzun kesinti tam test edilmedi).
- CORS şu an localhost origin'leri — production'da `CORS_ORIGINS` daraltılmalı.
- PDF içerik ingestion opsiyonel (`FETCH_PDF_CONTENT=False`); varsayılan sadece HTML `body`.
- Vektör araması yalnız Postgres'te (pgvector ≥0.7 `halfvec`, ≥0.8 `iterative_scan`); yerel SQLite'ta yok.
  Entegrasyon testleri `TEST_DATABASE_URL` ile (CI: `pgvector/pgvector:pg17` servisi).
- Supabase ücretsiz plan: 500 MB DB sınırı (768-dim halfvec ile ~40K chunk ≈ 200 MB) ve 7 gün hareketsizlikte duraklama (gece cron'u önler).
- Gemini embedding OpenAI-uyumlu endpoint üzerinden çalışır; `task_type` (`RETRIEVAL_DOCUMENT`/`QUERY`) ayrımı yok (küçük kalite ödünü).
