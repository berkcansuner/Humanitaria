# MEMORY — Humanitaria / ReliefWeb RAG (oturum sürekliliği)

> **Her oturum başında bu dosyayı oku. Her önemli ilerlemeden sonra güncelle.**
> Tarihçe değil, GÜNCEL durum: eskiyen satırı değiştir ya da sil, ~100 satırı geçme.
> Ayrıntı commit mesajlarında ve `git log`'da. 2026-06 → 2026-11-16 arası uzun tarihçe:
> `git show 2daf528:MEMORY.md`.

**Son güncelleme:** 2026-11-16 — MEMORY.md sadeleştirildi (420 → ~100 satır); 17 birleşmiş yerel branch silindi;
**Dalga 2 CANLIDA** (`c57395e`…`5ddf0de`, 776 test yeşil, CI yeşil):
akış hatalarında traceback (`logger.exception`), ölü `rag/query_rewriter.py` silindi (`_format_history` →
`query_processor`), context her belgede `Source: <kurum>` satırı taşıyor, sohbet prompt'u uygulanan filtreleri
görüyor (`rag/chain.py` `describe_filters`, kural 5). Canlı test (Sudan, Ocak 2026'dan beri gıda güvenliği, TR): cevap "Uygulanan filtreler: Ülke: Sudan; Konu: Gıda ve
Beslenme; Tarih: 2026-01-01 …" satırıyla başlıyor, rakamlar kurumla anılıyor (FSL Kümesi); test sohbeti silindi.
Küçük: filtre satırı biraz mekanik; tek tük İngilizce kelime kaldı ("cereal", "Famine"). Rapor tarafı canlıda denenmedi.

---

## Kalıcı kullanıcı talimatları
- **"Devam edelim" denince:** önce plan; seçenekleri önceliklendir, kullanıcıyla seç, hemen koda dalma.
- **Tasarım değişiklikleri geri alınabilir:** her adım ayrı branch + ayrı commit, öncesi/sonrası ekran görüntüsü (CLAUDE.md kural 6).
- **Canlı Gemini harcayan denemelerden önce** kullanıcı onayı al, maliyeti tahmin et.
- **Tekrar önerme (kullanıcı reddetti):** anahtar-rakam paneli (`d03d50d` ile kaldırıldı); AI rapor görselleri
  (kod duruyor, `REPORT_IMAGES_ENABLED=False`); admin "Data breakdown" çubuk grafikleri.
- **Kimlik rotasyonu hatırlatması yapma** (kullanıcı talimatı, 2026-07-10).
- **Repo herkese açık:** bu dosyaya kişisel değer veya sır yazma.
- Hesaptaki eski sohbet ve raporlar kullanıcınındır; test verisini yalnız kendin oluşturduysan sil.
- Arayüz İngilizce (global), sohbet çok dilli.

## Canlı sistem
- **URL:** https://humanitaria.onrender.com · Render ücretsiz Docker, Frankfurt, servis `humanitaria`.
  `master`'a push → otomatik deploy (CI: `.github/workflows/ci.yml`). 15 dk boşta uyur; ilk istek ~30–60 sn.
- **Render paneli:** `GEMINI_BASE_URL` = Cloudflare AI Gateway (Render IP'si Gemini'den engelli). Model/effort override YOK
  (kullanıcı 2026-11-16'da doğruladı); override eklenirse kod varsayılanını ezer. `HDX_APP_IDENTIFIER`,
  `INGEST_TRIGGER_TOKEN`, `ADMIN_EMAILS` panelde. `RATE_LIMIT_TRUSTED_HOPS=3`.
- **DB:** Supabase `humanitaria` (Frankfurt, ücretsiz plan). App tabloları + `chunks`/`documents` (pgvector). Tüm
  tablolarda RLS açık, politika yok, `anon`/`authenticated` REVOKE. Yerel `.env` `DATABASE_URL` CANLI DB'yi gösterir.
- **Pinecone:** yalnız reranker (Inference API, index yok). `PINECONE_API_KEY` kalsın.
- **Modeller (2026-11-16):** sohbet + sorgu işleme `gemini-3.5-flash-lite` (effort medium, `CHAT_LLM_TIMEOUT=90`);
  raporlar + "What changed" kontrolü `gemini-3.8-flash` (`REPORT_LLM_MODEL`, medium, `REPORT_LLM_TIMEOUT=240`).
  Fiyat ($/1M girdi/çıktı): 3.5 FL 0,30/2,50; 3.8 Flash 0,75/3,75 → **2027-01-01'den 1,50/7,50**.
  Rapor ~110 sn + kontrol ~27 sn; sonraki dönem raporu ≲2,5 TL, tek seferlik ≲1,5 TL.
- **Gece ingest:** GitHub Actions `nightly-ingest.yml`, 03:00 UTC + elle çalıştırma → `/health` ile uyandırır → token'lı
  `POST /admin/ingest/cron` (202 arka plan). Repo sırrı `INGEST_TRIGGER_TOKEN` = Render'daki değer. Cloudflare Worker
  `humanitaria-daily-cron` cron'suz duruyor (Render, CF Worker IP'lerine 429 veriyordu); geri almak için
  `cloudflare-cron/wrangler.toml`'a cron satırını geri koy. Retention: 365 gün + ülke başına 200 belge.
- **Admin** = `ADMIN_EMAILS` listesinde **ve** Google bağlı hesap.

## Veri durumu (2026-11-16)
- ~9.070 belge / ~25.001 chunk, DB ~161 MB / 500 MB. Watermark `ingest_state` tablosunda (2026-11-16).
- Kapsam: tüm ülkeler × son 1 yıl × ülke başına en yeni 200 (`reports` + `disasters`). Metinsiz (PDF/infografik) belgeler atlanır.
- Sıfırdan yükleme (yerelden, ~1 saat, idempotent):
  `.\.venv\Scripts\python.exe scripts/ingest.py --all-countries --limit 200 --endpoints reports disasters`

## Canlıdaki özellikler (özet)
- **Sohbet:** SSE akış; sessiz atıf çipleri + `CitePreview` önizlemesi + "Back to text"; "Copy answer with sources";
  hatada "Try again"; cevap dili kodda belirlenir (`rag/chain.py` `answer_language`).
- **M&E raporları** (`/reports?report=<id>`; DİKKAT: `/reports/<id>` JSON API'dir): türler `situation`,
  `indicator_monitoring`, `needs_assessment`, `technical_monitoring` (HDX HAPI'den 6 indikatör, istatistik kodda,
  matplotlib grafikleri, LLM yalnız yorumlar). PDF export. **Rapor serisi:** `previous_report_id`, "Run next period",
  "What changed since the last report" + `rag/report_compare.py` doğrulama çağrısı (model yalnız silinecek cümle
  numaralarını döner, silmeyi kod yapar), üretim sırasında Stop.
- **Tasarım:** "Quiet Archive" (`PRODUCT.md`, `DESIGN.md`, `.impeccable/design.json`); Source Serif 4 (okuma metni) +
  Inter (arayüz); Claude ölçüleri (sidebar 288px, cevap sütunu 736px). Son critique 3. tur 27/40
  (`.impeccable/critique/`). impeccable v4.9.1'de sabit.
- **Diğer:** Google + e-posta/şifre girişi, Ayarlar, Admin (ingestion paneli, kullanıcılar, belge listesi),
  geri alınabilir silme (8 sn undo).

## Yerel geliştirme ve doğrulama
- Python 3.12 `.venv` → `.\.venv\Scripts\python.exe -m pytest tests/ -q` (+ CI kapsamı `ruff check api rag ingestion config.py`; `tests/` eski uyarılar taşır); frontend (Node 24)
  `cd frontend; npm test; npm run lint; npm run build`.
- **Yerel UI (canlı DB'ye dokunmadan):** `DATABASE_URL= CONVERSATION_DB_PATH=<scratch>.db INGEST_SCHEDULE_HOURS=0`
  ile uvicorn :8010; demo kullanıcı + raporları `rag.users`/`rag.reports` ile tohumla; `rw_session` çerezini JS ile ayarla.
- **Telefon ekran görüntüsü:** Chrome penceresi yeniden boyutlanmıyor → Playwright'ın chrome-headless-shell'iyle headless
  CDP betiği (VW/VH/DPR). Chrome eklentisinde ref-tıklama router-link'i tetiklemez, koordinatla tıkla.
- Vite önizlemesi bazen eski modül verir → `touch` + `?v=` ile yenile.
- `tests/test_pgvector_store.py` tabloları DROP eder → yalnız yerel/CI Postgres (Supabase URL'si reddedilir).
- `router.onError` dinleyicisi varken vue-router hataları kendiliğinden loglamaz → işlenmeyen hatayı handler'da logla.
- Cron kontrolü: Actions API `workflows/nightly-ingest.yml/runs` (event=schedule) + `ingest_state.updated_at`.

## Açık işler (öncelik sırasıyla)
1. **17 Kasım 03:00 UTC** zamanlanmış gece çalışmasını doğrula (ilk zamanlanmış koşu; elle koşu başarılıydı).
2. **Dalga 3 — eval kapılı retrieval:** rerank skor eşiği, MMR'ın cross-encoder'dan önce aday elemesi, geçmiş/trend
   sorularında recency'yi kapatma, çoklu ülke yakalama. Önce baseline'ı yeniden ölç (son: recall@5 0,253 / MRR 0,528 /
   nDCG@5 0,327, 2026-07-10; pgvector ve model değişiminden ÖNCE).
3. **Rapor kalitesi kalanları:** "What changed" kontrolü fazla temkinli (gerçek yeni riski silebiliyor); silme sonrası
   bağlayıcı cümle boşta kalabiliyor; 3.5 FL sohbette iki kaynağın rakamını tek rakamda birleştirdi (Sudan IPC).
4. **Büyük özellikler** (her biri kendi brainstorm → plan turu): arayüz TR/EN dil seçici (i18n yok); sohbet
   export/paylaş; scrollytelling rapor; donör şablonu; HAPI conflict_events'i geri getirme; refugees için asylum tarafı.
5. **Zamanlı:** 3.8 Flash fiyatı 2027-01-01'de ikiye katlanıyor → öncesinde rapor model kararını gözden geçir.
   Google OAuth uygulamasını yayınla (son bilinen: Testing modu; güncel durum doğrulanmadı).
6. **Küçükler:** `generate()` başta `syncUrl(null)` → çok hızlı sunucu hatasında hata kutusu görünmeyebilir;
   embedding `task_type` (native `:embedContent` + korpus re-embed); React 19 / vue-router 5; her deploy eski
   `/assets`'i siler (açık sekme bir kez tam yenilemeyle kurtulur).

## Bilinen kısıtlamalar
- Supabase ücretsiz: 500 MB sınır, 7 gün hareketsizlikte duraklama (gece ingest önler).
- 1 yıllık pencere tarihsel büyük olayları kaçırır.
- Selamlama / "belge bulunamadı" şablonları İngilizce; yalnız LLM cevabı çok dilli (bilinçli).
- Görseller/infografikler sorgulanamaz; yalnız başlık + açıklama index'lenir.
- Sohbet geçmişi penceresi in-memory LRU; restart sonrası `messages` tablosundan yüklenir.
