# MEMORY — ReliefWeb RAG (oturum sürekliliği)

> **Her oturum başında bu dosyayı oku. Her önemli ilerlemeden sonra güncelle.**
> Bu bir tarihçe değil — GÜNCEL durumu yansıtır. Eskiyen satırları sil/değiştir.
> "Nerede kalmıştık?" sorusunun cevabı burasıdır.

**Son güncelleme:** 2026-06-02

---

## ✅ Bu seansta tamamlanan iş (2026-06-02) — COMMIT'LENDİ + PUSH'LANDI

### A) Önceki seansın bekleyen işi 5 mantıklı commit'e ayrıldı (master)
`3323e51` ingestion (source-link `/node/{id}` + 5xx/orphan reliability) · `fe94ebe` CORS `X-API-Key` ·
`a12767a` İngilizce backend mesaj/prompt · `edec7a4` Humanitaria redesign + İngilizce UI + resend guard ·
`98564d3` MEMORY.md. (redesign+İngilizce aynı dosyalarda iç içe → dosya düzeyinde birleşti.)

### B) Faz 2 ilk dilim — Güncellik-farkında retrieval TAMAMLANDI (7 commit)
**Amaç:** "current situation in X" sorularında en güncel raporların yanıta girmesi (veri silmeden, geçmiş sorgularını bozmadan).
- `should_boost_recency(query, filters)` (`rag/query_processor.py`): boost varsayılan AÇIK; tarih filtresi varsa
  veya geçmiş/trend kelimesi (evolv/trend/tarihçe/"nasıl gelişti"...) varsa KAPALI.
- `_retrieve_docs` (`api/routes/chat.py`): boost AÇIK → alaka rerank'i **geniş havuza** (`RECENCY_RERANK_POOL=10`)
  uygulanır, sonra `RECENCY_BOOST_FACTOR=0.6` ile recency-blend, sonra top-k → 6-10. sıradaki güncel raporlar yükselir.
  Boost KAPALI → eski davranış (alaka→top-k + hafif recency 0.3).
- Yanıt: context satırları artık `[n] (YYYY-MM-DD) ...` (LLM tarihleri görüyor); system prompt **rule 9** "en yeni
  belgelere öncelik ver, tarih aralığını belirt". `eval_rag.py` formatı senkron.
- `eval_rag.py`: artık route'un gerçek `_retrieve_docs`'unu çağırıyor (DRY) + **freshness metriği** + vakalar.

**Önce/sonra (eval, canlı Pinecone) — sıfır-sonuç regresyonu YOK:**
| Sorgu | medyan yaş (önce→sonra) | ≤6ay (önce→sonra) |
|---|---|---|
| Sudan "current" | 80g → 42g | 5/5 → 5/5 |
| Yemen "current" | 315g → **76g** | 1/5 → **4/5** |
| Ukraine "latest" | 542g → **260g** | 1/5 → **2/5** |

