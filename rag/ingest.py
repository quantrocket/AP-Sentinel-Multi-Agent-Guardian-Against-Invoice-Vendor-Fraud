"""
Builds/queries a Chroma vector store over the AP policy + playbook knowledge
base. Uses Gemini embeddings when GOOGLE_API_KEY is set, otherwise falls back
to a local sentence-transformer so the pipeline still runs for graders
without a key (Reasonableness Standard: no participant should be blocked
from reproducing results by a paid-only dependency).
"""
import os, glob, chromadb
from chromadb.utils import embedding_functions

PERSIST_DIR = "data/chroma"
COLLECTION = "ap_knowledge_base"


def _embedding_fn():
    if os.environ.get("GOOGLE_API_KEY"):
        return embedding_functions.GoogleGenerativeAiEmbeddingFunction(
            api_key=os.environ["GOOGLE_API_KEY"], model_name="models/text-embedding-004"
        )
    return embedding_functions.DefaultEmbeddingFunction()  # local, free, deterministic


def _chunk(text: str, size: int = 800, overlap: int = 100):
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + size])
        i += size - overlap
    return chunks


def build_index(kb_dir: str = "data/knowledge_base"):
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    coll = client.create_collection(COLLECTION, embedding_function=_embedding_fn())

    ids, docs, metas = [], [], []
    for path in glob.glob(os.path.join(kb_dir, "**/*.md"), recursive=True):
        text = open(path, encoding="utf-8").read()
        for j, chunk in enumerate(_chunk(text)):
            ids.append(f"{os.path.basename(path)}-{j}")
            docs.append(chunk)
            metas.append({"source": os.path.basename(path)})
    if docs:
        coll.add(ids=ids, documents=docs, metadatas=metas)
    print(f"Indexed {len(docs)} chunks into '{COLLECTION}'.")
    return coll


def get_retriever(top_k_default: int = 4):
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    coll = client.get_or_create_collection(COLLECTION, embedding_function=_embedding_fn())

    def retrieve(query: str, top_k: int = top_k_default):
        res = coll.query(query_texts=[query], n_results=top_k)
        out = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            out.append({"text": doc, "source": meta.get("source"), "score": 1 - dist})
        return out
    return retrieve


if __name__ == "__main__":
    build_index()
