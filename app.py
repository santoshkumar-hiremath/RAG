import streamlit as st
import faiss
import json
import numpy as np
import subprocess
from sentence_transformers import SentenceTransformer

# --- Config ---
OLLAMA_MODEL = "llama3:latest"

st.set_page_config(page_title="HPE RAG Assistant", page_icon="🏢")
st.title("🏢 HPE Wiki & Document AI")

@st.cache_resource
def load_data():
    model = SentenceTransformer("all-MiniLM-L6-v2")
    index = faiss.read_index("combined_index.faiss")
    with open("metadata.json", "r") as f:
        metadata = json.load(f)
    return model, index, metadata

try:
    model, index, metadata = load_data()
except:
    st.error("Index not found. Please run ingest.py first!")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Show history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Retrieval
    q_emb = model.encode([prompt]).astype('float32')
    D, I = index.search(q_emb, k=5)
    
    context = ""
    sources = set()
    for idx in I[0]:
        if idx != -1:
            context += f"\n---\n{metadata[idx]['text']}"
            sources.add(metadata[idx]['source'])

    # Answer
    with st.chat_message("assistant"):
        full_prompt = f"Use the context to answer. Context: {context}\n\nQuestion: {prompt}"
        res = subprocess.run(["ollama", "run", OLLAMA_MODEL, full_prompt], capture_output=True, text=True)
        answer = res.stdout.strip()
        st.markdown(answer)
        
        with st.expander("Sources Used"):
            for s in sources:
                st.write(f"- {s}")

    st.session_state.messages.append({"role": "assistant", "content": answer})
