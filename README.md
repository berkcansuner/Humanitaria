# ReliefWeb RAG Sistemi

ReliefWeb insani yardım veritabanı üzerinden Türkçe/İngilizce çok dilli sohbet yapılabilen RAG (Retrieval-Augmented Generation) sistemidir.

## Mimari

```
ReliefWeb API → Ingestion Pipeline → ChromaDB (yerel dosya)
                                            ↓
Kullanıcı → Vue 3 Frontend → FastAPI (localhost:8000) → RAG Engine (LangChain) → Ollama Cloud LLM
                                                              ↑
                                          Yerel Ollama (embedding, localhost:11434)
```

## Kurulum

1. Gerekli Python sürümü: 3.12
2. Sanal ortam oluşturun:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/macOS
   ```
3. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
4. `.env.example` dosyasını `.env` olarak kopyalayın ve kendi değerlerinizi girin:
   ```bash
   cp .env.example .env
   ```
5. Yerel Ollama sunucusunu başlatın ve embedding modelini çekin:
   ```bash
   ollama pull qwen3-embedding:8b
   ollama serve
   ```
6. Frontend bağımlılıklarını yükleyin ve build edin:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

## Çalıştırma

- Backend + Frontend'i başlatmak için:
  ```bash
  python -m uvicorn api.main:app --reload
  ```
  Tarayıcıda `http://localhost:8000` adresine gidin.

- Veri çekmek için:
  ```bash
  python scripts/ingest.py --limit 1000 --endpoints reports disasters countries
  ```
  Seçenekler: `--force` (koleksiyonu temizle), `--date-from YYYY-MM-DD` (sadece belirli tarihten sonraki belgeler)

## Dizin Yapısı

```
.
├── config.py            # Pydantic ayarları
├── requirements.txt     # Python bağımlılıkları
├── .env.example         # Ortam değişkenleri şablonu
├── api/                 # FastAPI uygulaması
│   ├── main.py          # Uygulama giriş noktası
│   └── routes/          # API route'ları (chat, health)
├── frontend/            # Vue 3 SPA
│   ├── src/             # Kaynak kodlar
│   └── dist/            # Build edilmiş production bundle
├── ingestion/           # ReliefWeb'den veri çekme, parse etme
├── rag/                 # Embedding, retriever, LangChain zinciri
├── scripts/             # CLI komutları (ingest.py)
├── tests/               # pytest testleri
└── chroma_db/            # ChromaDB verileri (gitignore'da)
```