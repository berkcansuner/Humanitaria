# MEMORY — ReliefWeb RAG (oturum sürekliliği)

> **Her oturum başında bu dosyayı oku. Her önemli ilerlemeden sonra güncelle.**
> Bu bir tarihçe değil — GÜNCEL durumu yansıtır. Eskiyen satırları sil/değiştir.
> "Nerede kalmıştık?" sorusunun cevabı burasıdır.

**Son güncelleme:** 2026-06-24

---

## ✅ Bu seansta UYGULANAN — Canlı test + 8 iş kolu geliştirme (2026-06-24, COMMIT BEKLİYOR)

Kullanıcı "canlı test et → geliştir" dedi. **Canlı test P0 buldu:** chat modeli `gemini-3.5-flash`
kronik **503 "high demand"** → uygulama hiçbir RAG sorusuna cevap veremiyordu (embedding/Pinecone/
query-proc sağlıklıydı; tek kırılma chat modeliydi; MEMORY'de 17 gün önce de aynı 503). Plan onaylandı
(4 alan), 8 iş kolu uygulandı (hepsi test + canlı doğrulandı):

- **İK1 Güvenilirlik (P0):** chat modeli → **`gemini-2.5-flash`** (config.py + .env + tüm docs;
  reasoning_effort=low 2.5-flash'te çalışıyor). Non-stream `/chat`'e `_ainvoke_with_retry` (transient
  503 retry) + `_is_high_demand` helper (stream+non-stream paylaşır). Geniş `except→503` daraltıldı:
  busy→503 net mesaj, beklenmeyen→`logger.exception`+**500**. **Canlı: EN+TR chat 200 + 5 kaynak.**
- **İK2 Güvenlik:** auth signup/login **rate-limit** (yeni paylaşılan `api/limiter.py` — chat↔auth
  circular import'tan kaçınmak için; `AUTH_LOGIN_RATE_LIMIT=5/min`, `AUTH_SIGNUP_RATE_LIMIT=3/min`).
  **Canlı: login #6→429.** Login **timing-attack** fix (`users.DUMMY_PASSWORD_HASH` — kullanıcı yoksa da
  bcrypt çalışır). Ölü config temizliği (.env'den CHROMA_*/OLLAMA_*/*_PROVIDER; config'ten kullanılmayan
  `API_KEY`). **+ yan-bug:** `.env` `CHUNK_SIZE=800/100` eski word-count kalıntısıydı → **1500/200** (config
  intent'i; ingest kotada bloklu, anlık etki yok ama gelecekteki ingest doğru chunk üretir).
- **İK3 RAG kalitesi:** MMR/aday-havuzu/truncate A/B (`eval_rag.py --metrics`, 15 etiketli sorgu).
  **3 varyant da baseline'dan KÖTÜ** (havuz×8+fetch40 → nDCG 0.351; fetch40 MMR-div → 0.273; truncate=START
  → recall düştü). → **KOD DEĞİŞİKLİĞİ YOK; default'lar optimal** (baseline recall@5=**0.224** MRR=**0.672**
  nDCG=**0.426**). Audit'in "büyük havuz→recall" hipotezi YANLIŞ; reranker dar/alaka-odaklı havuzla daha iyi.
  Gerçek lever hâlâ v2 namespace cutover (Pinecone kotası bloklu).
- **İK4 Test & UX:** `apply_date_filter` (testsizdi, 5 test) + `chat_stream` busy-503 testi + non-stream
  resilience testleri. **Frontend:** session-expiry **401→/login yönlendirme** (`authStore.handleSessionExpired`,
  api.js request() + Chat.vue stream); sessiz sidebar hataları → görünür banner (ChatView); a11y aria-label'ları
  (chat input, mesaj balonu role/aria, edit textarea). EmptyState i18n ATLANDI (UI bilinçli İngilizce).

**Test: 335 backend (+13) + 62 frontend (+1) yeşil. Build OK.** **HENÜZ COMMIT/PUSH YOK.**
Canlı test kullanıcısı `claude_smoke@test.local` + birkaç sohbet conversations.db'de kaldı (zararsız).

---

## 🚀 DEPLOY — Render (ücretsiz, Docker) hazırlandı (2026-06-07)
`Dockerfile` (multi-stage: Vue build → FastAPI runtime) + `render.yaml` (Blueprint, free, frankfurt, `/health`) + `DEPLOY.md` (adım adım). Tek servis API+SPA'yı aynı origin'den sunar (CORS yok). Prod env: `SESSION_COOKIE_SECURE=true`, `INGEST_SCHEDULE_HOURS=0` (scheduler kapalı; kota dolu), `GEMINI_REASONING_EFFORT=low`, URL'ler `https://reliefweb-rag.onrender.com` varsayımıyla; `AUTH_SESSION_SECRET` Render üretir; secret'lar (GEMINI/PINECONE/RELIEFWEB/GOOGLE) dashboard'da `sync:false`. **Ücretsiz tier:** disk yok → SQLite (kullanıcı/sohbet) uyku/deploy'da SIFIRLANIR + 15dk boşta uyur (ilk istek ~30-60s). Kalıcı için: paid+disk veya Postgres göçü. Google Console'a prod redirect eklenecek. Adımlar `DEPLOY.md`'de.

---

## ✅ Bu seansta UYGULANAN — Chat latency: enstrümantasyon + reasoning_effort + dayanıklılık (2026-06-07, commit bekliyor)

Kullanıcı 8000'de chat'i yavaş buldu. **Ölçüm bulgusu:** Gemini o sırada hem chat
(gemini-3.5-flash) hem query (gemini-2.5-flash) modelinde **503 "high demand"** veriyordu
(dış/geçici). Ayrıca chat LLM'de timeout/retry kontrolü yoktu → OpenAI client 503'te ~60s
iç-backoff yapıp asılıyordu.
- **Enstrümantasyon** (`api/routes/chat.py`): her yanıtta `chat latency: filter=..ms
  retrieval=..ms ttft=..ms total=..ms ns=..` INFO logu (ölç-önce-optimize-et).
- **`reasoning_effort=low`** (`config.GEMINI_REASONING_EFFORT` + `chain.py`): chat thinking
  bütçesini düşürür → TTFT azalır. Kill-switch ("" = gönderme). **Canlı DOĞRULANMADI (Gemini
  503'teydi); Gemini düzelince logdan TTFT + 400-yok kontrolü yapılmalı** (verirse kill-switch).
- **Dayanıklılık** (`chat.py _astream_with_retry` + `chain.py max_retries=0`/`timeout`):
  OpenAI client'ın ~60s iç-backoff'u kapatıldı; ilk-token ÖNCESİ kısa kontrollü retry (geçici
  503'ü atlatır), başarısızsa "model meşgul, tekrar dene" mesajı. Ölçüm: 503'te **~60s → ~19s**
  (kalan ~19s, Gemini tümden 503'te filter+embedding retry'larından; normal çalışmada tetiklenmez).
- Yeni config: `GEMINI_REASONING_EFFORT=low`, `CHAT_LLM_TIMEOUT=45`, `CHAT_LLM_MAX_RETRIES=2`.
- **Test: 322 backend** (+4 stream-retry) + 61 frontend yeşil.

---

## ✅ Bu seansta UYGULANAN — İş Kolu 2 (RAG kalite & ölçüm) + İş Kolu 3 (veri derinliği) (2026-06-07, commit `6c7a70a` → origin/master)

**İş Kolu 2A — Retrieval eval metrikleri (READ-only, kotadan etkilenmez):**
- `rag/eval_metrics.py` (YENİ, TDD): recall@k / reciprocal_rank (MRR) / nDCG@k (binary relevance).
- `scripts/build_eval_labels.py` (YENİ): default+v2'den aday havuzu + LLM relevance (TREC-tarzı pooled, silver) → `scripts/eval_data/labeled_queries.json` (15 sorgu, v2'nin 8 ülke kapsamı). Düz JSON-dizi parse + 503 retry.
- `scripts/eval_rag.py --metrics`: etiketli sette current namespace'in recall@k/MRR/nDCG'si. `PINECONE_NAMESPACE=v2` vs `''` ile A/B.
- **A/B SONUCU (k=5):** default recall@5=**0.208** MRR=**0.650** nDCG=**0.396** · v2 recall@5=**0.201** MRR=**0.622** nDCG=**0.370**. → **Doküman düzeyinde v2 ≈ default (regresyon YOK, belirgin kazanım YOK).** v2'nin değeri granülarite (küçük chunk → reranker/LLM %100 görür), doküman recall'u değil. **Cutover retrieval'ı bozmaz.** Caveat: 15 sorgu, silver label, iki-namespace havuz → kapsam gürültüsü.

**İş Kolu 2B — Konuşma-bağlamlı sorgu yeniden yazımı:**
- `rag/query_rewriter.py` (YENİ, TDD): follow-up'ı ("ya kuzeyde?") chat history ile standalone retrieval sorgusuna çevirir (gemini-2.5-flash, 5s, hata→orijinal). **Yanıt hâlâ orijinal mesajdan** üretilir; yalnız RETRIEVAL sorgusu yeniden yazılır.
- `chat.py` `_resolve_retrieval_query` (her iki route, retrieval ÖNCESİ, yalnız in-memory history varsa). `config.QUERY_REWRITE_ENABLED` kill-switch. (Faz C multi-query atlandı — A/B recall açığı göstermedi.)

**İş Kolu 3 — Veri derinliği (kod HAZIR; çalıştırma kota reset'inde):**
- `parser.py` parse_report: `iso3` (upper), `language`, `themes` (TÜM temalar; `theme`=ilk, back-compat), `glide` (linked disaster).
- `chunker.py`: bu alanları metadata'ya yazar (themes boşsa atlar — Pinecone empty-list).
- `client.py` reports fields: +`primary_country.iso3`, `language.name`, `disaster.glide`.
- `retriever._build_pinecone_filter`: tema filtresi `$or(theme $eq, themes $in)` → eski string + yeni liste kayıtları (eski namespace REGRESSİZ).
- **Reindex:** yeni script GEREKMEDİ — `ingest.py` zaten delete-before-upsert ile re-index. Kota reset'inde `PINECONE_NAMESPACE=v2 ingest.py --country PSE UKR --date-from 2023-06-05` yeni chunker+zenginleştirmeyi uygular.

**Test:** **318 backend** (yeni: eval_metrics 10, query_rewriter 5, parser/chunker/retriever enrichment 6) + 61 frontend yeşil.

---

## ✅ Bu seansta UYGULANAN — Auth (Login/Signup) sistemi (2026-06-07, commit `2198891` → origin/master)

Zorunlu giriş + e-posta/şifre **ve** Google OAuth, **httpOnly cookie** oturum. TDD ile.
Aynı zamanda **conversation IDOR açığını kapattı** (sohbetler artık kullanıcıya ait).

**Backend (yeni/değişen):**
- `rag/users.py` (YENİ) — users + sessions tabloları (aynı SQLite DB), bcrypt şifre hash, opak session token (DB'de sha256 hash'li). `get_or_create_google_user` (sub→email-link→create).
- `api/routes/auth.py` (YENİ) — `POST /auth/signup|login|logout`, `GET /auth/me`, `GET /auth/google/login|callback` (authlib). `get_current_user` dependency (cookie→user veya 401).
- `rag/conversations.py` — `user_id` kolonu + migration (`_ensure_schema` ALTER) + `is_owner()`; `create_conversation`/`list_conversations` artık `user_id` alır.
- `api/routes/{chat,conversations}.py` — gating `require_api_key` → `get_current_user` (X-API-Key KALDIRILDI); tüm conv işlemleri sahiplik-kontrollü (non-owner **404**). chat'te supplied session_id sahiplik kontrolü. Mesaj-id local'leri `user_msg_id`/`assistant_msg_id` (SSE payload anahtarları aynı: frontend uyumu).
- `api/main.py` — CORS `allow_credentials=True` + `SessionMiddleware` (authlib OAuth state).
- `config.py` — `AUTH_SESSION_SECRET`, `SESSION_COOKIE_NAME/SECURE`, `FRONTEND_URL`, `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI`. `requirements.txt` — bcrypt, authlib, itsdangerous, httpx.

**Frontend (yeni/değişen):**
- `utils/authApi.js` + `utils/authStore.js` (YENİ, reactive — Pinia yok). `views/AuthView.vue` (YENİ, login+signup tek `mode` prop'lu view, `.mkt-scope` tasarımı, Google butonu). `router/index.js` — `/login`,`/signup` + `/app` `requiresAuth` guard (`beforeEach` → `refresh()`). `MarketingNav.vue` — authed'de Open app/Log out. `api.js` + Chat.vue SSE — `credentials:'include'`.

**Test/Doğrulama:** **297 backend** (yeni: users 13, auth 10, auth_google 2 [mock], IDOR access-control 3) + **61 frontend** yeşil. Build OK. Testlerde `get_current_user` override (conftest `_auth_override` + `@pytest.mark.real_auth` opt-out). **Canlı smoke (geçici DB):** signup→HttpOnly/SameSite=lax cookie, /me 200, /conversations cookie'li 200 / cookie'siz **401**, logout→**401** (sunucu-tarafı iptal), /login SPA 200, google(yapılandırılmamış) 503.
**Google OAuth canlı DOĞRULANDI** — kullanıcı Google ile giriş yaptı (redirect→accounts.google.com→/app). Cred'ler `.env`'de (gitignored): `GOOGLE_CLIENT_ID/SECRET`, `GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback`, `FRONTEND_URL=http://localhost:8000`, güçlü `AUTH_SESSION_SECRET`. Google consent "App name" = Console ayarı (Humanitaria). **Sidebar footer artık gerçek kullanıcıyı gösterir + Log out** (hardcoded "Alex Morgan" kaldırıldı). vite.config proxy'ye `/auth`+`/conversations` eklendi.

---

## 🎯 SONRAKİ SEANS — Rollout TIKANDI (Pinecone aylık write-unit kotası doldu); v2 8/10 ülke hazır+doğrulandı

Tüm-ülke rollout başlatıldı (3 yıl, 10 ülke, ülke-başı **en yeni 2000 cap**, yeni **`v2` namespace**).
**8 ülke başarıyla v2'ye yazıldı (68.936 vektör) + 8-ülke A/B ile kalite DOĞRULANDI (GO):** granülarite
kesin kazanım (ort. chunk 479 vs default 3070 char → reranker tam görüyor), freshness 160g vs 445g, judge 5.0=5.0.
AMA son 2 ülke (**Palestine kısmi, Ukraine 0**) yazılamadı: **Pinecone AYLIK write-unit kotası (2.000.000) doldu**
(hata gövdesi: "reached your write unit limit for the current month"). Sabit kota — retry/backoff çare değil. Bkz. [[run-gotchas]].

**v2 EKSİK: 8/10 ülke.** Cutover YAPILMADI (eksik v2'ye geçersek default'taki Ukrayna+Filistin kaybolur → regresyon).
**Veri kaybı yok:** default 31.628 + pilot 4.892 + v2 68.936 sağlam, izole.

**KARAR (2026-06-06): Aylık write-unit reset'i BEKLE** (gelecek fatura döngüsü — kesin tarih için Pinecone dashboard). Bu arada app default'ta çalışıyor.

**RESUME TARİFİ (reset gelince, sırayla):**
1. `PINECONE_NAMESPACE=v2 ./venv/Scripts/python.exe scripts/ingest.py --country PSE UKR --date-from 2023-06-05 --limit 2000` → v2 = 10/10 olur (store'da artık 429-retry var; aynı 2023-06-05 penceresi = diğer 8 ülkeyle tutarlı). Önce stats al; kota gerçekten resetlendi mi diye tek-vektör test upsert ile kontrol et.
2. v2 stats doğrula (PSE/UKR 0 failed) + 10-ülke A/B (v2 vs default).
3. **CUTOVER:** `PINECONE_NAMESPACE=v2` → `config.py` default + `.env` → commit/push → app v2'ye geçer.
4. v2 sağlam çalıştığı teyit edilince → **eski default ('') namespace'i SİL** (yer açılır) + **pilot namespace'i sil** (v2 Suriye'yi kapsıyor). Silmeden önce kullanıcıya son onay.

---

## ✅ Bu seansta UYGULANAN — Suriye Re-ingest Pilotu (2026-06-05, branch `feat/reingest-pilot-syria` → master'a YEREL merge, PUSH YOK)

Plan/spec: `docs/superpowers/{plans,specs}/2026-06-02-reingest-pilot-syria*` (gitignore'da, yerel). `subagent-driven-development` ile yürütüldü.

**Commit'ler (master'a merge edildi, push EDİLMEDİ):**
- `e2c0e7d` — guardrail `INGEST_LOOKBACK_YEARS=3` + `scripts/ingest.py _resolve_date_from` + `scripts/prune_old_vectors.py` (rafta) + testler (devralınan iş checkpoint'i)
- `c23963f` — **chat LLM → `gemini-3.5-flash`** (query-processor `gemini-2.5-flash` DEĞİŞMEDİ). Canlı smoke Türkçe yanıt verdi.
- `79d61f1` — **chunker: word-count → `RecursiveCharacterTextSplitter` ~1500 char/200 overlap**; `CHUNK_SIZE=1500` (artık KARAKTER), `CHUNK_OVERLAP=200`. Metadata + `{doc_id}_{i}` id şeması korundu.
- `01f6d4d` — **PLAN-DIŞI BUG FIX:** `client.py` ReliefWeb tarih filtresi `{operator:"gte"}` (API 400 "Invalid filter operator GTE") → `{value:{from:<ISO8601>}}`. Çıplak `YYYY-MM-DD` reddediliyor → `T00:00:00+00:00` ekleniyor. **Scheduler'ın incremental ingest'ini de düzeltti** (aynı kod yolu, sessizce bozuktu). systematic-debugging ile canlı API'ye karşı kök neden kanıtlandı.
- `2139951` — final-review nit'leri (test fixture model adı, retriever bayat yorum, `INGEST_LOOKBACK_YEARS` docs).

**Pilot ingest (CANLI):** `PINECONE_NAMESPACE=pilot scripts/ingest.py --country SYR --date-from 2025-06-02` → Suriye son-1-yıl: **805 doc OK / 0 failed / 246 skipped** (boş body) → **"pilot" namespace = 4.892 vektör**. **İzolasyon kanıtlandı:** default namespace 31.628 → 31.628 (DEĞİŞMEDİ).

**A/B sonucu (8 Suriye sorgusu TR+EN, pilot vs default; chat 3.5-flash + judge 2.5-flash her ikisinde sabit):**
| Metrik | Pilot (yeni) | Default (eski) |
|---|---|---|
| ort. chunk uzunluğu | **529 char** | 2400 char |
| max chunk | 792 char (~200 tok) | 5913 char (~1480 tok) |
| judge groundedness | 5.00/5 | 5.00/5 |
| judge relevance | 4.88/5 | 5.00/5 |
| freshness (medyan yaş) | **102 gün** | 387 gün |

**Dürüst değerlendirme:** ✅ **granülarite kesin kazanım** (4.5× küçük; reranker artık chunk'ın %100'ünü görüyor — eskiden ~%25-40). ✅ regresyon yok (5 belge/sorgu, groundedness 5.0). ✅ freshness çok daha iyi (AMA kısmen 1-yıl kapsam etkisi, saf chunking değil). ⚠️ **judge doygun (~5/5 tavan) → kaliteyi KANITLAYAMIYOR**; relevance 4.88 vs 5.00 farkı judge gürültüsü + 1-yıl penceresinin deprem içeriğini kaçırması. **Sonuç: koşullu GO** — chunker mekanizması çalışıyor, kalite argümanı yapısal (küçük chunk → ince embedding + tam reranker görüşü).

---

## Hedef
İnsani yardım M&E ekibi için ReliefWeb belgeleri üzerinden RAG sohbet sistemi. **UI İngilizce (global), sohbet çok dilli.** Marka: **Humanitaria**. Yerel geliştirme aşaması.

## Mevcut Durum (çalışıyor)
- **Mimari:** Gemini (chat/query/embed) + Pinecone — tek sağlayıcı, provider flag YOK. Tamamen bulut.
- **Chat LLM:** Gemini **`gemini-2.5-flash`** (GA, çok dilli; thinking modeli, `reasoning_effort="low"`). `gemini-3.5-flash`'ten geçildi (kronik 503 "high demand"). Transient 503'e karşı bounded retry: non-stream `_ainvoke_with_retry` + stream `_astream_with_retry` (ortak `_is_high_demand`); `except` busy→503/beklenmeyen→500. System prompt İngilizce; yanıt kullanıcının dilinde. Rule 9 = recency.
- **Query processor:** Gemini `gemini-2.5-flash` (DEĞİŞMEDİ). **Embedding:** `gemini-embedding-001` (3072-dim).
- **Chunker:** **`RecursiveCharacterTextSplitter` ~1500 char/200 overlap** (yeni default). NOT: mevcut default-namespace verisi hâlâ ESKİ 800-kelime chunk'larda — rollout'a kadar karışık durum.
- **Retrieval:** güncellik-farkında + alaka reranker'ı (truncate=END); recency blend ham alaka skoruyla. `RECENCY_RERANK_POOL=10`, `RECENCY_BOOST_FACTOR=0.6`.
- **Backend:** FastAPI, port `.env`'deki `API_PORT`. SSE streaming. Vue dist'i **SPA history-mode fallback** ile sunar (`api/main.py`: `/assets` mount + index.html catch-all). Kod değişikliğinden sonra restart (`--reload` yok).
- **Frontend:** Vue 3 + **vue-router** SPA, Humanitaria (yeşil/antrasit, dark+light), İngilizce. Rotalar: **`/` Landing** (marketing, `.mkt-scope` izole CSS) + **`/login`+`/signup`** (`views/AuthView.vue`) + **`/app` Chat** (`views/ChatView.vue`, **router guard'lı — zorunlu giriş**). **Pricing sayfası KALDIRILDI** (route+view+CSS); navbar: Product/Sources/Use cases (Citations nav linki de kaldırıldı, sayfa bölümü+footer linki kaldı). Marketing döküman-scroll (global viewport-lock yalnız chat'e özel: `ChatView .app{height:100vh;overflow:hidden}`). `frontend/dist/` gitignore'da.
- **Test:** **335 backend** + 62 frontend yeşil. Judge groundedness 5.0/5 (doygun); etiketli retrieval metrikleri baseline recall@5=0.224/MRR=0.672/nDCG=0.426 (MMR/havuz tuning A/B'de baseline optimal çıktı — bkz. 2026-06-24 İK3).

## Veri Durumu (Pinecone `reliefweb-docs`, 3072-dim)
- **default namespace (''): 31.628 vektör** — ESKİ 800-kelime chunk, 10 ülke. **App bunu kullanıyor** (cutover henüz YOK).
- **"v2" namespace: 68.936 vektör** — rollout, YENİ ~1500-char chunk. **8/10 ülke** (IRN/IRQ/SYR/TUR/YEM/AFG/SOM/SDN). EKSİK: Palestine (kısmi), Ukraine (0) → Pinecone aylık kotası doldu. 8-ülke A/B GO.
- **"pilot" namespace: 4.892 vektör** — Suriye son-1-yıl, YENİ chunk. v2 onu kapsıyor → cutover'da temizlenebilir.
- ⚠️ **Pinecone AYLIK write-unit kotası (2M) DOLU** — kota reset / plan upgrade olmadan YENİ yazma yapılamaz (ingest 429). Reset sonrası PSE+UKR tamamlanır.
- Yalnız `reports` endpoint. Daha fazla veri: `PINECONE_NAMESPACE=v2 scripts/ingest.py --country X --date-from YYYY-MM-DD --limit N` (`--force` KULLANMA; idempotent).

## Önemli Komutlar
| İş | Komut |
|----|-------|
| Sunucu başlat | `./venv/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8010` |
| Backend testleri | `./venv/Scripts/python.exe -m pytest tests/ -q` |
| Frontend build / test | `cd frontend && npm run build` / `npm test -- --run` |
| RAG eval (judge) | `./venv/Scripts/python.exe scripts/eval_rag.py --judge` |
| Pinecone namespace stats | `./venv/Scripts/python.exe -c "from config import get_settings; from pinecone import Pinecone; s=get_settings(); print(Pinecone(api_key=s.PINECONE_API_KEY).Index(s.PINECONE_INDEX).describe_index_stats())"` |

> **Bash gotcha:** kabuk cwd kalıcı; her komutta önce `cd "C:/Projeler/Reliefweb_RAG_System"`. Inline env var (`PINECONE_NAMESPACE=pilot cmd`, `$(...)`) Bash tool'unda çalışır, PowerShell'de DEĞİL.

## Commit / Push Durumu
- **`origin/master`'a PUSH'LANDI (master = origin):** pilot+chunker+model+date-filter-fix (`…5ab02a0`), store 429-retry (`918637d`), marketing entegrasyonu — Landing/Pricing/router/SPA-fallback (`cdc4a95`), marketing scroll fix (`5810e15`), pricing kaldırma (`e81aade`), citations-nav kaldırma (`daa9e1d`) + MEMORY docs.
- **PUSH'LANDI:** Auth (Login/Signup) sistemi — `2198891` (`6d73d9b..2198891 master→master`), 32 dosya. `.env` gitignored → Google/Gemini/Pinecone secret'ları commit'lenmedi.
- Remote: **https://github.com/berkcansuner/reliefweb-rag** (private).

## Sıradaki Adımlar (kullanıcı yönlendirir)
- [ ] **Kotayı çöz** (aylık reset bekle VEYA Pinecone plan upgrade) → `PINECONE_NAMESPACE=v2 ingest --country PSE UKR --date-from 2023-06-05 --limit 2000` ile v2'yi tamamla.
- [ ] v2 tamla → **CUTOVER:** `PINECONE_NAMESPACE=v2` (config default + .env) commit/push → app v2'ye geçer. Eski default rollback olarak TUT; pilot namespace temizle.
- [ ] (Karar) "pilot" + (cutover sonrası) eski default namespace temizliği.
- [ ] Diğer Faz 2 eksenleri: hibrit (keyword+vektör) arama; kaynak snippet/önizleme.
- [x] ~~Conversation kullanıcı modeli / IDOR~~ → **YAPILDI** (auth sistemi, 2026-06-07, commit bekliyor). Kalan deploy-öncesi: conv rate-limit; CORS daraltma; prod `.env`'e güçlü `AUTH_SESSION_SECRET` + Google cred'leri.
- [x] ~~**İş Kolu 2 — RAG kalite & ölçüm**~~ → **YAPILDI** (eval metrikleri + etiketli set + A/B + sorgu yeniden yazımı; commit bekliyor). A/B: v2≈default doküman düzeyinde.
- [x] ~~**İş Kolu 3 — Veri derinliği** (kod)~~ → **YAPILDI** (parser/chunker/client/retriever zenginleştirme; commit bekliyor). **Çalıştırma:** kota reset'inde `ingest.py` ile re-index (yeni alanlar + chunker o zaman uygulanır).

## Bilinen Sorunlar / Kısıtlamalar
- **Pinecone aylık write-unit kotası (2M):** rollout bunu doldurdu → yeni yazma 429 ("write unit limit for the current month"). Sabit kota; retry çare değil. Reset/plan-upgrade gerek. Büyük ingest planlarken hesaba kat.
- **Karışık chunk durumu:** chunker yeni default (~1500 char) ama mevcut default-namespace verisi hâlâ eski 800-kelime — cutover'a kadar böyle. Yeni ingest'ler yeni chunk üretir.
- 1-yıl ingest penceresi tarihsel büyük olayları kaçırır (deprem) → rollout'ta ≥2-3 yıl.
- ~~Conversation IDOR~~ → **ÇÖZÜLDÜ** (auth sistemi; sohbetler `user_id`-sahipli, non-owner 404). Mevcut conversations.db satırları migration'da `user_id=NULL` → görünmez (dev verisi; kabul).
- Şablon/sistem mesajları (greeting, no-docs) İngilizce; yalnız LLM yanıtı çok dilli (bilinçli).
- Session history varsayılan in-memory (restart'ta silinir); `REDIS_URL` ile kalıcı.
- Görseller/infografikler doğrudan sorgulanamaz (246 Suriye raporu boş body → atlandı).
