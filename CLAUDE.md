# CLAUDE.md — ReliefWeb RAG Sistemi

## Proje Amacı
İnsani yardım izleme-değerlendirme (M&E) ekibi için ReliefWeb içerikleri üzerinden
Türkçe/İngilizce çok dilli sohbet yapılabilen RAG sistemi. Şu an yerel geliştirme aşamasında;
deployment kararı proje olgunlaştıktan sonra verilecek.

---

## Mimari

```
ReliefWeb API → Ingestion Pipeline → ChromaDB (yerel dosya, ./chroma_db/)
                                            ↓
Kullanıcı → Vue 3 Frontend → FastAPI (localhost:8001) → RAG Engine (LangChain LCEL)
                                          ↓                        ↓              ↓
                          Yerel Ollama (embedding +        Gemini (chat yanıtı)
                          query processor, :11434)
```

- **Chat yanıtı:** Google Gemini (OpenAI-uyumlu endpoint).
- **Query processor + embedding:** yerel Ollama (`localhost:11434`) — varsayılan; `EMBED_PROVIDER=gemini` ile Gemini'ye geçilebilir.
- **Vector DB:** ChromaDB (yerel dosya) — varsayılan; `VECTOR_STORE_PROVIDER=pinecone` ile Pinecone serverless'a geçilebilir.

---

## Tech Stack

| Katman | Teknoloji | Notlar |
|--------|-----------|--------|
| Chat LLM | Google Gemini `gemini-2.5-flash` | OpenAI-uyumlu endpoint; `CHAT_LLM_PROVIDER` ile ollama'ya geçilebilir |
| Query processor LLM | Yerel Ollama `qwen2.5:0.5b` | Filtre çıkarma (json_mode) + rule-based fallback |
| Embedding | Yerel Ollama `qwen3-embedding:8b` (varsayılan) veya Gemini `gemini-embedding-001` | `EMBED_PROVIDER` flag'i; ollama→4096 dim, gemini→3072 dim |
| Vector DB | ChromaDB (varsayılan) veya Pinecone serverless | `VECTOR_STORE_PROVIDER` flag'i; ChromaDB gömülü dosya tabanlı, Pinecone bulut |
| Backend | Python 3.12 / FastAPI | REST + SSE; Vue statik sunumu; port **8001** |
| RAG Framework | LangChain LCEL | Düz `prompt \| llm \| StrOutputParser`; history route'da manuel beslenir |
| Web UI | Vue 3 + Vite | Chat arayüzü, SSE streaming, kaynak gösterimi |

---

## Dosya Yerleşim İlkeleri

- **Kök:** giriş noktaları — `config.py`, `requirements.txt`, `MEMORY.md`
- **`api/`** — FastAPI app + route'lar (`chat.py`, `health.py`)
- **`frontend/`** — Vue 3 SPA (`src/`), Vite build (`dist/`), `src/utils/parseSSE.js`
- **`ingestion/`** — `client.py`, `parser.py`, `chunker.py`, `embedder.py`, `store.py`,
  `pipeline.py`, `file_loader.py` (HTML strip + PDF), `scheduler.py` (APScheduler)
- **`rag/`** — `embeddings.py`, `retriever.py`, `chain.py`, `query_processor.py`, `history.py`
- **`tests/`** — pytest, modül yapısını yansıtır
- **`scripts/`** — CLI (`ingest.py`)
- **`chroma_db/`** — ChromaDB verisi, `.gitignore`'da

---

## Ortam Değişkenleri (.env)