**Test:** **278 backend (pytest) + 51 frontend (vitest) yeşil.** Spec/plan: `docs/superpowers/{specs,plans}/2026-06-01-recency-aware-retrieval*` (gitignore'da, yerel).

### ✅ Reranker token-limit fix (2026-06-02, master'da, commit `e4624b2`)
`rerank_by_relevance` query+doc çiftinde 1024-token sınırını aşan chunk'larda 400 verip MMR'a düşüyordu
(chunker kelime-bazlı, ~800 kelime ≈ ~1760 token) → alaka sinyali sessizce kayboluyordu. Fix: rerank çağrısına
`parameters={"truncate": "END"}`. "Relevance rerank failed" uyarıları artık **0**; reranker tüm sorgularda çalışıyor.
**Yan etki/gözlem:** gerçek alaka reranking'i devreye girince Ukraine "latest" sorgusu *daha eski* çıktı
(medyan 260g→501g) — en alakalı Ukraine içeriği eski; eski 260g bozuk reranker'ın yan etkisiydi. **Sonuç:
recency-boost artık yeniden ayar gerektirebilir** (alaka güçlendi). Sudan 39g/5-5, Yemen 76g/5-5 (Yemen 4/5→5/5'e çıktı).

### ⚠️ Açık taşınan not
- **Büyük-harf Türkçe** geçmiş sorgusu ("NASIL GELİŞTİ") boost-off'u kaçırır (`_turkish_lower` noktalı/noktasız `i`).
  Düşük etki, mevcut rule-based davranışıyla tutarlı.
- **Chunk boyutu 800 kelime** (büyük): retrieval hassasiyetini + context boyutunu etkiler, reranker truncate=END ile
  yalnız ilk ~1024 token'ı görür. Küçültmek 31.5k vektör re-ingest gerektirir → ayrı/büyük karar.

---

## Hedef
İnsani yardım M&E ekibi için ReliefWeb belgeleri üzerinden RAG sohbet sistemi. **UI İngilizce (global),
sohbet çok dilli.** Marka: **Humanitaria**. Şu an yerel geliştirme aşamasında.

## Mevcut Durum (çalışıyor)
- **Aktif config (.env):** `CHAT_LLM_PROVIDER=gemini`, `VECTOR_STORE_PROVIDER=pinecone`, `EMBED_PROVIDER=gemini`,
  `QUERY_LLM_PROVIDER=gemini` → **tamamen bulut, Ollama gerekmez**.
- **Chat LLM:** Gemini `gemini-2.5-flash`. System prompt İngilizce; yanıt kullanıcının dilinde. Rule 9 = recency.
- **Embedding:** Gemini `gemini-embedding-001` (3072-dim). **Vector DB:** Pinecone `reliefweb-docs` (31.508 vektör).
- **Retrieval:** güncellik-farkında + alaka reranker'ı (truncate=END ile) çalışıyor. Config: `RECENCY_RERANK_POOL=10`, `RECENCY_BOOST_FACTOR=0.6`.
- **Backend:** FastAPI, **port 8010**. SSE streaming. Kod değişikliğinden sonra sunucuyu restart et (`--reload` yok).
- **Frontend:** Vue 3, Humanitaria (yeşil/antrasit, dark+light), İngilizce. `frontend/dist/` gitignore'da (`npm run build`).
- **Test:** 278 backend + 51 frontend.

## Veri Durumu
- **Pinecone `reliefweb-docs`: 31.508 vektör (3072-dim).** Kaynak url'leri `/node/{id}` (200).
- IRN/TUR/UKR/SYR/IRQ derin + 10 öneri ülkesi. Yalnız `reports` endpoint.
- Daha fazla veri: `python scripts/ingest.py --limit N` (`--force` KULLANMA; idempotent upsert).

## Önemli Komutlar
| İş | Komut |
|----|-------|
| Sunucu başlat | `./venv/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8010` |
| Frontend build | `cd frontend && npm run build` |
| Backend testleri | `./venv/Scripts/python.exe -m pytest tests/ -q` |
| Frontend testleri | `cd frontend && npm test -- --run` |
| RAG eval (freshness) | `./venv/Scripts/python.exe scripts/eval_rag.py` |
| RAG eval (judge) | `./venv/Scripts/python.exe scripts/eval_rag.py --judge` |

> **Bash gotcha:** kabuk cwd kalıcı; her git/komutta önce `cd "C:/Projeler/Reliefweb_RAG_System"` (mutlak). `cd frontend` sonrası geri dönmeyi unutma.

## Commit / Push Durumu
- Recency feature + önceki iş (toplam ~22 commit) **`origin/master`'a PUSH'LANDI** (2026-06-02).
- **Reranker fix `e4624b2` + MEMORY güncellemesi: lokal commit'li, PUSH durumu için seans sonuna bak.**
- Remote: **https://github.com/berkcansuner/reliefweb-rag** (private).

## Sıradaki Adımlar (Faz 2 devamı — kullanıcı yönlendirir)
- [ ] **Recency yeniden ayarı (öne çıktı):** Reranker artık çalıştığından alaka güçlendi; Ukraine "latest" 501g.
      `RECENCY_BOOST_FACTOR`/`RECENCY_RERANK_POOL` (veya recency'yi aday havuzunda relevance'tan ÖNCE uygulama) eval ile ince ayar.
- [ ] `eval_rag.py --judge` ile yanıt kalitesi (groundedness/relevance) önce/sonra ölçümü.
- [ ] Diğer Faz 2 eksenleri: hibrit (keyword+vektör) arama; sorgu anlama; kaynak snippet/önizleme.
- [ ] (Büyük/ayrı) chunk boyutunu küçült + re-ingest (retrieval hassasiyeti + reranker tam görüş).
- [ ] (Opsiyonel) büyük-harf Türkçe geçmiş-niyeti.
- [ ] (Deploy öncesi) Conversation endpoint'lerinde kullanıcı modeli/IDOR; conv rate-limit; CORS daraltma.

## Bilinen Sorunlar / Kısıtlamalar
- Chunk boyutu 800 KELİME (büyük): reranker truncate=END ile yalnız ilk ~1024 token'ı görür; retrieval hassasiyeti seyrek. Küçültmek re-ingest gerektirir.
- Conversation endpoint'lerinde gerçek kullanıcı modeli/auth YOK → IDOR (yerel tek-kullanıcıda sorun değil, deploy öncesi şart).
- Şablon/sistem mesajları (greeting, no-docs, clarification) İngilizce; yalnız LLM yanıtı çok dilli (bilinçli ayrım).
- Session history varsayılan in-memory (restart'ta silinir); `REDIS_URL` ile kalıcı.
- Pipeline resume kısmi: scheduler watermark var ama uzun kesinti tam test edilmedi.
