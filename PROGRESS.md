# ReliefWeb RAG — Proje İlerleme Durumu

## Son Güncelleme: 2026-05-12

---

## Tamamlanan İşler

### 1. Mimari ve Altyapı
- `config.py` — Pydantic `BaseSettings` ile tüm ortam değişkenleri yönetimi
- `.env.example` — Şablon dosyası tamamlandı (senkronize: `qwen3-embedding:8b`, `EMBED_DIM=2560`)
- `.gitignore` — Python, ChromaDB, IDE kuralları aktif
- `requirements.txt` — LangChain, ChromaDB, Ollama, FastAPI, pytest

### 2. Ingestion Pipeline (`ingestion/`) — Çoklu Endpoint Desteği
- `client.py` — `ENDPOINT_CONFIG` ile 3 endpoint tanımı (reports, disasters, countries); generic `fetch()` metodu; `fetch_reports()` backward-compatible wrapper; 429 exponential backoff; pagination; `date_from` parametresi ile ReliefWeb API tarih filtresi
- `parser.py` — `parse_report()`, `parse_disaster()`, `parse_country()` endpoint'e özel parser'lar; `parse()` dispatcher fonksiyonu; tüm parser'lar `doctype` alanı üretir; `_normalize_date()` ile tarih normalizasyonu (ISO 8601 → YYYY-MM-DD)
- `chunker.py` — Body chunking (CHUNK_SIZE=800, CHUNK_OVERLAP=100), metadata + `doctype` propagation
- `embedder.py` — Yerel Ollama embedding (`qwen3-embedding:8b`), retry x3
- `store.py` — ChromaDB idempotent upsert, `sha256(url)` bazlı doc_id, `clear_collection()` desteği
- `pipeline.py` — Multi-endpoint orchestrator: `endpoints` parametresi ile reports + disasters + countries sırayla işlenir; `BATCH_SIZE=500` API batch boyutu; per-batch ilerleme loglaması (docs/sec, ETA); sayaç tutarsızlığı düzeltmesi; `date_from` parametresi ile incremental ingestion desteği; varsayılan limit 1000
- `scripts/ingest.py` — CLI: `--limit` (default 1000), `--force`, `--endpoints`, `--date-from` (incremental ingestion); `sys.path` düzeltmesi eklendi

### 3. RAG Engine (`rag/`)
- `embeddings.py` — LangChain `Embeddings` wrapper (Ollama local)
- `query_processor.py` — **LLM-first** filter extractor (json_mode) + rule-based fallback; ülke, tema, tarih, doctype, kaynak, format; İngilizce + Türkçe tarih pattern'leri (son hafta, geçen ay, since YYYY-MM-DD, yesterday/dün, today/bugün, this week/bu hafta, this month/bu ay, recent/güncel/son dönem); dict-based cache (None sonuçları cache'lenmiyor); LLM timeout 15s; `analyze_query()` ile belirsiz sorgu tespiti ve clarification önerileri
- `retriever.py` — ChromaDB MMR retriever + metadata filtering, `@lru_cache(maxsize=1)` singleton; `rerank_by_recency()` ile tarih bazlı yeniden sıralama (blended score: MMR relevance + recency weighting)
- `history.py` — `WindowedChatMessageHistory(k=5)` session-based memory + `InMemoryChatMessageHistory`
- `chain.py` — LCEL zinciri: `ChatPromptTemplate | ChatOpenAI | StrOutputParser` + `RunnableWithMessageHistory`; `streaming=True`

### 4. ~~Chainlit UI~~ (Kaldırıldı)
- `chainlit_app.py`, `.chainlit/`, `chainlit.md` silindi ve git'ten kaldırıldı
- Yerine FastAPI + Vue 3 frontend kullanılıyor

