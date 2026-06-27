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
- **Kimlik doğrulama:** httpOnly cookie session — e-posta/şifre + opsiyonel Google OAuth.
- **Tamamen bulut** — yerel model sunucusu gerektirmez.

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
   `RELIEFWEB_APPNAME` (ReliefWeb API). Kimlik doğrulama e-posta/şifre ile kutudan çıktığı gibi
   çalışır; production için `AUTH_SESSION_SECRET`'i değiştirin (bkz. Kimlik Doğrulama bölümü).
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

## Kimlik Doğrulama

Chat endpoint'leri (`/chat`, `/chat/stream`) oturum açmayı gerektirir; istek bir oturum
cookie'si taşımıyorsa **401** döner. İki yöntem desteklenir:

- **E-posta / şifre** — kutudan çıktığı gibi çalışır, ek kurulum gerekmez
  (`POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`).
- **Google OAuth (opsiyonel)** — `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` boşsa
  `GET /auth/google/login` `503` döner. Etkinleştirmek için Google Cloud Console'da bir
  OAuth 2.0 Client ID oluşturun ve yetkili callback URI'yi `GOOGLE_REDIRECT_URI` ile eşitleyin.

Oturum, httpOnly cookie'de tutulan opak bir token'dır (SQLite'ta hash'li saklanır).

**Production:** `AUTH_SESSION_SECRET`'i uzun, rastgele bir değerle değiştirin ve HTTPS
arkasında `SESSION_COOKIE_SECURE=True` yapın.

## Dizin Yapısı

```
.
├── config.py            # Pydantic ayarları
├── requirements.txt     # Python bağımlılıkları
├── .env.example         # Ortam değişkenleri şablonu
├── api/                 # FastAPI uygulaması
│   ├── main.py          # Uygulama giriş noktası
│   └── routes/          # API route'ları (auth, chat, conversations, health)
├── frontend/            # Vue 3 SPA
│   ├── src/             # Kaynak kodlar
│   └── dist/            # Build edilmiş production bundle (gitignore'da)
├── ingestion/           # ReliefWeb'den veri çekme, parse, chunk, store
├── rag/                 # Embedding, retriever, LangChain zinciri, query processor
├── scripts/             # CLI komutları (ingest.py, setup_pinecone.py, eval_rag.py, prune_old_vectors.py)
├── tests/               # pytest testleri
└── conversations.db     # Sohbet geçmişi (SQLite; gitignore'da)
```

## Deployment

Canlı dağıtım adımları (Render + OAuth ortam değişkenleri) için `DEPLOY.md`'ye bakın.
