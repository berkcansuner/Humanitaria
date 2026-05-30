# MEMORY — ReliefWeb RAG (oturum sürekliliği)

> **Her oturum başında bu dosyayı oku. Her önemli ilerlemeden sonra güncelle.**
> Bu bir tarihçe değil — GÜNCEL durumu yansıtır. Eskiyen satırları sil/değiştir.
> "Nerede kalmıştık?" sorusunun cevabı burasıdır.

**Son güncelleme:** 2026-05-30

---

## Hedef
İnsani yardım M&E ekibi için ReliefWeb belgeleri üzerinden Türkçe/İngilizce çok dilli RAG
sohbet sistemi. Şu an yerel geliştirme aşamasında.

## Mevcut Durum (çalışıyor)
- **Aktif config (.env):** `CHAT_LLM_PROVIDER=gemini`, `VECTOR_STORE_PROVIDER=pinecone`,
  `EMBED_PROVIDER=gemini` → **tamamen bulut, Ollama zorunlu değil** (yalnız query processor Ollama'yı
  dener, kapalıysa rule-based fallback çalışır).
- **Chat LLM:** Google Gemini `gemini-2.5-flash` (OpenAI-uyumlu endpoint). Akıcı Türkçe üretiyor.
- **Query processor** (filtre çıkarma): Ollama `qwen2.5:0.5b` + rule-based fallback. **Artık merge ediliyor** (aşağıya bak).
- **Embedding:** Gemini `gemini-embedding-001` (3072-dim). (`EMBED_PROVIDER=ollama` ile yerel `qwen3-embedding:8b` 4096-dim'e dönülebilir; o zaman `EMBED_DIM=4096` yap.)
- **Vector DB:** Pinecone serverless, index `reliefweb-docs` (3072, cosine, aws/us-east-1). (`VECTOR_STORE_PROVIDER=chroma` ile yerel ChromaDB'ye dönülebilir.)
- **Backend:** FastAPI, config default port 8000. **Ama 8000'i başka bir uygulama (RState_ai emlak app) tutuyor** → RAG şu an **port 8010**'da çalışıyor (`http://localhost:8010`). Frontend relative `fetch('/chat/...')` kullandığı için hangi portta serve edilirse orada çalışır. SSE streaming. Başlangıçta lifespan warmup + ingestion scheduler.
- **Frontend:** Vue 3, `frontend/dist/` build edilmiş, FastAPI statik serve ediyor.
- **Kaynaklar (citation-grounded):** Yanıt context belgelerine satır içi `[n]` atıfı verir; `sources` event'i yalnızca atıf verilen belgeleri döndürür (atıf yoksa fallback: tümü). Prompt artık kaynakları metin içinde isimlendirmiyor — sadece altta `SOURCES (N)` kompakt liste (`[n]` numaralı).
- **Öneriler:** Belirsiz sorgularda yanıttan SONRA **React island** öneri kartı (Claude tarzı, 1/N: ülke→zaman→konu). **Ülke ve zaman aralığı adımları: çip YOK, sadece metin girişi + autocomplete** (yazarken eşleşen öneriler açılır listede). Yalnız **konu adımı çipli** (yan yana çipler, tıklamada "seçildi" flash animasyonu) + metin girişi. Autocomplete: yazılanı filtreler; ok tuşları + Enter / tık seçer. İlerleme noktaları (mobilde gizli), **mobil/responsive (375px doğrulandı)**, klavye, CSS animasyon+reduced-motion, ARIA. `react/SuggestionCard.jsx`(+`.css`) + `SuggestionCardIsland.vue` (Vue↔React köprüsü); seçimler birikir, son adımda sorgu zenginleşir ve **sessiz** gönderilir (`sendMessage({text, silent:true})` → ekstra ham kullanıcı balonu YOK, sadece yeni yanıt gelir). Autocomplete açılır listesi input'un **altında (aşağı doğru)** açılır. SSE sırası: token → sources → clarification.
- **Test:** **212 backend (pytest) + 11 frontend (vitest), hepsi yeşil.**

## Veri Durumu
- **Pinecone `reliefweb-docs`: 866 vektör (3072-dim).** Uçtan uca retrieval + tarih filtresi doğrulandı (Sudan sorguları 5 kaynak dönüyor).
- **Kaynak linkleri rapor web sayfası** (`reliefweb.int/report/{id}`) — PDF değil (tıklayınca tarayıcıda açılır). 2026-05-31 re-ingest (`ingest.py`, 1000 limit → 720 OK) ile mevcut docs'un `url` metadata'sı güncellendi; doc_id stabil olduğu için sayı 866'da kaldı (yerinde overwrite). Tema uyuşmazlığı (öneri temaları ↔ gerçek ReliefWeb temaları) hâlâ açık — bkz. aşağı.
- Veri hâlâ az — kapsamlı sohbet için daha fazlası faydalı olur (opsiyonel, kritik değil).
- Daha fazla veri çek: `python scripts/ingest.py --limit N` (`--force` KULLANMA; idempotent upsert tekrarı önler).
- (Eski yerel ChromaDB `./chroma_db/` artık aktif store değil; provider chroma'ya dönülürse kullanılır.)

## Önemli Komutlar
| İş | Komut |
|----|-------|
| Sunucu başlat | `./venv/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8010` (8000 başka app'te) |
| Veri çek | `python scripts/ingest.py --limit N` |
| Backend testleri | `./venv/Scripts/python.exe -m pytest tests/ -q` |
| Frontend build | `cd frontend && npm run build` |
| Frontend testleri | `cd frontend && npm test -- --run` |

## Remote / Push
- Remote: **https://github.com/berkcansuner/reliefweb-rag** (private). `origin/master` güncel — her tur push ediliyor. (NOT: `RState_ai` farklı bir proje, ona dokunulmadı.)

## Sıradaki Adımlar (bir sonraki oturumda buradan devam)
### ⭐ SONRAKI SEANS ODAĞI: VERİ INGESTION
Kullanıcı bir dahaki seansta **veri ingestion** üzerinde duracak. İlgili bağlam:
- Şu an Pinecone'da ~720 rapor / 866 vektör var (yalnız `reports` endpoint, `--limit 1000`).
- Genişletme yolları: `ingest.py --limit` artır; çoklu endpoint (`--endpoints reports disasters countries`); `--date-from` ile aralık.
- **Tema uyuşmazlığı (önemli):** öneri çiplerindeki/`_THEME_MAP`'teki tema adları veride saklı gerçek ReliefWeb temalarıyla eşleşmiyor (ör. öneri "Protection"/"Shelter and NFI" ↔ veri "Protection and Human Rights"; "Shelter and NFI" veride YOK). Tema filtresi `$eq` olduğundan bu temalar hep boş döner. Ingestion sırasında veya `query_processor`'da hizalanmalı.
- Scheduler (APScheduler) watermark ile incremental ingestion yapıyor; uzun kesinti resume tam test edilmedi.
- PDF içerik ingestion opsiyonel (`FETCH_PDF_CONTENT=False`); açılırsa `pdf_url`'den tam metin çekilir (yavaş).

**Öneri kartı (SuggestionCard) iyileştirmeleri:**
1. [x] ~~Metin girişine autocomplete~~ — TAMAM (2026-05-31, tüm adımlarda).
2. [ ] **Çip sayısını sınırla + "daha fazla":** zaman/konu adımlarında çok seçenek olursa ilk ~6 çip + "daha fazla" toggle.
3. [x] ~~Mobil/responsive~~ — TAMAM (375px CDP doğrulandı; noktalar gizli, taşma yok).
4. [x] ~~Ülke adımı çipsiz, sadece yazı + autocomplete~~ — TAMAM.

**Performans / kalite:**
4. [ ] **React island'ı lazy-load:** `defineAsyncComponent` ile `SuggestionCardIsland`'ı yalnız clarification gelince yükle → React+lucide ilk bundle'dan çıkar (~47KB gz initial tasarruf). `Chat.vue`'de async import.
5. [ ] **Frontend bileşen testleri:** vitest + `@vue/test-utils` (ve React island için ayrı) — şu an yalnız `parseSSE` test ediliyor; SuggestionCard akışı/SourceList test edilmiyor.

**Backend / RAG:**
6. [ ] **Stale warmup fix:** `api/main.py` lifespan warmup `OllamaLangChainEmbeddings` hardcode → `rag.embeddings.get_embeddings()` factory (yanıltıcı 4096≠3072 log + gereksiz Ollama bağımlılığını giderir).
7. [ ] (Opsiyonel) Daha fazla veri ingestion — `ingest.py --limit` artır; çoklu endpoint (`reports disasters countries`).
8. [ ] (Opsiyonel) `RunnableWithMessageHistory` → LangGraph migrasyonu (4 deprecation uyarısı).

**Güvenlik:**
9. [ ] **Gemini API anahtarını rotate et** (geçmişte sohbete yazıldı) — Google AI Studio.

## Bilinen Sorunlar / Açık İşler
- **`requirements.txt` çakışması:** `pip install -r requirements.txt` başarısız (chromadb 1.0.5 → fastapi==0.115.9 ister, ama pin 0.115.0). Tüm requirements'ı kurma; eksik paketleri tek tek kur. Bu oturumda venv'e eksik paketler kuruldu: `langchain-chroma==0.2.4`, `langchain-pinecone==0.2.13`, `apscheduler==3.10.4` (chromadb otomatik 1.5.9 oldu).
- **Stale warmup:** lifespan warmup Gemini provider'da yanıltıcı dim-mismatch uyarısı veriyor (kritik değil; gerçek istekler `get_embeddings()` factory kullanıyor). Bkz. Sıradaki Adımlar #2.
- Query processor modeli çok küçük (`qwen2.5:0.5b`); merge fix sonrası rule-based backstop güvenilirliği artırdı ama harita-dışı ülke/kaynak için sınırlı.
- **Gemini API anahtarı geçmişte sohbete yazıldı → Google AI Studio'dan rotate edilmeli.**
- CORS production için daraltılmalı (şu an localhost origin'leri, `.env` `CORS_ORIGINS`).
- Pipeline resume kısmi: scheduler watermark (`chroma_db/.last_ingest.json`) var ama uzun kesinti tam test edilmedi.

## Son Oturum Özeti (2026-05-31)
Bu seansta öneri kartı (React island) ince ayarları + iki UX/veri düzeltmesi yapıldı (hepsi commit+push'lu):
- **Öneri kartı:** ülke + zaman aralığı çipsiz (yazı+autocomplete), konu çipli; autocomplete prefix/kelime-başı eşleşme ("s"→Sudan/Syria, Afghanistan değil); çip seçince "seçildi" flash; seçim **sessiz** uygulanıyor (ham birleşik sorgu balonu YOK); dropdown aşağı açılır; mobil/responsive.
- **Boş-sonuç mesajı** kullanıcı dostu yapıldı (geliştirici `ingest.py` komutu kaldırıldı).
- **Kaynak linkleri rapor web sayfası** oldu (PDF→indirme yerine tarayıcıda açılır): `parser.py` `url=canonical_url`; re-ingest (720 OK) ile mevcut veri güncellendi; canlı 8010'da doğrulandı.
- **Server 8010'da** (8000 başka app'te). 212 backend + 11 frontend test yeşil.
- **Sonraki seans: VERİ INGESTION** (bkz. Sıradaki Adımlar ⭐). Açık iş: tema uyuşmazlığı.

---

### Daha önce (2026-05-31, aynı gün): React island tasarımı
Öneri kartı **React island** olarak yeniden tasarlandı (kullanıcı tercihi). `ui-ux-pro-max` skill
tasarım yönü için kullanıldı; **Magic MCP `[object Object]` döndürdü (bu ortamda bozuk)** → React
bileşeni spec'e göre elle yazıldı. Eklenenler: `frontend/src/components/react/SuggestionCard.jsx`
(+`.css`), `SuggestionCardIsland.vue` (createRoot ile Vue↔React köprüsü), `vite.config.js`'e
`@vitejs/plugin-react@^4` (jsx/tsx scope), deps `react@18 react-dom lucide-react`. Eski Vue
`SuggestionCard.vue` kaldırıldı. Cilalı minimal + tam klavye + CSS animasyon (reduced-motion) + ARIA.
Bundle 52→99KB gz (React maliyeti). CDP ile canlı doğrulandı (tema `rgb(97,0,0)`, klavye 1/3→3/3→birleşik
sorgu). 11/11 frontend test geçiyor. (Daha hafif Vue-native alternatif fallback olarak duruyor.)

---

### Önceki tur (2026-05-30)
query-processor merge fix + chat input UX fix (7 commit). Ardından 3 özellik:

1. **Citation-grounded sources** (`api/routes/chat.py`, `rag/chain.py`): Context belgeleri `[n]` ile
   numaralanır; prompt modele kullandığı belgeye `[n]` atıfı vermesini söyler; route yanıttaki `[n]`
   işaretlerini ayıklayıp `sources`'u sadece atıf verilenlere filtreler (`_filter_cited_sources`,
   atıf yoksa fallback=tümü). `SourceDocument`'a `index` eklendi. Canlı: 5 retrieve → 4 atıf → 4 kaynak.
2. **Öneriler yanıttan sonra** (`api/routes/chat.py`, `Chat.vue`): `clarification` SSE event'i artık
   token+sources'tan SONRA yayınlanıyor; `Chat.vue` clarification kartı sade öneri şeridine restyle edildi.
3. **Kompakt kaynak listesi** (`SourceList.vue`): büyük kartlar → ince tek-satır `[n] başlık · kaynak · tarih`.

212/212 backend + 11/11 frontend test geçiyor. Backend (citation filter + event sırası) ve frontend
(kompakt liste + `[n]`, CDP screenshot) canlı doğrulandı. **Push engellendi:** verilen repo yanlış (bkz. üstteki PUSH ENGELİ).
