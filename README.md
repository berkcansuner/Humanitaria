# ReliefWeb RAG Sistemi

ReliefWeb insani yardım veritabanı üzerinden Türkçe/İngilizce çok dilli sohbet yapılabilen RAG
(Retrieval-Augmented Generation) sistemidir. Arayüz markası: **Humanitaria**.

## Mimari

```
ReliefWeb API → Ingestion Pipeline → Pinecone (serverless vektör DB)
                                            ↓
Kullanıcı → Vue 3 Frontend → FastAPI → RAG Engine (LangChain LCEL) → Google Gemini (chat yanıtı)
                                              ↑
                       Gemini embedding (gemini-embedding-001, 3072 boyut) + query processor
```

- **Chat & sorgu-işleme LLM'i:** Google Gemini (`gemini-2.5-flash`, OpenAI-uyumlu endpoint).
- **Embedding:** Google Gemini (`gemini-embedding-001`, 3072 boyut).
- **Vektör DB:** Pinecone serverless (`reliefweb-docs`).
- **Tamamen bulut** — yerel model sunucusu gerektirmez.

> **Opsiyonel alternatif sağlayıcılar:** yerel Ollama (embedding/LLM) ve ChromaDB, `config.py`
> flag'leriyle (`EMBED_PROVIDER`, `CHAT_LLM_PROVIDER`, `QUERY_LLM_PROVIDER`, `VECTOR_STORE_PROVIDER`)
> desteklenir. Varsayılan kurulum yukarıdaki bulut mimarisidir.

## Kurulum

1. Gerekli Python sürümü: 3.12
2. Sanal ortam oluşturun:
   ```bash
   python -m venv venv
   venv\Scripts\activate       # Windows
   source venv/bin/activate    # Linux/macOS
   ```
3. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
4. `.env.example` dosyasını `.env` olarak kopyalayın ve anahtarlarınızı girin:
   ```bash
   cp .env.example .env
   ```
   En az şunlar gerekir: `GEMINI_API_KEY` (chat + embedding), `PINECONE_API_KEY` (vektör DB),
   `RELIEFWEB_APPNAME` (ReliefWeb API).
5. Pinecone index'ini oluşturun:
   ```bash
   python scripts/setup_pinecone.py
   ```
6. Frontend bağımlılıklarını yükleyin ve build edin:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

## Çalıştırma

- Backend (Vue build'ini de sunar) başlatmak için:
  ```bash
  python -m uvicorn api.main:app
  ```
  Tarayıcıda `http://localhost:8000` adresine gidin (port `.env` içindeki `API_PORT` ile değiştirilebilir).

- Veri çekmek için:
  ```bash
  python scripts/ingest.py --limit 1000
  ```
  Seçenekler: `--endpoints reports disasters countries` (varsayılan `reports`),
  `--date-from YYYY-MM-DD` (yalnız belirli tarihten sonraki belgeler).
  Not: ingestion idempotent'tir; `--force` koleksiyonu temizler (dikkatli kullanın).

## Dizin Yapısı

```
.
├── config.py            # Pydantic ayarları (sağlayıcı flag'leri dahil)
├── requirements.txt     # Python bağımlılıkları
├── .env.example         # Ortam değişkenleri şablonu
├── api/                 # FastAPI uygulaması
│   ├── main.py          # Uygulama giriş noktası
│   └── routes/          # API route'ları (chat, conversations, health)
├── frontend/            # Vue 3 SPA
│   ├── src/             # Kaynak kodlar
│   └── dist/            # Build edilmiş production bundle (gitignore'da)
├── ingestion/           # ReliefWeb'den veri çekme, parse, chunk, store
├── rag/                 # Embedding, retriever, LangChain zinciri, query processor
├── scripts/             # CLI komutları (ingest.py, setup_pinecone.py, eval_rag.py)
├── tests/               # pytest testleri
├── chroma_db/           # ChromaDB verileri (yalnız chroma sağlayıcısında; gitignore'da)
└── conversations.db     # Sohbet geçmişi (SQLite; gitignore'da)
```
