# MEMORY — ReliefWeb RAG (oturum sürekliliği)

> **Her oturum başında bu dosyayı oku. Her önemli ilerlemeden sonra güncelle.**
> Bu bir tarihçe değil — GÜNCEL durumu yansıtır. Eskiyen satırları sil/değiştir.
> "Nerede kalmıştık?" sorusunun cevabı burasıdır.

**Son güncelleme:** 2026-06-01

---

## 🎯 SIRADAKİ SEANS — Faz 2: RAG Kalitesi (kullanıcı "kaldığım yerden devam" dedi)
**Amaç:** Kullanıcıların sorduğu sorularda istedikleri sonuca ulaşması — retrieval + yanıt kalitesini artır.
Kullanıcı bunu Faz 2 olarak istedi (Faz 1 = İngilizce çeviri TAMAMLANDI).

**İlk adım:** Kullanıcıya **somut sorun/örnek sor** (alakasız kaynak mı, eksik bilgi mi, yanlış filtre mi),
sonra `eval_rag.py --judge` ile ölç → hedefli iyileştir → tekrar ölç (önce/sonra kıyas).

**Olası eksenler (kullanıcı yönlendirecek):**
- **Retrieval:** `TOP_K_RETRIEVAL`/MMR (`MMR_FETCH_K`,`MMR_LAMBDA`) ayarı; hosted reranker'ı her zaman aç
  (şu an iki-aşamalı `_retrieve_docs`'ta var); hibrit (keyword+vektör) arama; kaynak snippet/önizleme.
- **Sorgu anlama:** filtre çıkarma kalitesi (ülke/tema/tarih); eşanlamlı genişletme; belirsiz sorguda
  netleştirme akışı (zaten `analyze_query` + SuggestionCard var).
- **Yanıt:** daha sıkı groundedness; "yeterli kaynak yoksa söyle"; follow-up/çok-adımlı bağlam.
- **Ölçüm:** `python scripts/eval_rag.py --judge` (groundedness/relevance 1-5, Gemini). Son temel: 5.00/5.00.

---

## ✅ Bu seansta tamamlanan iş (2026-06-01) — hepsi working tree'de, COMMIT EDİLMEDİ
Plan dosyası: `C:\Users\bcsun\.claude\plans\witty-riding-wirth.md` (son hali İngilizce çeviri planı).

1. **Source-link 404 fix + backfill.** `parse_report` linki artık `url_alias→url→/node/{id}` (doc_id sentetik
   kanonikten — idempotency korundu); `client.py` reports field'larına `url`/`url_alias` eklendi.
   `scripts/backfill_source_urls.py` (yeni) mevcut **31.508 Pinecone vektörünün** metadata url'ini
   `/report/{id}`→`/node/{id}` yaptı (**0 hata**). Kaynak linkleri artık **HTTP 200**. (Eski `/report/{id}` 404 veriyordu.)
2. **Tier-1 doğruluk fix'leri** (kapsamlı kod denetimi sonrası, hepsi TDD):
   A1 `client.py` 5xx retry (backoff); A2 `pipeline.py` orphan-delete artık embed BAŞARILIYSA;
   A3 `Chat.vue` truncate-hatası `planResend` guard (saf helper, ayrışma yok); A4 `main.py` CORS `X-API-Key`.
3. **Humanitaria redesign (frontend).** Yeşil+antrasit palet, `HelpingHandLogo.vue`, topbar marka+alt başlık,
   sidebar arama+tarih grupları (Today/This week/Older)+avatar footer, EmptyState, yeşil `[n]` atıf çipleri.
   React prototip → mevcut Vue'ya taşındı (yapı korundu). Export: `Desktop/Reliefweb_RAG_System_FRONTEND_CHANGE`.
4. **İngilizce çeviri (Faz 1).** UI **sadece İngilizce** (hard-convert, i18n yok); sohbet **ÇOK DİLLİ KORUNDU**
   (system prompt İngilizce yazıldı ama "answer in the user's language" kuralı kalıyor → TR soru=TR yanıt, EN=EN).
   Frontend ~42 string + backend mesajları (greeting, no-docs, clarifications, "New chat", "Untitled") İngilizce.
   Türkçe GİRDİ desteği (greeting pattern, query_processor kelime eşlemeleri) korundu.

**Test:** **260 backend + 51 frontend yeşil.** Canlı doğrulandı (EN→EN, TR→TR, greeting EN, UI EN).

---

## Hedef
İnsani yardım M&E ekibi için ReliefWeb belgeleri üzerinden RAG sohbet sistemi. **UI İngilizce (global),
sohbet çok dilli.** Marka: **Humanitaria**. Şu an yerel geliştirme aşamasında.

## Mevcut Durum (çalışıyor)
- **Aktif config (.env):** `CHAT_LLM_PROVIDER=gemini`, `VECTOR_STORE_PROVIDER=pinecone`, `EMBED_PROVIDER=gemini`,
  `QUERY_LLM_PROVIDER=gemini` → **tamamen bulut, Ollama gerekmez**.
- **Chat LLM:** Gemini `gemini-2.5-flash`. **System prompt İngilizce; yanıt kullanıcının dilinde.**
- **Embedding:** Gemini `gemini-embedding-001` (3072-dim). **Vector DB:** Pinecone `reliefweb-docs` (31.508 vektör).
- **Backend:** FastAPI, **port 8010** (8000'i RState_ai tutuyor). SSE streaming. Sunucu komutu için tabloya bak.
  > Backend kod değişikliğinden sonra **sunucuyu restart et** (uvicorn `--reload` yok; eski kodu hafızada tutar).
- **Frontend:** Vue 3, Humanitaria redesign (yeşil/antrasit, dark+light), İngilizce. `frontend/dist/` gitignore'da
  — yerelde `npm run build` ile üretilir. SourceList linkleri `/node/{id}` (çalışıyor).
- **Test:** 260 backend (pytest) + 51 frontend (vitest).

## Veri Durumu
- **Pinecone `reliefweb-docs`: 31.508 vektör (3072-dim).** Kaynak url'leri `/node/{id}` (backfill ile düzeltildi, 200).
- IRN/TUR/UKR/SYR/IRQ derin kapsamlı (~4-5 bin rapor/ülke) + 10 öneri ülkesi. Yalnız `reports` endpoint.
- Daha fazla veri: `python scripts/ingest.py --limit N` (`--force` KULLANMA; idempotent upsert).

## Önemli Komutlar
| İş | Komut |
|----|-------|
| Sunucu başlat | `./venv/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8010` |
| Frontend build | `cd frontend && npm run build` |
| Backend testleri | `./venv/Scripts/python.exe -m pytest tests/ -q` |
| Frontend testleri | `cd frontend && npm test -- --run` |
| RAG eval (judge) | `./venv/Scripts/python.exe scripts/eval_rag.py --judge` |
| URL backfill (gerekirse) | `./venv/Scripts/python.exe -u scripts/backfill_source_urls.py --apply` |

## Commit / Push Durumu (ÖNEMLİ)
- **Bu seansın TÜM işi commit EDİLMEDİ** — working tree'de duruyor (yukarıdaki 4 blok).
- Ek olarak **önceki seanstan 9 commit `origin/master` önünde, push EDİLMEDİ** (claude.ai-tarzı özellikler).
- Remote: **https://github.com/berkcansuner/reliefweb-rag** (private). Kullanıcı onayıyla mantıklı commit'lere
  bölünüp push edilecek — kendiliğinden push etme.

## Sıradaki Adımlar
- [ ] **Faz 2: RAG kalitesi** (yukarıdaki "🎯 SIRADAKİ SEANS" bölümü) — kullanıcı somut sorun/örnek verecek.
- [ ] (Kullanıcı isteyince) Bu seansın işini commit'le + push.
- [ ] (Deploy öncesi, denetimden) Conversation endpoint'lerinde kullanıcı modeli/IDOR; conv rate-limit; CORS daraltma.
- [ ] (Opsiyonel, denetimden D1-D3) embedding dim her batch doğrula; disaster/country doc_id stabilitesi;
      scheduler watermark `date.changed` ile güncelleme algılama.

## Bilinen Sorunlar / Kısıtlamalar
- Conversation endpoint'lerinde gerçek kullanıcı modeli/auth YOK → IDOR (yerel tek-kullanıcıda sorun değil, deploy öncesi şart).
- Şablon/sistem mesajları (greeting, no-docs, clarification) İngilizce; yalnız LLM yanıtı çok dilli (bilinçli ayrım).
- Session history varsayılan in-memory (restart'ta silinir); `REDIS_URL` ile kalıcı.
- Gemini query json_mode bazen liste döndürüyor (validator coerce ediyor; sorun değil).
- Pipeline resume kısmi: scheduler watermark var ama uzun kesinti tam test edilmedi.
