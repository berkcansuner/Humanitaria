# MEMORY — ReliefWeb RAG (oturum sürekliliği)

> **Her oturum başında bu dosyayı oku. Her önemli ilerlemeden sonra güncelle.**
> Bu bir tarihçe değil — GÜNCEL durumu yansıtır. Eskiyen satırları sil/değiştir.
> "Nerede kalmıştık?" sorusunun cevabı burasıdır.

**Son güncelleme:** 2026-05-29

---

## Hedef
İnsani yardım M&E ekibi için ReliefWeb belgeleri üzerinden Türkçe/İngilizce çok dilli RAG
sohbet sistemi. Şu an yerel geliştirme aşamasında.

## Mevcut Durum (çalışıyor)
- **Chat LLM:** Google Gemini `gemini-2.5-flash` — OpenAI-uyumlu endpoint üzerinden
  (`.env`: `CHAT_LLM_PROVIDER=gemini`). Akıcı Türkçe üretiyor. `gemini-2.5-pro`'ya veya
  `CHAT_LLM_PROVIDER=ollama`'ya `.env`'den geçilebilir.
- **Query processor** (filtre çıkarma): Ollama yerel (`qwen2.5:0.5b`) + rule-based fallback.
- **Embedding:** yerel Ollama `qwen3-embedding:8b` (4096-dim). DEĞİŞMEZ — ChromaDB bu boyutta.
- **Backend:** FastAPI, port **8001** (8000'de başka bir uygulama çalışıyor). SSE streaming.
  Başlangıçta embedding warmup + ingestion scheduler (lifespan) açılıyor.
- **Frontend:** Vue 3, `frontend/dist/` build edilmiş, FastAPI statik serve ediyor. Robot avatar yok.
- **Test:** ~172 backend (pytest) + 11 frontend (vitest), hepsi yeşil.

## Veri Durumu (KRİTİK — ana iş bu)
- **ChromaDB: 429 chunk, 71 ülke** (en son `--force` ile sıfırlanıp 500 rapor çekildi: 348 OK).
- Veri AZ — kapsamlı sohbet için çok daha fazlası gerekiyor. **Sıradaki ana iş bu.**
- Daha fazla veri çek:
  ```
  python scripts/ingest.py --limit 2000
  ```
  (~37 dk / 500 belge — embedding yerelde yavaş; büyük limitler uzun sürer, arka planda çalıştır)
- `--force` KULLANMA (mevcut veriyi siler); idempotent upsert zaten tekrarı önler.
- Ülke adları normalize ediliyor ("Iran (Islamic Republic of)" → retriever `$in` ile eşliyor).

## Önemli Komutlar
| İş | Komut |
|----|-------|
| Sunucu başlat | `python -m uvicorn api.main:app --host 127.0.0.1 --port 8001` |
| Veri çek | `python scripts/ingest.py --limit N` |
| Testler | `python -m pytest tests/ -q` |
| Frontend build | `cd frontend && npm run build` |
| Chat modeli değiştir | `.env` → `GEMINI_LLM_MODEL` (flash↔pro) / `CHAT_LLM_PROVIDER` (gemini↔ollama) |

## Sıradaki Adımlar (öncelik sırası)
1. [ ] **Daha fazla veri toplama** (ANA HEDEF) — `ingest.py --limit` artırarak kapsam genişlet
2. [ ] Çoklu endpoint ingestion (`--endpoints reports disasters countries`) ile çeşitlilik

## Bilinen Sorunlar / Açık İşler
- Pipeline resume kısmi: scheduler high-water-mark (`chroma_db/.last_ingest.json`) var ama
  uzun ingestion kesilirse tam resume test edilmedi.
- **Gemini API anahtarı sohbete yazıldı → Google AI Studio'dan rotate edilmeli.**
- CORS production için daraltılmalı (şu an localhost origin'leri, `.env` `CORS_ORIGINS`).
- Query processor modeli çok küçük (`qwen2.5:0.5b`); filtre kalitesi için büyütülebilir
  (kullanıcı şimdilik Ollama'da bırakmayı seçti).

## Son Oturum Özeti (2026-05-29)
Bu oturumda yapılanlar (tümü commit'li): kapsamlı kod incelemesi + düzeltmeler (doğruluk,
güvenlik, RAG kalitesi, ingestion), RunnableWithMessageHistory → düz LCEL, Gemini chat
entegrasyonu, tarih-filtresi yanlış pozitif düzeltmeleri, country adı normalizasyonu,
boş-sonuç mesajı, embedding warmup, LLM timeout 15s→5s. PROGRESS.md kaldırıldı, bu dosya
oturum sürekliliği için tek doğruluk kaynağı oldu. CLAUDE.md gerçek kodla senkronlanıp
sadeleştirildi (182 satır, operating-manual formatı).
