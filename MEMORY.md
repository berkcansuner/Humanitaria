# MEMORY — ReliefWeb RAG (oturum sürekliliği)

> **Her oturum başında bu dosyayı oku. Her önemli ilerlemeden sonra güncelle.**
> Bu bir tarihçe değil — GÜNCEL durumu yansıtır. Eskiyen satırları sil/değiştir.
> "Nerede kalmıştık?" sorusunun cevabı burasıdır.

**Son güncelleme:** 2026-05-31

---

## ✅ Son tamamlanan iş (2026-05-31 akşam — claude.ai-tarzı özellikler, 5 faz + citation fix)
Plan dosyası: `C:\Users\bcsun\.claude\plans\misty-spinning-pebble.md`.
**6 commit `master`'da, henüz PUSH EDİLMEDİ** (`git log origin/master..HEAD`):
`2432f85` citation fix → `5639981` faz1 → `563e163` faz2 → `f3a66f1` faz3 → `4c53cb8` faz4 →
`8180513` faz5. Test: **251 backend + 43 frontend** yeşil.

1. **Citation fix** (`renumberCitations.js`): atıf verilen kaynaklar 1..M'e yeniden numaralanıyor —
   tek kaynak artık `[3]` değil `[1]` (eski hata: `_filter_cited_sources` orijinal index'i koruyup boşluk bırakıyordu).
2. **Faz1 hızlı kazanımlar:** dark mode (`theme.js`, `style.css` `:root[data-theme=dark]`, `ThemeToggle`),
   boş-ekran örnek sorgu kartları (`EmptyState`), kod-bloğu kopyala (`codeCopy.js`).
3. **Faz2 durdur+yeniden üret:** `AbortController`+Stop (abort=temiz durdurma, kısmi metin kalır),
   `MessageActions` (kopyala/regenerate), `conversationOps.js`.
4. **Faz3 SQLite kalıcılık:** `rag/conversations.py` (sync, WAL, CASCADE), `api/routes/conversations.py`
   (CRUD; auth VAR, chat rate-limit YOK), `chat.py` entegrasyon (ilk mesajda auto-create+başlık,
   soğuk-başlangıç pencere seed, her exchange persist). `CONVERSATION_DB_PATH=./conversations.db`
   (gitignore'da). conftest autouse fixture DB'yi izole eder (gerçek DB kirlenmesin).
5. **Faz4 sidebar:** `api.js` client, `Sidebar`/`ConversationList`, App.vue sidebar+main layout,
   Chat.vue `conversationId` prop ile konuşma yükleme/değiştirme + yeni sohbet.
6. **Faz5 düzenle/yeniden gönder:** stream `persisted` event (mesaj id'leri)+`serverId` takibi;
   `POST /conversations/{id}/truncate`+`resync_window`; edit (inline textarea) ve regenerate ortak
   `resendFrom` ile sunucu+istemci kırpıp yeniden gönderir (duplicate/bayat turn yok).

**Sıradaki adım:** `git push origin master` (6 commit). Manuel tarayıcı testi kullanıcıda.
Ingest bitince Pinecone vektör sayısını güncelle.

**ÇALIŞAN VERİ İNGESTİ (arka plan):** `ingest.py --country IRN TUR UKR SYR IRQ --limit 5000`.
IRN/TUR/UKR/SYR bitti, IRQ sürüyordu (son ülke, ETA ~45dk). Bitince Pinecone toplam vektörü
`describe_index_stats` ile kontrol et + güncelle (başlangıç 11.599).

**Önceki iş (pushed, `acd4170`'e kadar):** 4 iyileştirme — tema kirliliği fix, retrieval dedup+rerank,
API rate-limit+auth, eval LLM-judge (groundedness/relevance 5.00/5.00).

---

## Hedef
İnsani yardım M&E ekibi için ReliefWeb belgeleri üzerinden Türkçe/İngilizce çok dilli RAG
sohbet sistemi. Şu an yerel geliştirme aşamasında.

## Mevcut Durum (çalışıyor)
- **Aktif config (.env):** `CHAT_LLM_PROVIDER=gemini`, `VECTOR_STORE_PROVIDER=pinecone`,
  `EMBED_PROVIDER=gemini`, **`QUERY_LLM_PROVIDER=gemini`** → **tamamen bulut, Ollama hiç gerekmez**
  (query processor artık Gemini'de; yerel Ollama'ya bağımlılık kalmadı).
- **Chat LLM:** Google Gemini `gemini-2.5-flash` (OpenAI-uyumlu endpoint). Akıcı Türkçe.
- **Query processor** (filtre çıkarma): **Gemini `gemini-2.5-flash`** (`QUERY_LLM_PROVIDER`,
  `GEMINI_QUERY_MODEL`) + rule-based backstop (merge). Gemini json_mode bazen string alanları
  tek elemanlı liste döndürüyor → `QueryFilters` validator'ı liste→ilk eleman coerce ediyor.
  `QUERY_LLM_PROVIDER=ollama` ile eski yerele dönülebilir.
- **Embedding:** Gemini `gemini-embedding-001` (3072-dim). (`EMBED_PROVIDER=ollama` ile yerel.)
- **Vector DB:** Pinecone serverless, index `reliefweb-docs` (3072, cosine, aws/us-east-1).
- **Backend:** FastAPI, config default port 8000. **8000'i başka app (RState_ai) tutuyor** → RAG
  **port 8010**'da çalışıyor. Frontend relative `fetch('/chat/...')` → hangi portta serve edilirse
  orada. SSE streaming. Lifespan warmup artık `get_embeddings()` factory kullanıyor (provider'a
  uygun; yanıltıcı dim-mismatch uyarısı giderildi).
- **Frontend:** Vue 3, `frontend/dist/` build (gitignore'da — yerelde build edilir). React öneri
  island'ı (`SuggestionCardIsland`) artık **lazy-load** (`defineAsyncComponent`) → ayrı async chunk;
  initial JS bundle ~99→**~52 KB gz**.
- **Kaynaklar:** citation-grounded (`[n]`), rapor web sayfası linkleri.
- **Öneriler:** belirsiz sorguda yanıttan sonra React island kartı (ülke/zaman çipsiz+autocomplete,
  konu çipli), sessiz uygulama.
- **Test:** **232 backend (pytest) + 11 frontend (vitest), hepsi yeşil.**
- **RAG eval:** `python scripts/eval_rag.py` (filtre + canlı retrieval) / `--no-retrieval` (offline) /
  `--judge` (LLM-judge: groundedness+relevance 1-5, Gemini). Son koşu: filtre 20/20 vaka, judge
  groundedness 5.00 / relevance 5.00.

## Veri Durumu
- **Pinecone `reliefweb-docs`: 11.599 vektör (3072-dim).** Üç aşamada (2026-05-31): (1) global
  `reports --limit 3000` → 2282 OK; (2) ülke-bazlı `--country` (10 ülke × 400) → 3035 OK;
  (3) ülke-bazlı (10 ülke × 1000) → 7894 OK. Yalnız `reports` endpoint.
- **Tema uyuşmazlığı ÇÖZÜLDÜ:** tema adları ReliefWeb taksonomisine hizalandı
  (`Protection and Human Rights`, `Shelter and Non-Food Items`; diğer 6 zaten doğruydu). Eval ile
  doğrulandı (tema filtreli sorgular artık sonuç dönüyor).
- **Ülke kapsamı:** 10 öneri ülkesi (IRN/SYR/YEM/UKR/TUR/AFG/SOM/SDN/PSE/IRQ) hedefli çekildi;
  önceki "Sudan + Water Sanitation Hygiene → 0 belge" boşluğu KAPANDI (eval'de 1 belge — sınırlı).
  Harita-dışı ülkeler için kapsam hâlâ sınırlı (genişletme açık iş).
- Daha fazla veri: `python scripts/ingest.py --limit N` (`--force` KULLANMA; idempotent upsert).
  Pagination zaten var (pipeline offset döngüsü, BATCH_SIZE=500) → >1000 sorunsuz.

## Önemli Komutlar
| İş | Komut |
|----|-------|
| Sunucu başlat | `./venv/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8010` |
| Veri çek (global) | `python scripts/ingest.py --limit N` |
| Veri çek (ülke) | `python scripts/ingest.py --country IRN SYR YEM UKR TUR AFG SOM SDN PSE IRQ --limit 400` |
| Backend testleri | `./venv/Scripts/python.exe -m pytest tests/ -q` |
| RAG eval | `./venv/Scripts/python.exe scripts/eval_rag.py [--no-retrieval]` |
| Frontend build | `cd frontend && npm run build` |
| Frontend testleri | `cd frontend && npm test -- --run` |

## Remote / Push
- Remote: **https://github.com/berkcansuner/reliefweb-rag** (private). `origin/master` güncel.
  (NOT: `RState_ai` farklı bir proje.)

## Sıradaki Adımlar
**Veri / kapsam:**
- [ ] Ülke/tema haritalarını genişlet (`_COUNTRY_MAP` ~10 ülke; temalar 8/19). Kapsam dışı
      ülke/tema sorulduğunda filtre üretilmiyor.
- [ ] (Opsiyonel) Çoklu endpoint ingest (`--endpoints reports disasters countries`). NOT: tema
      kirliliği ÇÖZÜLDÜ — `parse_disaster` artık `theme=""` (afet tipini tema filtresine yazmıyor).
- [ ] (Opsiyonel) PDF içerik ingestion (`FETCH_PDF_CONTENT=True`) — daha zengin gövde, yavaş.

**Frontend (bekleyen):**
- [ ] Öneri kartı: çip sayısını sınırla + "daha fazla" toggle.
- [ ] Frontend bileşen testleri (vitest + @vue/test-utils; şu an yalnız parseSSE).

**Backend / RAG:**
- [ ] (Opsiyonel) Session history kalıcılığı için `REDIS_URL` (şu an in-memory).

## Bilinen Sorunlar / Kısıtlamalar
- Gemini query json_mode bazen liste döndürüyor (validator ile coerce ediliyor; sorun değil).
- Query/embedding/chat hepsi Gemini → Gemini rate limit/kota toplu işlemlerde (ör. büyük ingest,
  retrieval'lı eval) yavaşlatabilir; embedding retry x3 mevcut.
- CORS production için daraltılmalı (şu an localhost origin'leri).
- Session history varsayılan in-memory (restart'ta silinir); `REDIS_URL` ile kalıcı.
- Pipeline resume kısmi: scheduler watermark var ama uzun kesinti tam test edilmedi.

## Son Oturum Özeti (2026-05-31)
Tema fix + 3 iyileştirme + veri ingestion (hepsi commit+push'lu):
- **Tema hizalama** (`query_processor.py`): `_THEME_MAP`/`_SUGGESTION_THEMES`/prompt ReliefWeb
  taksonomisine uyduruldu (ReliefWeb facet ile doğrulandı). 2 yeni test.
- **Warmup fix** (`api/main.py`): `get_embeddings()` factory.
- **React island lazy-load** (`Chat.vue`): `defineAsyncComponent`, bundle 99→52 KB gz.
- **Veri ingestion:** global `reports --limit 3000` (2282 OK) + ülke-bazlı `--country` (10 ülke×400,
  3035 OK); Pinecone 866→**5697 vektör**. Yeni: `ingest.py --country` (`primary_country.iso3`
  filtresi, +date ile AND), 3 yeni test. Sudan+WASH boşluğu kapandı.
- **Query processor → Gemini** (`config.py` `QUERY_LLM_PROVIDER`/`GEMINI_QUERY_MODEL`,
  `query_processor.py`): Ollama bağımlılığı kalktı; liste-coerce validator + 3 test.
- **requirements.txt** çalışan sete sabitlendi (chromadb 1.5.9 / fastapi 0.115.9 ...); `pip check` temiz.
- **RAG eval harness** (`scripts/eval_rag.py`): filtre 10/10, retrieval canlı doğrulandı; Gemini
  liste-bug'ını ve bir veri boşluğunu (Sudan+WASH) yakaladı.
- **Testler:** 220 backend + 11 frontend yeşil.

> NOT (ortam): Bu oturumda araç çıktıları kalıcı şekilde ~1 tur gecikmeli geldi (harness sorunu);
> işlevsel olarak tüm adımlar doğrulandı.