```env
# Vector store provider: "chroma" veya "pinecone"
VECTOR_STORE_PROVIDER=chroma
# Embedding provider: "ollama" veya "gemini"
EMBED_PROVIDER=ollama
GEMINI_EMBED_MODEL=gemini-embedding-001

# Pinecone (serverless) — VECTOR_STORE_PROVIDER=pinecone ile aktif
PINECONE_API_KEY=xxx
PINECONE_INDEX=reliefweb-docs
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
PINECONE_NAMESPACE=

# Chat LLM provider: "gemini" veya "ollama"
CHAT_LLM_PROVIDER=gemini

# Google Gemini (chat — OpenAI uyumlu endpoint)
GEMINI_API_KEY=xxx
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_LLM_MODEL=gemini-2.5-flash

# Ollama Cloud/Local (query processor LLM) — şu an yerele işaret ediyor
OLLAMA_CLOUD_API_KEY=ollama
OLLAMA_CLOUD_BASE_URL=http://localhost:11434/v1
OLLAMA_LLM_MODEL=qwen2.5:0.5b

# Ollama Local (embedding)
OLLAMA_LOCAL_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=qwen3-embedding:8b

# ReliefWeb
RELIEFWEB_APPNAME=xxx           # URL param: ?appname=...  (Bearer auth YOK)
RELIEFWEB_BASE_URL=https://api.reliefweb.int/v2

# ChromaDB / Embedding
CHROMA_DB_PATH=./chroma_db
CHROMA_COLLECTION=reliefweb_docs
EMBED_DIM=4096                  # provider'a bağlı: ollama qwen3-embedding:8b → 4096, gemini gemini-embedding-001 → 3072
EMBED_BATCH_SIZE=32

# RAG retrieval
CHUNK_SIZE=800
CHUNK_OVERLAP=100
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
- `scheduler.py` — APScheduler + watermark (`chroma_db/.last_ingest.json`) ile incremental

---

## RAG Pipeline

**Query processor** (`rag/query_processor.py`): LLM-first filtre çıkarma (`json_mode` +
`QueryFilters` Pydantic) → başarısızsa rule-based fallback (`_COUNTRY_MAP`/`_THEME_MAP`/
`_DOCTYPE_MAP` + regex). dict-based cache (512 giriş, `None` cache'lenmez), LLM timeout 5s.
"şu anda / güncel / latest" gibi belirsiz ifadeler date filtresi ÜRETMEZ; `date_from`
bugün/gelecek ise reddedilir.

**Retriever** (`rag/retriever.py`): ChromaDB MMR (`k=TOP_K_RETRIEVAL`, `fetch_k=MMR_FETCH_K`,
`lambda_mult=MMR_LAMBDA`). `_build_chroma_filter` → `$and`/`$eq`; country `$in` (kısa+tam ad).
**Tarih filtresi ChromaDB'de DEĞİL** — `apply_date_filter` ile Python'da post-retrieval
(ChromaDB string `$gte` desteklemez). `rerank_by_recency` → MMR + üstel recency blend.

**Chain** (`rag/chain.py`): düz LCEL `prompt | llm | StrOutputParser`. Provider'a göre
Gemini veya Ollama `ChatOpenAI`. History route'da `get_session_history` ile alınır,
`chat_history` olarak geçilir, yanıt sonrası kaydedilir (RunnableWithMessageHistory YOK).

**ChromaDB metadata şeması (her chunk):**
```python
{"doc_id", "url", "title", "country", "theme", "date" (YYYY-MM-DD),
 "source", "format", "doctype"}  # doc_id orphan cleanup için kullanılır
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
2. **`chroma_db/`** `.gitignore`'da — vektör verisi repoya girmesin.
3. **Ingestion idempotent**: kanonik URL `doc_id` + upsert öncesi orphan temizliği.
4. **Rate limiting**: ReliefWeb 429/5xx → backoff; 4xx → retry yok; Ollama → retry x3.
5. **Loglama**: her modülde `logger = logging.getLogger(__name__)`.
6. **Testler**: `tests/` altında pytest; değişiklikten sonra `python -m pytest tests/ -q`.

---

## Bilinen Kısıtlamalar

- Embedding yerel çalışır — ingestion sırasında `ollama serve` ayakta olmalı; yavaştır.
- `qwen3-embedding:8b` ~4.7GB RAM; yetersizse `qwen3-embedding:4b` (2560 dim, `EMBED_DIM` güncelle).
- Görseller/infografikler doğrudan sorgulanamaz; başlık + açıklama metadata'sı index'lenir.
- Session history varsayılan in-memory (restart'ta silinir); `REDIS_URL` ile kalıcı yapılabilir.
- Query processor modeli küçük (`qwen2.5:0.5b`) — filtre kalitesi sınırlı, rule-based fallback var.
- Pipeline resume kısmi (watermark var, uzun kesinti tam test edilmedi).
- CORS şu an localhost origin'leri — production'da `CORS_ORIGINS` daraltılmalı.
- PDF içerik ingestion opsiyonel (`FETCH_PDF_CONTENT=False`); varsayılan sadece HTML `body`.
- Pinecone serverless metadata-filtreli silme desteklemez; orphan temizliği chunk-id prefix (`{doc_id}_`) list+delete ile yapılır.
- Gemini embedding OpenAI-uyumlu endpoint üzerinden çalışır; `task_type` (`RETRIEVAL_DOCUMENT`/`QUERY`) ayrımı yok (küçük kalite ödünü).
