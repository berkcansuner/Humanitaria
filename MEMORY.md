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
- **Kaynaklar (citation-grounded):** Yanıt context belgelerine satır içi `[n]` atıfı verir; `sources` event'i yalnızca atıf verilen belgeleri döndürür (atıf yoksa fallback: tümü). Prompt artık kaynakları metin içinde isimlendirmiyor — sadece altta `SOURCES (N)` kompakt liste (`[n]` numaralı).
- **Öneriler:** Belirsiz sorgularda yanıttan SONRA **React island** öneri kartı (Claude tarzı, 1/N: ülke→zaman→konu). Seçenekler **yan yana sarmalanan çipler** (uzun dikey liste yok) + **serbest metin girişi** (kullanıcı kendi cevabını yazıp Enter/→ ile gönderebilir). İlerleme noktaları, klavye (Tab/Enter, Esc kapatır), CSS animasyon+reduced-motion, ARIA radiogroup, "Atla". `react/SuggestionCard.jsx`(+`.css`) + `SuggestionCardIsland.vue` (Vue↔React köprüsü); seçimler birikir, son adımda sorgu zenginleşip yeniden gönderilir. SSE sırası: token → sources → clarification.
- **Test:** **212 backend (pytest) + 11 frontend (vitest), hepsi yeşil.**

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

## Remote / Push
- Remote: **https://github.com/berkcansuner/reliefweb-rag** (private). `origin/master` güncel — her tur push ediliyor. (NOT: `RState_ai` farklı bir proje, ona dokunulmadı.)

## Sıradaki Adımlar
1. [ ] (Opsiyonel) Stale warmup düzeltmesi: `api/main.py` lifespan warmup'ı `OllamaLangChainEmbeddings`'i hardcode ediyor → `rag.embeddings.get_embeddings()` factory'sine çevir (yanıltıcı 4096≠3072 log'unu ve gereksiz Ollama bağımlılığını giderir).
3. [ ] (Opsiyonel) Daha fazla veri toplama — `ingest.py --limit` artır; çoklu endpoint (`--endpoints reports disasters countries`).
4. [ ] (Opsiyonel) `RunnableWithMessageHistory` → LangGraph migrasyonu (4 deprecation uyarısı).

## Bilinen Sorunlar / Açık İşler
- **`requirements.txt` çakışması:** `pip install -r requirements.txt` başarısız (chromadb 1.0.5 → fastapi==0.115.9 ister, ama pin 0.115.0). Tüm requirements'ı kurma; eksik paketleri tek tek kur. Bu oturumda venv'e eksik paketler kuruldu: `langchain-chroma==0.2.4`, `langchain-pinecone==0.2.13`, `apscheduler==3.10.4` (chromadb otomatik 1.5.9 oldu).
- **Stale warmup:** lifespan warmup Gemini provider'da yanıltıcı dim-mismatch uyarısı veriyor (kritik değil; gerçek istekler `get_embeddings()` factory kullanıyor). Bkz. Sıradaki Adımlar #2.
- Query processor modeli çok küçük (`qwen2.5:0.5b`); merge fix sonrası rule-based backstop güvenilirliği artırdı ama harita-dışı ülke/kaynak için sınırlı.
- **Gemini API anahtarı geçmişte sohbete yazıldı → Google AI Studio'dan rotate edilmeli.**
- CORS production için daraltılmalı (şu an localhost origin'leri, `.env` `CORS_ORIGINS`).
- Pipeline resume kısmi: scheduler watermark (`chroma_db/.last_ingest.json`) var ama uzun kesinti tam test edilmedi.

## Son Oturum Özeti (2026-05-31)
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
