from langchain.memory import ConversationBufferWindowMemory


def build_memory() -> ConversationBufferWindowMemory:
    return ConversationBufferWindowMemory(k=5, return_messages=True, memory_key="chat_history")
