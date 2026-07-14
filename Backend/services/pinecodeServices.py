from services.transcriptService import get_raw_transcript, get_trans
from pinecone import Pinecone
from db.connection import client
from dotenv import load_dotenv
import os
load_dotenv()
from pinecone import ServerlessSpec
pc = Pinecone(api_key=os.getenv("PINE_CONE_DB_API_KEY"))


pc_index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
collection = client["quizDB"]["pineconeCollection"]


print("Index from env:", repr(os.getenv("PINECONE_INDEX_NAME")))
print("Indexes:", pc.list_indexes().names())

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore

from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

vectorstore = PineconeVectorStore(
    index=pc_index,
    embedding=embeddings
)

def getresultfromPinecodeDB(video_id,user_question):
    retriever = vectorstore.as_retriever(
        search_kwargs={
            "k": 5,
            "filter": {
                "video_id": video_id
            }
        }
    )
    docs = retriever.invoke(user_question)
    return docs


def generateAndStoreEmbeddings(video_id):
    # Fetch the raw transcript for the given video ID
    transcript = get_trans(video_id)
    if transcript is None:
        print(f"Failed to fetch transcript for video ID: {video_id}. Embedding generation aborted.")
        # save a record that transcript not found for the video ID in the pineconeCollection
        collection.insert_one({"video_id": video_id, "transcript_found": False})
        return {"message": "Failed to fetch transcript. Embedding generation aborted."}
    
    else:
        documents = [
            Document(
                page_content=item["text"],
                metadata={
                    "video_id": video_id,
                    "start": item["start"],
                    "end": item["end"],
                },
            )
            for item in transcript
        ]

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )

        chunks = splitter.split_documents(documents)

        vectorstore.add_documents(chunks)

        collection.insert_one({"video_id": video_id, "transcript_found": True})
        return {"message": "Embeddings generated and stored successfully."}