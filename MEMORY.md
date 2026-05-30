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
- **Backend:** FastAPI, **port 8000** (.env'de `API_PORT` yok → config default 8000; bu oturumda 8000'de sorunsuz çalıştı). SSE streaming. Başlangıçta lifespan warmup + ingestion scheduler.
- **Frontend:** Vue 3, `frontend/dist/` build edilmiş, FastAPI statik serve ediyor.
- **Test:** **205 backend (pytest) + 11 frontend (vitest), hepsi yeşil.**

## Veri Durumu
- **Pinecone `reliefweb-docs`: 866 vektör (3072-dim).** Uçtan uca retrieval + tarih filtresi doğrulandı (Sudan sorguları 5 kaynak dönüyor).
- Veri hâlâ az — kapsamlı sohbet için daha fazlası faydalı olur (opsiyonel, kritik değil).
- Daha fazla veri çek: `python scripts/ingest.py --limit N` (`--force` KULLANMA; idempotent upsert tekrarı önler).
- (Eski yerel ChromaDB `./chroma_db/` artık aktif store değil; provider chroma'ya dönülürse kullanılır.)

## Önemli Komutlar
| İş | Komut |
|----|-------|
| Sunucu başlat | `./venv/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000` |
| Veri çek | `python scripts/ingest.py --limit N` |
| Backend testleri | `./venv/Scripts/python.exe -m pytest tests/ -q` |
| Frontend build | `cd frontend && npm run build` |
| Frontend testleri | `cd frontend && npm test -- --run` |

## ⚠️ COMMIT EDİLMEMİŞ DEĞİŞİKLİKLER (bu oturum — branch `master`)
Bu oturumda yapılan iki düzeltme henüz commit edilmedi (kullanıcı isteğiyle bekliyor):
1. **`rag/query_processor.py` + `tests/test_rag_query_processor.py`** — query-processor merge fix (aşağıda).
2. **`frontend/src/components/Chat.vue`** (+ rebuild edilmiş `frontend/dist/`) — input UX fix (aşağıda).
- `server.log` çalışan sunucunun log dosyası (untracked, .gitignore'a eklenebilir).
- Not: `App.vue`, `style.css`, `renderMarkdown.js`, `package-lock.json` bu oturum ÖNCESİNDEN modifiye durumdaydı (bana ait değil).

## Sıradaki Adımlar
1. [ ] **Commit kararı:** yukarıdaki 2 düzeltmeyi commit et (conventional commit, İngilizce). Önerilen:
   `fix(query): merge rule-based extractor as backstop and reclassify country-as-source`
   ve `fix(frontend): keep chat input editable during streaming`.
2. [ ] (Opsiyonel) Stale warmup düzeltmesi: `api/main.py` lifespan warmup'ı `OllamaLangChainEmbeddings`'i hardcode ediyor → `rag.embeddings.get_embeddings()` factory'sine çevir (yanıltıcı 4096≠3072 log'unu ve gereksiz Ollama bağımlılığını giderir).
3. [ ] (Opsiyonel) Daha fazla veri toplama — `ingest.py --limit` artır; çoklu endpoint (`--endpoints reports disasters countries`).
4. [ ] (Opsiyonel) `RunnableWithMessageHistory` → LangGraph migrasyonu (4 deprecation uyarısı).

## Bilinen Sorunlar / Açık İşler
- **`requirements.txt` çakışması:** `pip install -r requirements.txt` başarısız (chromadb 1.0.5 → fastapi==0.115.9 ister, ama pin 0.115.0). Tüm requirements'ı kurma; eksik paketleri tek tek kur. Bu oturumda venv'e eksik paketler kuruldu: `langchain-chroma==0.2.4`, `langchain-pinecone==0.2.13`, `apscheduler==3.10.4` (chromadb otomatik 1.5.9 oldu).
- **Stale warmup:** lifespan warmup Gemini provider'da yanıltıcı dim-mismatch uyarısı veriyor (kritik değil; gerçek istekler `get_embeddings()` factory kullanıyor). Bkz. Sıradaki Adımlar #2.
- Query processor modeli çok küçük (`qwen2.5:0.5b`); merge fix sonrası rule-based backstop güvenilirliği artırdı ama harita-dışı ülke/kaynak için sınırlı.
- **Gemini API anahtarı geçmişte sohbete yazıldı → Google AI Studio'dan rotate edilmeli.**
- CORS production için daraltılmalı (şu an localhost origin'leri, `.env` `CORS_ORIGINS`).
- Pipeline resume kısmi: scheduler watermark (`chroma_db/.last_ingest.json`) var ama uzun kesinti tam test edilmedi.

## Son Oturum Özeti (2026-05-30)
Sistem `master` üzerinde çalıştırıldı (Pinecone+Gemini config, port 8000). venv güncel değildi →
eksik paketler kuruldu (yukarı bak). İki bug bulundu ve düzeltildi (commit EDİLMEDİ):

1. **Query-processor misclassification fix** (`rag/query_processor.py`): Mimari "LLM-first, sadece
   exception'da rule-based fallback" idi; `qwen2.5:0.5b` tutarsız — "Sudan"ı `source`'a koyuyor ya da
   `{}` dönüyordu → başarılı-ama-boş/yanlış LLM çıktısı güvenilir rule-based'i baypaslıyor, retrieval 0
   sonuç. Fix: (a) `extract_filters` artık rule-based'i **backstop merge** ediyor (`{**rule, **llm}` —
   LLM çakışmada kazanır, rule-based curated country/theme/doctype/date boşluklarını doldurur);
   (b) yeni `_as_known_country` ile `_normalize_llm_filters` `source`'a düşen bilinen ülkeyi `country`'ye
   taşıyor. 5 yeni test eklendi; 205/205 backend test geçiyor. Canlı doğrulandı (Sudan sorguları 0→5 kaynak).
2. **Frontend chat input UX fix** (`frontend/src/components/Chat.vue`): Mesaj gönderince input focus'u
   kaybediyordu. Önce refocus eklendi (`ref="chatInput"` + `nextTick(focus)`), sonra kullanıcı isteğiyle
   input'tan `:disabled="loading"` kaldırıldı → artık yanıt akarken bir sonraki soru yazılabiliyor (send
   butonu disable kalıyor, `sendMessage` loading guard'ı çift gönderimi engelliyor). Gerçek Chrome (CDP) ile
   doğrulandı; frontend 11/11 test geçiyor; `frontend/dist/` rebuild edildi.
