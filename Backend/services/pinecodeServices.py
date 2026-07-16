from services.transcriptService import get_trans
from pinecone import Pinecone
from db.connection import client
from dotenv import load_dotenv
import os
from utility.logger import log
load_dotenv()
from pinecone import ServerlessSpec
pc = Pinecone(api_key=os.getenv("PINE_CONE_DB_API_KEY"))


pc_index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
collection = client["quizDB"]["pineconeCollection"]


log(f"Index from env: {repr(os.getenv('PINECONE_INDEX_NAME'))}")
log(f"Indexes: {pc.list_indexes().names()}")

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
    log(f"getresultfromPinecodeDB: Querying pinecone for video_id={video_id}, question='{user_question[:50]}...'")
    retriever = vectorstore.as_retriever(
        search_kwargs={
            "k": 5,
            "filter": {
                "video_id": video_id
            }
        }
    )
    docs = retriever.invoke(user_question)
    log(f"getresultfromPinecodeDB: Retrieved {len(docs)} documents for video_id={video_id}")
    return docs


def generateAndStoreEmbeddings(video_id):
    log(f"generateAndStoreEmbeddings: Starting embedding generation for video_id={video_id}")
    # Fetch the raw transcript for the given video ID
    transcript = get_trans(video_id)
    if transcript is None:
        log(f"generateAndStoreEmbeddings: Failed to fetch transcript for video_id={video_id}. Embedding generation aborted.")
        # save a record that transcript not found for the video ID in the pineconeCollection
        collection.insert_one({"video_id": video_id, "transcript_found": False})
        return {"message": "Failed to fetch transcript. Embedding generation aborted."}
    
    else:
        log(f"generateAndStoreEmbeddings: Transcript fetched for video_id={video_id}, creating documents...")
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
        log(f"generateAndStoreEmbeddings: Split into {len(chunks)} chunks for video_id={video_id}")

        vectorstore.add_documents(chunks)
        log(f"generateAndStoreEmbeddings: Embeddings stored in pinecone for video_id={video_id}")

        collection.insert_one({"video_id": video_id, "transcript_found": True})
        log(f"generateAndStoreEmbeddings: Database updated for video_id={video_id}")
        return {"message": "Embeddings generated and stored successfully."}


def generate_and_store_embeddings_from_transcript(video_id, transcript_segments):
    """
    Generate and store embeddings directly from a pre-parsed transcript (list of dicts).
    Used by the manual transcript fallback so it doesn't try to re-fetch the transcript.

    transcript_segments format:
        [{"text": "...", "start": float, "end": float}, ...]
    """
    log(f"generate_and_store_embeddings_from_transcript: Starting for video_id={video_id} with {len(transcript_segments) if transcript_segments else 0} segments")
    if not transcript_segments or len(transcript_segments) == 0:
        log(f"generate_and_store_embeddings_from_transcript: No transcript segments provided for video_id={video_id}. Aborting.")
        collection.insert_one({"video_id": video_id, "transcript_found": False})
        return {"message": "No transcript segments provided. Embedding generation aborted."}

    documents = [
        Document(
            page_content=item["text"],
            metadata={
                "video_id": video_id,
                "start": item["start"],
                "end": item["end"],
            },
        )
        for item in transcript_segments
    ]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    chunks = splitter.split_documents(documents)
    log(f"generate_and_store_embeddings_from_transcript: Split into {len(chunks)} chunks for video_id={video_id}")

    vectorstore.add_documents(chunks)
    log(f"generate_and_store_embeddings_from_transcript: Embeddings stored in pinecone for video_id={video_id}")

    collection.insert_one({"video_id": video_id, "transcript_found": True})
    log(f"generate_and_store_embeddings_from_transcript: Database updated for video_id={video_id}")
    return {"message": "Embeddings generated and stored successfully from manual transcript."}