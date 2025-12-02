import glob
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, OllamaLLM



docs = []
#load dococument

for file in glob.glob("./docs/*"):
    if file.endswith(".pfg"):
        docs.extend(PyPDFLoader(file).load())
    else:
        docs.extend(TextLoader(file).load())


# slpit in to chunks
spiltter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
chunks = spiltter.split_documents(docs)
embeddings = OllamaEmbeddings(model="nomic-embed-text")


# store chunks in chromaDB
db = Chroma.from_documents(chunks, embedding=embeddings, persist_directory='db')

llm = OllamaLLM(model="llama3:latest")

def ask(query):
    results = db.similarity_search(query, k=5)
    context = "\n\n".join([doc.page_content for doc in results])
    prompt = f"""
    Use the following context if it is useful, but you may also answer with your own knowledge.
    Context:
    {context}
    Question: {query}
    Answer:
    """
    return llm.invoke(prompt)


print(ask("Who is the primeminister of nepal"))