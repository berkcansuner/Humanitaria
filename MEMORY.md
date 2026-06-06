# MEMORY — ReliefWeb RAG (oturum sürekliliği)

> **Her oturum başında bu dosyayı oku. Her önemli ilerlemeden sonra güncelle.**
> Bu bir tarihçe değil — GÜNCEL durumu yansıtır. Eskiyen satırları sil/değiştir.
> "Nerede kalmıştık?" sorusunun cevabı burasıdır.

**Son güncelleme:** 2026-06-06

---

## 🎯 SONRAKİ SEANS — Rollout TIKANDI (Pinecone aylık write-unit kotası doldu); v2 8/10 ülke hazır+doğrulandı

Tüm-ülke rollout başlatıldı (3 yıl, 10 ülke, ülke-başı **en yeni 2000 cap**, yeni **`v2` namespace**).
**8 ülke başarıyla v2'ye yazıldı (68.936 vektör) + 8-ülke A/B ile kalite DOĞRULANDI (GO):** granülarite
kesin kazanım (ort. chunk 479 vs default 3070 char → reranker tam görüyor), freshness 160g vs 445g, judge 5.0=5.0.
AMA son 2 ülke (**Palestine kısmi, Ukraine 0**) yazılamadı: **Pinecone AYLIK write-unit kotası (2.000.000) doldu**
(hata gövdesi: "reached your write unit limit for the current month"). Sabit kota — retry/backoff çare değil. Bkz. [[run-gotchas]].

**v2 EKSİK: 8/10 ülke.** Cutover YAPILMADI (eksik v2'ye geçersek default'taki Ukrayna+Filistin kaybolur → regresyon).
**Veri kaybı yok:** default 31.628 + pilot 4.892 + v2 68.936 sağlam, izole.

**Kota çözülmeden ilerlenemez — kullanıcı kararı bekliyor:**
1. **Aylık reset bekle** (gelecek fatura döngüsü) → PSE+UKR tamamla → cutover. Bu arada app default'ta (çalışıyor).
2. **Pinecone planını yükselt** → PSE+UKR hemen tamamla → cutover.
Cutover = `PINECONE_NAMESPACE=v2` (config/.env) + commit/push; eski default rollback olarak TUT; pilot+kısmi-eski namespace'ler temizlenebilir (kullanıcı onayı).

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
- **Backend:** FastAPI, port `.env`'deki `API_PORT`. SSE streaming. Kod değişikliğinden sonra restart (`--reload` yok).
- **Frontend:** Vue 3, Humanitaria (yeşil/antrasit, dark+light), İngilizce. `frontend/dist/` gitignore'da.
- **Test:** **271 backend** + 51 frontend yeşil. Judge groundedness 5.0/5, relevance ~4.9-5.0/5 (judge doygun/varyanslı).

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
- **`origin/master`'a PUSH'LANDI:** pilot (`e2c0e7d`,`c23963f`,`79d61f1`,`01f6d4d`,`2139951`,`5ab02a0`) + store 429-retry fix (`918637d`). Master = origin/master.
- Remote: **https://github.com/berkcansuner/reliefweb-rag** (private).

## Sıradaki Adımlar (kullanıcı yönlendirir)
- [ ] **Kotayı çöz** (aylık reset bekle VEYA Pinecone plan upgrade) → `PINECONE_NAMESPACE=v2 ingest --country PSE UKR --date-from 2023-06-05 --limit 2000` ile v2'yi tamamla.
- [ ] v2 tamla → **CUTOVER:** `PINECONE_NAMESPACE=v2` (config default + .env) commit/push → app v2'ye geçer. Eski default rollback olarak TUT; pilot namespace temizle.
- [ ] (Karar) "pilot" + (cutover sonrası) eski default namespace temizliği.
- [ ] Diğer Faz 2 eksenleri: hibrit (keyword+vektör) arama; kaynak snippet/önizleme.
- [ ] (Deploy öncesi) Conversation endpoint'lerinde kullanıcı modeli/IDOR; conv rate-limit; CORS daraltma.

## Bilinen Sorunlar / Kısıtlamalar
- **Pinecone aylık write-unit kotası (2M):** rollout bunu doldurdu → yeni yazma 429 ("write unit limit for the current month"). Sabit kota; retry çare değil. Reset/plan-upgrade gerek. Büyük ingest planlarken hesaba kat.
- **Karışık chunk durumu:** chunker yeni default (~1500 char) ama mevcut default-namespace verisi hâlâ eski 800-kelime — cutover'a kadar böyle. Yeni ingest'ler yeni chunk üretir.
- 1-yıl ingest penceresi tarihsel büyük olayları kaçırır (deprem) → rollout'ta ≥2-3 yıl.
- Conversation endpoint'lerinde gerçek auth YOK → IDOR (yerel tek-kullanıcıda sorun değil, deploy öncesi şart).
- Şablon/sistem mesajları (greeting, no-docs) İngilizce; yalnız LLM yanıtı çok dilli (bilinçli).
- Session history varsayılan in-memory (restart'ta silinir); `REDIS_URL` ile kalıcı.
- Görseller/infografikler doğrudan sorgulanamaz (246 Suriye raporu boş body → atlandı).
