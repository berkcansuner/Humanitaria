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

**Test:** **277 backend (pytest) + 51 frontend (vitest) yeşil.** Spec/plan: `docs/superpowers/{specs,plans}/2026-06-01-recency-aware-retrieval*` (gitignore'da, yerel).

### ⚠️ Açık taşınan notlar (kullanıcıya iletildi, henüz YAPILMADI)
1. **`rerank_by_relevance` Pinecone reranker 1024-token sınırını aşıp başarısız oluyor** → MMR sırasına düşüyor.
   Feature'dan önce de vardı. Düzeltilirse (chunk'ı reranker'a göndermeden önce kısaltma) alaka sinyali güçlenir,
   Ukraine gibi sorgular daha da iyileşir. **Faz 2'nin en yüksek getirili sıradaki adımı.**
2. **Büyük-harf Türkçe** geçmiş sorgusu ("NASIL GELİŞTİ") boost-off'u kaçırır (`_turkish_lower` noktalı/noktasız `i`).
   Düşük etki, mevcut rule-based davranışıyla tutarlı.

---

## Hedef
İnsani yardım M&E ekibi için ReliefWeb belgeleri üzerinden RAG sohbet sistemi. **UI İngilizce (global),
sohbet çok dilli.** Marka: **Humanitaria**. Şu an yerel geliştirme aşamasında.

## Mevcut Durum (çalışıyor)
- **Aktif config (.env):** `CHAT_LLM_PROVIDER=gemini`, `VECTOR_STORE_PROVIDER=pinecone`, `EMBED_PROVIDER=gemini`,
  `QUERY_LLM_PROVIDER=gemini` → **tamamen bulut, Ollama gerekmez**.
- **Chat LLM:** Gemini `gemini-2.5-flash`. System prompt İngilizce; yanıt kullanıcının dilinde. Rule 9 = recency.
- **Embedding:** Gemini `gemini-embedding-001` (3072-dim). **Vector DB:** Pinecone `reliefweb-docs` (31.508 vektör).
- **Retrieval:** güncellik-farkında (yukarı bak). Yeni config: `RECENCY_RERANK_POOL=10`, `RECENCY_BOOST_FACTOR=0.6`.
- **Backend:** FastAPI, **port 8010**. SSE streaming. Kod değişikliğinden sonra sunucuyu restart et (`--reload` yok).
- **Frontend:** Vue 3, Humanitaria (yeşil/antrasit, dark+light), İngilizce. `frontend/dist/` gitignore'da (`npm run build`).
- **Test:** 277 backend + 51 frontend.

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
- **2026-06-02:** Bu seansın tüm işi (önceki 5 + recency 7 commit) ve önceki seanstan 9 commit **`origin/master`'a PUSH'LANDI**.
- Remote: **https://github.com/berkcansuner/reliefweb-rag** (private).

## Sıradaki Adımlar (Faz 2 devamı — kullanıcı yönlendirir)
- [ ] **Reranker token-limit fix** (yukarıdaki not #1) — Pinecone reranker'a giden chunk'ları kısalt; en yüksek getiri.
- [ ] Diğer Faz 2 eksenleri: hibrit (keyword+vektör) arama; sorgu anlama (eşanlamlı genişletme, netleştirme); kaynak snippet/önizleme.
- [ ] (Opsiyonel) recency parametre ayarı: Ukraine hâlâ medyan 260g → `RECENCY_BOOST_FACTOR`/`RECENCY_RERANK_POOL` eval ile ince ayar.
- [ ] (Opsiyonel) büyük-harf Türkçe geçmiş-niyeti (not #2).
- [ ] (Deploy öncesi) Conversation endpoint'lerinde kullanıcı modeli/IDOR; conv rate-limit; CORS daraltma.

## Bilinen Sorunlar / Kısıtlamalar
- `rerank_by_relevance` reranker 1024-token sınırı → bazı sorgularda MMR'a düşüyor (bkz. not #1).
- Conversation endpoint'lerinde gerçek kullanıcı modeli/auth YOK → IDOR (yerel tek-kullanıcıda sorun değil, deploy öncesi şart).
- Şablon/sistem mesajları (greeting, no-docs, clarification) İngilizce; yalnız LLM yanıtı çok dilli (bilinçli ayrım).
- Session history varsayılan in-memory (restart'ta silinir); `REDIS_URL` ile kalıcı.
- Pipeline resume kısmi: scheduler watermark var ama uzun kesinti tam test edilmedi.
