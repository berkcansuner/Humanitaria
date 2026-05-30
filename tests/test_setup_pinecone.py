import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _settings():
    s = MagicMock()
    s.PINECONE_API_KEY = "k"
    s.PINECONE_INDEX = "reliefweb-docs"
    s.PINECONE_CLOUD = "aws"
    s.PINECONE_REGION = "us-east-1"
    s.EMBED_DIM = 3072
    return s


def test_creates_index_when_absent():
    from scripts.setup_pinecone import create_index
    with patch("scripts.setup_pinecone.get_settings", return_value=_settings()), \
         patch("scripts.setup_pinecone.Pinecone") as MockPC, \
         patch("scripts.setup_pinecone.ServerlessSpec") as MockSpec:
        pc = MagicMock()
        pc.list_indexes.return_value = []
        MockPC.return_value = pc
        create_index()
        pc.create_index.assert_called_once()
        kwargs = pc.create_index.call_args[1]
        assert kwargs["name"] == "reliefweb-docs"
        assert kwargs["dimension"] == 3072
        assert kwargs["metric"] == "cosine"


def test_skips_when_index_exists():
    from scripts.setup_pinecone import create_index
    existing = MagicMock()
    existing.name = "reliefweb-docs"
    with patch("scripts.setup_pinecone.get_settings", return_value=_settings()), \
         patch("scripts.setup_pinecone.Pinecone") as MockPC, \
         patch("scripts.setup_pinecone.ServerlessSpec"):
        pc = MagicMock()
        pc.list_indexes.return_value = [existing]
        MockPC.return_value = pc
        create_index()
        pc.create_index.assert_not_called()