### 5. Testler (`tests/`)
- `test_ingestion_client.py` — API client mock testleri + `fetch()` generic metod testleri + ENDPOINT_CONFIG doğrulama
- `test_ingestion_parser.py` — `parse_report`, `parse_disaster`, `parse_country`, `parse()` dispatcher testleri; `_normalize_date()` testleri (ISO 8601, timezone, empty, short date)
- `test_ingestion_chunker.py` — Chunking + metadata + `doctype` koruma testleri
- `test_ingestion_embedder.py` — Embedding retry mock testleri
- `test_ingestion_store.py` — ChromaDB upsert + clear_collection mock testleri
- `test_ingestion_pipeline.py` — Pipeline orchestrator (limit, force, multi-endpoint) mock testleri
- `test_rag_embeddings.py` — LangChain wrapper testleri
- `test_rag_query_processor.py` — Filter extraction (country, theme, date, doctype) + LLM mock testleri + rule-based fallback + 16 yeni tarih pattern testi (son hafta, since, yesterday, today, this week, this month, recent vb.) + LLM cache davranış testleri (failure not cached, success cached)
- `test_rag_analyze_and_rerank.py` — `analyze_query()` belirsizlik tespiti testleri + `rerank_by_recency()` tarih bazlı yeniden sıralama testleri
- `test_rag_retriever.py` — Retriever + Chroma cache testleri
- `test_rag_history.py` — Windowed history, session store, populate from messages testleri
- `test_rag_chain.py` — LCEL chain + singleton + streaming testleri
- `test_config.py` — Settings cache + env override testleri
- `test_api_chat_stream.py` — SSE endpoint + session_id integration testleri

**Toplam: 16 test dosyası, 69 test PASSED (parser + query processor + analyze/rerank)

### 6. FastAPI Backend (`api/`)
- `api/main.py` — FastAPI uygulaması, CORS middleware (`allow_origins=["*"]`), health ve chat router'ları, frontend `dist/` statik mount
- `api/routes/health.py` — `GET /health` endpoint'i
- `api/routes/chat.py` — `POST /chat` (non-streaming, session_id + ayrık retrieval) + `POST /chat/stream` (SSE, token-by-token, sources + session_id + clarification event); `rerank_by_recency()` ile güncellik önceliklendirmesi; `analyze_query()` ile belirsiz sorgu tespiti; clarification SSE event

