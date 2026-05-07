import logging
import chainlit as cl
from config import get_settings
from rag.query_processor import extract_filters
from rag.chain import build_chain
from rag.memory import build_memory

logger = logging.getLogger(__name__)

def _parse_users(users_str: str):
    users = {}
    for pair in users_str.split(","):
        if ":" in pair:
            u, p = pair.split(":", 1)
            users[u.strip()] = p.strip()
    return users

@cl.password_auth_callback
def auth_callback(username: str, password: str):
    settings = get_settings()
    users = _parse_users(settings.CHAINLIT_USERS)
    if users.get(username) == password:
        return cl.User(identifier=username, metadata={"role": "user"})
    return None

@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("memory", build_memory())
    await cl.Message(content="Merhaba! ReliefWeb insani yardım belgeleri üzerinden sorularınızı yanıtlayabilirim.").send()

@cl.on_message
async def on_message(message: cl.Message):
    query = message.content
    filters = extract_filters(query)
    memory = cl.user_session.get("memory")
    chain = build_chain(filter=filters if filters else None, memory=memory)
    result = chain.invoke({"question": query})
    answer = result.get("answer", "")
    sources = result.get("source_documents", [])
    elements = []
    for i, doc in enumerate(sources[:3]):
        meta = doc.metadata
        url = meta.get("url", "")
        date = meta.get("date", "")
        title = meta.get("title", "")
        if url:
            elements.append(cl.Text(name=f"Kaynak {i+1}", content=f"{title} — {date}\n{url}", display="inline"))
    await cl.Message(content=answer, elements=elements).send()
