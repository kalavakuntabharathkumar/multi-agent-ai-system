import os
import warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

_QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template=(
        "Use the following document excerpts to answer the question. "
        "If the answer is not contained in the document, say 'I don't know'.\n\n"
        "Context:\n{context}\n\n"
        "Question: {question}\n\n"
        "Answer:"
    ),
)


def answer_from_document(document_text: str, question: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    docs = [Document(page_content=document_text)]
    vectorstore = FAISS.from_documents(docs, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.2,
        max_tokens=500,
        openai_api_key=api_key,
    )
    parser = StrOutputParser()

    def format_docs(retrieved_docs):
        return "\n\n".join(d.page_content for d in retrieved_docs)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | _QA_PROMPT
        | llm
        | parser
    )

    try:
        return chain.invoke(question)
    except Exception as exc:
        return f"Document QA failed: {exc}"