### 7. Vue 3 Frontend (`frontend/`)
- `frontend/package.json` — Vue 3.4 + Vite 5
- `frontend/src/App.vue` — Ana sayfa, `Chat` bileşeni mount'u; İngilizce subtitle; gradient header; DM Sans font
- `frontend/src/components/Chat.vue` — Chat UI, SSE streaming (`fetch + ReadableStream`), `v-html` ile formatMessage render; error state handling (4 hata tipi); İngilizce UI; typing indicator tek baloncukta; yuvarlak köşeler ve gölge tasarımı; clarification kartı (ülke/tarih/tema öneri chip'leri, otomatik gönder)
- `frontend/src/components/SourceList.vue` — Kaynak listesi bileşeni; İngilizce "Sources" başlık; card-style render; `formatDate()` ile okunabilir tarih; `isValidSource()` ile country belgeleri filtreleme
- `frontend/src/utils/formatMessage.js` — LLM çıktısını güvenli HTML'e çevirir (bold, italic, list, paragraph); XSS koruması (HTML escape)
- `frontend/src/style.css` — CSS custom properties: renkler, border-radius, shadow değişkenleri; DM Sans font ailesi
- `frontend/dist/` — Build edilmiş production bundle

### 11. LCEL Migration (2026-05-07 - Oturum 3)
- **`rag/chain.py`** — ConversationalRetrievalChain → LCEL (`ChatPromptTemplate | ChatOpenAI | StrOutputParser` + `RunnableWithMessageHistory`); singleton pattern; `streaming=True`
- **`rag/history.py`** — Yeni: `WindowedChatMessageHistory(k=5)` session-based memory; `get_session_history()`, `clear_session()`, `populate_history_from_messages()`
- **`rag/memory.py`** — Silindi (deprecated ConversationBufferWindowMemory kaldırıldı)
- **`api/routes/chat.py`** — `POST /chat`: ayrık retrieval + session_id; `POST /chat/stream`: SSE endpoint (`EventSourceResponse`)
- **`rag/__init__.py`** — Export'lar güncellendi (build_memory → get_session_history, clear_session, populate_history_from_messages)
- **`config.py`** — Chainlit ayarları kaldırıldı (CHAINLIT_AUTH_SECRET, CHAINLIT_USERS)
- **`requirements.txt`** — chainlit kaldırıldı; sse-starlette eklendi; dependency conflict çözüldü

### 12. LLM Query Processor (2026-05-07 - Oturum 3)
- **`rag/query_processor.py`** — LLM-first filter extraction (`ChatOpenAI.with_structured_output(json_mode)` + `QueryFilters` Pydantic modeli)
- Rule-based fallback korunuyor (`_extract_filters_rule_based`); İngilizce tarih pattern'leri eklendi
- `_normalize_llm_filters()` — LLM çıktısını canonical değerlerle doğrulama
- `@lru_cache(maxsize=256)` ile tekrarlanan sorgular cache'leniyor
- "irak" → "Iraq" mapping eklendi (Türkçe/İngilizce normalize farkı)
- `request_timeout=5` ile LLM timeout limiti

### 13. Streaming SSE (2026-05-07 - Oturum 3)
- **`api/routes/chat.py`** — `POST /chat/stream`: SSE endpoint; token event, sources event, session event, done event
- **`frontend/src/components/Chat.vue`** — `fetch + ReadableStream` ile SSE parse; `streaming` ref; connection drop handling; session_id desteği
- `.env` → `EMBED_DIM=2560` olarak düzeltildi (önceden yanlışlıkla 4096 yazılıydı)
- `.env.example` → `OLLAMA_EMBED_MODEL=qwen3-embedding:8b` ve `EMBED_DIM=2560` senkronize
- Chainlit dosyaları (`chainlit_app.py`, `.chainlit/`, `chainlit.md`, `tests/test_chainlit_app.py`) git'ten kaldırıldı
- Orphan `__pycache__/chainlit_app.cpython-312.pyc` temizlendi

### 14. Pipeline Error Handling (2026-05-08 - Oturum 4)
- **`pipeline.py`** — `IngestionStats` dataclass (endpoint, total, succeeded, failed, skipped, errors); per-document try/except isolation; `run_pipeline` artık `Dict[str, IngestionStats]` döndürüyor; `BATCH_SIZE=500` (önceden 100); per-batch ilerleme loglaması (işlenen/hedef, docs/sec, ETA dakika); sayaç tutarsızlığı düzeltmesi (`processed` counter)
- **`parser.py`** — `parse()` fonksiyonu artık `Optional[Dict]` döndürüyor; `_sanitize()`, `_safe_get()`, `_safe_list_get()` helper'ları ile None değer koruması; parse hatası → `logger.warning` + `None` dönüşü
- **`store.py`** — `clear_collection` sessiz `except: pass` → `logger.warning` ile hata loglama
- **`scripts/ingest.py`** — `_print_summary()` tablo formatında özet raporu; exit codes: 0 (tümü başarılı), 1 (kısmi başarısız), 2 (tümü başarısız)
- **`ingestion/__init__.py`** — `IngestionStats` export'a eklendi
- **Testler** → 12 yeni test eklendi (toplam 83 test PASSED)
- **`scripts/ingest.py`** — `sys.path.insert(0, ...)` ile modül import düzeltmesi

### 9. Çoklu Endpoint Ingestion (2026-05-07 - Oturum 2)
- **API keşfi:** `/updates` endpoint'i ReliefWeb API'sinde yok (404) — `/reports` zaten güncellemeleri içeriyor
- **`client.py`** → `ENDPOINT_CONFIG` dict ile reports, disasters, countries tanımlandı; generic `fetch(endpoint)` metodu eklendi
- **`parser.py`** → `parse_disaster()` (name→title, description→body, primary_type.name→theme, status→format), `parse_country()` (name→title+country, description→body), `parse()` dispatcher eklendi
- **`chunker.py`** → `doctype` metadata alanı eklendi
- **`pipeline.py`** → `endpoints` parametresi eklendi (varsayılan `["reports"]`)
- **`scripts/ingest.py`** → `--endpoints` CLI argümanı eklendi
- **`query_processor.py`** → `_DOCTYPE_MAP` ile doctype filtre çıkarma (rapor/afet/ülke/report/disaster/country)
- **`ingestion/__init__.py`** → Yeni export'lar eklendi
- **Testler** → 9 yeni test eklendi (toplam 57 test PASSED)

### 10. Canlı Ingestion (2026-05-07)
Komut: `python scripts/ingest.py --limit 500 --endpoints reports disasters countries --force`

| Endpoint | Doküman | Chunk | Süre |
|----------|---------|-------|------|
| Reports | 500 | 584 | ~65 dk |
| Disasters | 500 | 622 | ~70 dk |
| Countries | 160 | 160 | ~11 dk |
| **Toplam** | **1,160** | **1,366** | **~146 dk** |

- Sıralama: `date.created:desc` — en güncel veriler önce
- Countries'ta 249 ülkenin 160'ında description mevcut — sadece bunlar yüklendi
- Disaster type'lar (Flood, Earthquake vb.) `theme` metadata alanına map edildi
- Country kayıtlarında `country` = `name` (self-referencing)

### 15. Büyük Ölçekli Ingestion (2026-05-08 - Oturum 5)
- **`pipeline.py`** — API batch boyutu 100'den 500'e çıkarıldı (`BATCH_SIZE = 500`); per-batch ilerleme loglaması eklendi (işlenen/hedef, başarılı/hata/skip, docs/sec, ETA dakika); sayaç tutarsızlığı düzeltildi (`processed` counter)
- **`scripts/ingest.py`** — `sys.path` import düzeltmesi eklendi
- **`tests/test_ingestion_pipeline.py`** — `BATCH_SIZE` sabiti testi ve multi-batch davranış testi eklendi (toplam 85 test PASSED)

**Canlı ingestion sonuçları:**

| Endpoint | İşlenen | Başarılı | Atlandı | Başarısız | Süre |
|----------|---------|----------|---------|-----------|------|
| Countries | 249 | 160 | 89 | 0 | ~12 dk |
| Disasters | 3,705 | 2,279 | 1,426 | 0 | ~3.5 saat |
| Reports | 7,500 | 5,712 | 1,788 | 0 | ~10 saat (durduruldu) |
| **Toplam** | **11,454** | **8,151** | **3,303** | **0** | — |

- ChromaDB toplam: **9,597 chunk** (tüm endpoint'ler dahil)
- Reports ingestion ~7,500/10,000 belgede durduruldu, kalan 2,500 için resume mekanizması henüz yok

### 17. Tarih Filtreleme ve Veri Kalitesi Düzeltmeleri (2026-05-09 - Oturum 7)

**Sorun:** Kullanıcı "Iran'da son 1 haftadaki gelişmeler" ve "Iran'da 28 şubattan itibaren insani yardım durumu" gibi sorgularda sonuç alamıyordu.

**Kök nedenler:**
1. ReliefWeb API'den gelen tarihler karışık formatlarda (`"2021-09-06T00:00:00+00:00"`, `"2026-04-01"`, `""`) — ChromaDB `$gte` lexicographic karşılaştırması yanlış sonuçlar veriyordu
2. Rule-based tarih pattern'leri eksikti — sadece `son N ay/hafta/gün` (sayılı) tanınıyordu; "son hafta", "since YYYY-MM-DD", "yesterday", "bugün" vb. tanınmıyordu
3. LLM başarısızlığı `@lru_cache` ile kalıcı olarak cache'leniyordu — bir kez timeout olursa aynı sorgu sonsuza kadar rule-based fallback'e düşüyordu
4. LLM timeout 5 saniyeydi (397B parametreli model için yetersiz)

**Değişiklikler:**
- **`ingestion/parser.py`** — `_normalize_date()` fonksiyonu eklendi; tüm tarihler `YYYY-MM-DD` formatına normalize ediliyor; 3 parser call site'ı güncellendi
- **`rag/query_processor.py`** — 15 yeni tarih pattern'i eklendi (Türkçe + İngilizce); `@lru_cache` kaldırılıp dict-based cache ile değiştirildi (None sonuçları cache'lenmiyor); LLM timeout 5s → 15s; `@lru_cache(maxsize=1)` dekoratörü kaldırılıp modül-level `_llm_extractor` variable ile değiştirildi
- **`ingestion/client.py`** — `fetch()` metoduna `date_from` parametresi eklendi; ReliefWeb API filter parametresi olarak gönderiliyor
- **`ingestion/pipeline.py`** — `run_pipeline()` fonksiyonuna `date_from` parametresi eklendi; varsayılan limit 1000'e çıkarıldı
- **`scripts/ingest.py`** — `--date-from` CLI argument eklendi; varsayılan limit 1000'e çıkarıldı
- **Testler** — 6 yeni `_normalize_date` testi, 16 yeni tarih pattern testi, 2 yeni LLM cache testi eklendi (toplam 57 test PASSED sadece bu iki dosyada)

**Sonraki adım:** ChromaDB'yi `python scripts/ingest.py --limit 1000 --force --endpoints reports disasters countries` ile yeniden ingest etmek gerekiyor — tarihlerin normalize edilmiş formatla kaydedilmesini sağlayacak.

### 18. Date-aware Re-ranking + Interactive Query Refinement (2026-05-12 - Oturum 8)

**Sorun:** "En güncel insani yardım" sorgusunda eski belgeler (2023 deprem, 2025 Yemen) geliyordu. MMR retriever güncelliği önceliklendirmiyordu ve belirsiz sorgularda kullanıcıya rehberlik yoktu.

**Değişiklikler:**
- **`rag/retriever.py`** — `rerank_by_recency()` fonksiyonu eklendi. MMR relevance + recency blended skor: `(1-decay)*mmr_score + decay*recency_score`. Recency: gün bazlı (365 gün normalizasyonu). Tarih yoksa recency_score=0.
- **`rag/query_processor.py`** — `analyze_query()` fonksiyonu eklendi. Sorgunun belirsizliğini tespit eder (country/date/theme eksik), clarification önerileri sunar (ülke listesi, zaman periyotları, temalar).
- **`api/routes/chat.py`** — Her iki endpoint'te retrieval sonrası `rerank_by_recency()` çağrısı eklendi. Belirsiz sorgularda `clarification` SSE event'i gönderiliyor (ülke/tarih/tema önerileri).
- **`rag/chain.py`** — System prompt'a 7. kural eklendi: belirsiz sorgularda eksik bilgileri ve kullanıcıya sunulan detayları belirtme.
- **`config.py`** — `RERANK_BY_DATE: bool = True` ve `DATE_DECAY_FACTOR: float = 0.3` ayarları eklendi.
- **`frontend/src/components/Chat.vue`** — `clarification` SSE event handler eklendi. Clarification kartı: ülke/tarih/tema öneri chip'leri. `applySuggestion()`: chip'e tıklayınca orijinal sorgu + chip değeri otomatik gönderilir. CSS: clarification-card, suggestion-chip stilleri.
- **Testler** — 12 yeni test (`test_rag_analyze_and_rerank.py`): `analyze_query()` belirsizlik tespiti testleri + `rerank_by_recency()` re-ranking testleri.

### 19. Proje Temizliği (2026-05-12 - Oturum 8)

**Silinen dosyalar/klasörler:**
- 7 `__pycache__/` dizini (kök, api, api/routes, ingestion, rag, scripts, tests)
- 2 `.pytest_cache/` dizini (kök, frontend)
- `frontend/chroma_db/` — yanlış yerdeki ChromaDB verisi
- `.superpowers/` — brainstorm artifacts

**Güncellenen dosyalar:**
- `.env` — Chainlit satırları silindi (`CHAINLIT_AUTH_SECRET`, `CHAINLIT_USERS`); `OLLAMA_CLOUD_BASE_URL`, `RERANK_BY_DATE`, `DATE_DECAY_FACTOR` eklendi
- `.env.example` — Chainlit satırları silindi; yeni config değişkenleri eklendi
- `README.md` — Chainlit referansları kaldırıldı; FastAPI + Vue 3 mimarisi güncellendi; çalıştırma talimatları düzeltildi; dizin yapısı güncellendi
- `.gitignore` — `.superpowers/` eklendi

### 16. Frontend İyileştirmesi (2026-05-08 - Oturum 6)
- **`frontend/src/utils/formatMessage.js`** — Yeni: LLM çıktısını güvenli HTML'e çevirir; HTML escape → bold (`**`→`<strong>`) → italic (`*`→`<em>`) → list (`- item`→`<ul><li>`) → paragraph (`\n\n`→`</p><p>`); XSS koruması
- **`frontend/src/components/Chat.vue`** — `v-html` ile formatMessage render; 4 hata tipi (connection, stream_interrupted, empty_response, sse_parse) + `ERROR_MESSAGES` dict; error banner inline gösterim; İngilizce UI (placeholder, button); typing indicator tek baloncukta; yuvarlak köşeler (`--radius-lg`, `--radius-md`); box-shadow; focus glow; DM Sans font
- **`frontend/src/components/SourceList.vue`** — İngilizce "Sources" başlık; card-style render (background, border, shadow, hover); `formatDate()` ile ISO→okunabilir tarih ("3 Apr 2026"); `isValidSource()` ile country belgeleri filtreleme (doctype=country ve title=country olanlar gizleniyor); `computed` ile filtrelenmiş kaynak listesi
- **`frontend/src/App.vue`** — İngilizce subtitle ("Intelligent assistant on humanitarian aid documents"); gradient header; kompakt padding; subtitle opacity
- **`frontend/src/style.css`** — 7 yeni CSS variable: `--color-error-bg`, `--color-error-accent`, `--color-success`, `--radius-sm/md/lg`, `--shadow-sm/md`; DM Sans font ailesi (`--font-display`, `--font-body`)
- **`frontend/index.html`** — `lang="en"`; DM Sans Google Fonts import
- **`rag/chain.py`** — System prompt güncellendi: selamlaşmalarda kaynak gösterme zorunluluğu kaldırıldı; 6 kural maddesine yeniden yapılandırıldı
- **`api/routes/chat.py`** — `_is_greeting()` regex ile selamlaşma tespiti (merhaba, selam, hi, hello, hey, günaydın, nasılsın vb.); selamlaşmalarda retrieval atlanıyor → boş context, boş sources; `doctype` alanı SourceDocument model'ına ve SSE sources event'ine eklendi; URL'siz/başlıksız kaynaklar filtreleniyor

---

## Bilinen Riskler / Gözlem Listesi

| # | Konu | Etki | Plan |
|---|------|------|------|
| 1 | ~~`ChatOllama` cloud API key desteği~~ | ~~LLM bağlantısı kopabilir~~ | **ÇÖZÜLDÜ** — `ChatOpenAI`'ye geçildi |
| 2 | ~~`build_retriever` her çağrıda yeni Chroma instance~~ | ~~Performans etkisi~~ | **ÇÖZÜLDÜ** — `@lru_cache(maxsize=1)` |
| 3 | ~~`build_chain` her mesajda yeni memory~~ | ~~Konuşma geçmişi kaybolabilir~~ | **ÇÖZÜLDÜ** — FastAPI'de history client'tan geliyor |
| 4 | ~~Query processor rule-based~~ | ~~Karmaşık sorguları kaçırabilir~~ | **ÇÖZÜLDÜ** — LLM-first extraction + rule-based fallback |
| 5 | ~~Tarih filtresi `$gte` ChromaDB syntax~~ | ~~Metadata date string karşılaştırması güvenilirliği~~ | **ÇÖZÜLDÜ** — `_normalize_date()` ile YYYY-MM-DD format garantisi |
| 6 | ~~Embedding model adı tutarsızlığı~~ | ~~Belirsizlik~~ | **ÇÖZÜLDÜ** — tüm dosyalar `8b` / `2560` olarak senkronize |
| 7 | ~~`force` parametresi no-op~~ | ~~Kullanıcı beklentisini karşılamaz~~ | **ÇÖZÜLDÜ** — `ChromaStore.clear_collection()` eklendi |
| 9 | ~~`ConversationalRetrievalChain` deprecated~~ | ~~Gelecek LangChain versiyonlarında kırılabilir~~ | **ÇÖZÜLDÜ** — LCEL `RunnableWithMessageHistory` + singleton pattern |
| 10 | CORS `allow_origins=["*"]` | Production'da güvenlik riski | Spesifik origin'ler belirlenmeli |
| 11 | ~~Streaming response yok~~ | ~~Uzun LLM yanıtlarında UX kötü~~ | **ÇÖZÜLDÜ** — SSE `/chat/stream` + Vue streaming |
| 12 | ~~ReliefWeb sadece `/reports` endpoint'i~~ | ~~Zengin içerik kaçırılıyor~~ | **ÇÖZÜLDÜ** — `/disasters` + `/countries` eklendi |
| 13 | ~~Session tabanlı memory yok (FastAPI)~~ | ~~Her istekte yeni memory~~ | **ÇÖZÜLDÜ** — `WindowedChatMessageHistory` + session_id |
| 14 | ~~`v-html` XSS riski~~ | ~~LLM injection ile XSS~~ | **ÇÖZÜLDÜ** — formatMessage ile HTML escape + v-html |
| 15 | `/updates` endpoint'i yok | ReliefWeb API'de 404 | N/A — `/reports` zaten güncellemeleri içeriyor |
| 16 | Disaster `type` → `theme` mapping | Semantik olarak farklı (afet türü vs. sektör) | Gelecekte `disaster_type` metadata alanı eklenebilir |
| 17 | Pipeline resume mekanizması yok | Kesinti sonrası sıfırdan başlar | `--offset` veya ChromaDB dedup ile çözülebilir |
| 18 | ~~Eski belgeler güncel belgelerle karışıyor~~ | ~~MMR çeşitlilik öncelikli, güncellik değil~~ | **ÇÖZÜLDÜ** — `rerank_by_recency()` ile blended skor |
| 19 | ~~Belirsiz sorgularda rehberlik yok~~ | ~~Kullanıcı sonuç alamıyor~~ | **ÇÖZÜLDÜ** — `analyze_query()` + clarification SSE event + chip UI |

---

## Bekleyen İşler (Sıradaki Adımlar)

### Yüksek Öncelik
- [x] ~~LangGraph / LCEL migration~~ — ConversationalRetrievalChain → LCEL RunnableWithMessageHistory
- [x] ~~LLM tabanlı query processor~~ — ChatOpenAI json_mode + QueryFilters Pydantic modeli
- [x] ~~Tarih filtreleme düzeltmesi~~ — Date normalization, yeni pattern'ler, cache fix, timeout artışı
- [x] ~~Date-aware re-ranking~~ — `rerank_by_recency()` ile güncellik önceliklendirmesi
- [x] ~~Interactive query refinement~~ — Belirsiz sorgularda clarification UI (ülke/tarih/tema chip'leri)

### Orta Öncelik
- [x] ~~Streaming response~~ — SSE `/chat/stream` endpoint + Vue frontend
- [x] ~~Session tabanlı memory~~ — WindowedChatMessageHistory + session_id
- [ ] CORS origin kısıtlaması: production için spesifik origin'ler
- [x] Pipeline error handling: per-report hata takibi ve log — IngestionStats dataclass, try/except isolation, CLI summary table, exit codes
- [ ] Daha fazla veri çekme: reports kalan ~2,500 belge (resume mekanizması gerekli)
- [x] ~~Re-ingestion: `--force` ile ChromaDB tarih normalizasyonu~~ — kod hazır, akşam çalıştırılacak

### Düşük Öncelik
- [x] ~~Frontend: Markdown render~~ — formatMessage utility (bold, italic, list, paragraph)
- [x] ~~Frontend: hata state'leri~~ — 4 hata tipi + error banner + console.error
- [x] ~~Frontend: kaynak gösterimi~~ — card-style, tarih formatı, country filtreleme, greeting'de kaynak yok
- [x] ~~Frontend: İngilizce UI~~ — tüm metinler İngilizce
- [x] ~~Frontend: görsel iyileştirme~~ — DM Sans font, yuvarlak köşeler, gölge, gradient header
- [ ] Frontend: mobil iyileştirme (responsive design)
- [ ] Frontend test'leri (Vitest + Vue Test Utils)
- [ ] CI/CD pipeline (GitHub Actions)

---

## Commit Geçmişi

```
d8d4cb0 feat: implement full ReliefWeb RAG system
c5e2ce8 fix: correct retriever to use LangChain Chroma, fix chain prompt template, fix client test
73a9c8d feat: add FastAPI backend and Vue frontend scaffold; fix chain, retriever, embed_dim, force param; add tests
ef65378 fix: migrate LLM from ChatOllama to ChatOpenAI for Ollama Cloud compatibility
d0ccd03 fix: correct EMBED_DIM to 2560 for qwen3-embedding:8b
41ce6cd fix: wire force parameter in ingestion pipeline
# TODO: multi-endpoint ingestion + canlı ingestion commit'lenmeli
```

---

## Notlar
- `.env` dosyası `.gitignore`'da; canlı API anahtarları commit edilmiyor
- `chroma_db/` 8,151 doküman (9,597 chunk) içeriyor, `.gitignore`'da
  - Reports: 5,712 doküman (kısmi, 7,500/10,000 işlendi)
  - Disasters: 2,279 doküman, 2,279 chunk
  - Countries: 160 doküman, 160 chunk
- Test coverage: 16 test dosyası, 69 test PASSED (core modules)
- `__pycache__/`, `.pytest_cache/`, `.superpowers/`, `frontend/chroma_db/` silindi (temizlik)
- `.env` ve `.env.example` Chainlit satırları kaldırıldı; RERANK_BY_DATE, DATE_DECAY_FACTOR eklendi
- README.md FastAPI + Vue 3 mimarisine güncellendi
- Frontend: DM Sans font ailesi, İngilizce UI, formatMessage (bold/italic/list), error states, greeting detection
- Kaynak gösterimi: ISO tarih → okunabilir format, country belgeleri filtreli, greeting'te kaynak yok
- Chainlit bağımlılığı kaldırıldı; FastAPI + Vue 3 mimarisine geçildi
- Tarih metadata'ları artık `_normalize_date()` ile YYYY-MM-DD formatında normalize ediliyor (eski veriler re-ingestion gerektiriyor)
- Query processor artık 15+ yeni tarih pattern'ini tanıyor (son hafta, since, yesterday, bugün, bu ay vb.)
- LLM extraction başarısızlığı artık cache'lenmiyor (eski `@lru_cache` → dict-based cache)
- LLM timeout 5s'den 15s'ye çıkarıldı
- Vue frontend `dist/` build edilmiş ve FastAPI tarafından statik olarak sunuluyor
- `/updates` endpoint'i ReliefWeb API'sinde mevcut değil — `/reports` zaten güncellemeleri kapsıyor
- ChromaDB metadata şemasına `doctype` alanı eklendi ("report", "disaster", "country")