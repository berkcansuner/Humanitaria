# MEMORY — ReliefWeb RAG (oturum sürekliliği)

> **Her oturum başında bu dosyayı oku. Her önemli ilerlemeden sonra güncelle.**
> Bu bir tarihçe değil — GÜNCEL durumu yansıtır. Eskiyen satırları sil/değiştir.
> "Nerede kalmıştık?" sorusunun cevabı burasıdır.

**Son güncelleme:** 2026-06-07

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
- **Chat LLM:** Gemini **`gemini-3.5-flash`** (GA, çok dilli; thinking modeli — streaming latency kötüyse `reasoning_effort="low"` düşünülebilir, `chain.py`). System prompt İngilizce; yanıt kullanıcının dilinde. Rule 9 = recency.
- **Query processor:** Gemini `gemini-2.5-flash` (DEĞİŞMEDİ). **Embedding:** `gemini-embedding-001` (3072-dim).
- **Chunker:** **`RecursiveCharacterTextSplitter` ~1500 char/200 overlap** (yeni default). NOT: mevcut default-namespace verisi hâlâ ESKİ 800-kelime chunk'larda — rollout'a kadar karışık durum.
- **Retrieval:** güncellik-farkında + alaka reranker'ı (truncate=END); recency blend ham alaka skoruyla. `RECENCY_RERANK_POOL=10`, `RECENCY_BOOST_FACTOR=0.6`.
- **Backend:** FastAPI, port `.env`'deki `API_PORT`. SSE streaming. Vue dist'i **SPA history-mode fallback** ile sunar (`api/main.py`: `/assets` mount + index.html catch-all). Kod değişikliğinden sonra restart (`--reload` yok).
- **Frontend:** Vue 3 + **vue-router** SPA, Humanitaria (yeşil/antrasit, dark+light), İngilizce. Rotalar: **`/` Landing** (marketing, `.mkt-scope` izole CSS) + **`/login`+`/signup`** (`views/AuthView.vue`) + **`/app` Chat** (`views/ChatView.vue`, **router guard'lı — zorunlu giriş**). **Pricing sayfası KALDIRILDI** (route+view+CSS); navbar: Product/Sources/Use cases (Citations nav linki de kaldırıldı, sayfa bölümü+footer linki kaldı). Marketing döküman-scroll (global viewport-lock yalnız chat'e özel: `ChatView .app{height:100vh;overflow:hidden}`). `frontend/dist/` gitignore'da.
- **Test:** **297 backend** + 61 frontend yeşil. Judge groundedness 5.0/5, relevance ~4.9-5.0/5 (judge doygun/varyanslı).

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
- [ ] **İş Kolu 2 — RAG kalite & ölçüm** (etiketli eval seti recall@k/MRR + konuşma-bağlamlı sorgu yeniden yazımı). Onaylı plan: `~/.claude/plans/bunlar-d-nda-ekleyebilece-imiz-bir-drifting-cat.md`.
- [ ] **İş Kolu 3 — Veri derinliği** (ingest metadata zenginleştirme ISO3/dil/ikincil tema + tam reindex; çalıştırma Pinecone kota reset'ine bağlı).

## Bilinen Sorunlar / Kısıtlamalar
- **Pinecone aylık write-unit kotası (2M):** rollout bunu doldurdu → yeni yazma 429 ("write unit limit for the current month"). Sabit kota; retry çare değil. Reset/plan-upgrade gerek. Büyük ingest planlarken hesaba kat.
- **Karışık chunk durumu:** chunker yeni default (~1500 char) ama mevcut default-namespace verisi hâlâ eski 800-kelime — cutover'a kadar böyle. Yeni ingest'ler yeni chunk üretir.
- 1-yıl ingest penceresi tarihsel büyük olayları kaçırır (deprem) → rollout'ta ≥2-3 yıl.
- ~~Conversation IDOR~~ → **ÇÖZÜLDÜ** (auth sistemi; sohbetler `user_id`-sahipli, non-owner 404). Mevcut conversations.db satırları migration'da `user_id=NULL` → görünmez (dev verisi; kabul).
- Şablon/sistem mesajları (greeting, no-docs) İngilizce; yalnız LLM yanıtı çok dilli (bilinçli).
- Session history varsayılan in-memory (restart'ta silinir); `REDIS_URL` ile kalıcı.
- Görseller/infografikler doğrudan sorgulanamaz (246 Suriye raporu boş body → atlandı).
