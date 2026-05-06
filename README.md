# ReliefWeb RAG Sistemi

ReliefWeb insani yardım veritabanı üzerinden Türkçe/İngilizce çok dilli sohbet yapılabilen RAG (Retrieval-Augmented Generation) sistemidir.

## Mimari

```
ReliefWeb API → Ingestion Pipeline → ChromaDB (yerel dosya)
                                            ↓
Kullanıcı → Chainlit UI (localhost:8000) → RAG Engine (LangChain) → Ollama Cloud LLM
                                                   ↑
                               Yerel Ollama (embedding, localhost:11434)
```

## Kurulum

1. Gerekli Python sürümü: 3.12
2. Sanal ortam oluşturun:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/macOS
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

## Çalıştırma

- Uygulamayı başlatmak için:
  ```bash
  chainlit run chainlit_app.py
  ```
- Veri çekmek için:
  ```bash
  python scripts/ingest.py
  ```

## Dizin Yapısı

```
.
├── chainlit_app.py      # Chainlit giriş noktası
├── config.py            # Pydantic ayarları
├── requirements.txt     # Python bağımlılıkları
├── .env.example         # Ortam değişkenleri şablonu
├── scripts/
│   └── ingest.py        # ReliefWeb ingestion CLI
├── ingestion/           # Veri çekme ve parse etme
├── rag/                 # Embedding, retriever, LangChain zinciri
├── tests/               # pytest testleri
└── chroma_db/           # ChromaDB verileri (gitignore'da)
```
