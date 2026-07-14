from dotenv import load_dotenv
from langchain_groq import ChatGroq
import json
import tiktoken

load_dotenv()

llm = ChatGroq(
    model="qwen/qwen3-32b",
    temperature=0,
    max_tokens=None,
    reasoning_format="parsed",
    timeout=None,
    max_retries=2,
    # other params...
)

import tiktoken


def count_tokens(text):
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def generate_quiz(transcript):
    """
    transcript format:
    [
        {
            "text": "...",
            "start": 0,
            "end": 12.5
        }
    ]
    """

    transcript_text = json.dumps(transcript, indent=2)

    system_prompt = """
    You are an expert educational quiz generator.

    Your task is to create high-quality multiple-choice questions from a video transcript.

    IMPORTANT GUARDRAILS:
    1. Generate quizzes ONLY if the video is educational.
    2. Educational content includes:
    - Programming
    - Science
    - Mathematics
    - History
    - Geography
    - Engineering
    - Technology
    - Business
    - Finance
    - Language learning
    - Tutorials
    - Academic subjects

    3. Do NOT generate quizzes for:
    - Music videos
    - Vlogs
    - Podcasts
    - Comedy
    - Entertainment
    - Gaming streams
    - Memes
    - Reactions
    - Movies
    - Sports highlights

    If the content is not educational, return:

    {
        "is_educational": false,
        "reason": "Short reason",
        "quiz": []
    }

    If it is educational, return in below JSON Scehema:

    {
        "is_educational": true,
        "reason": null,
        "quiz": [
            {
                "question": "...",
                "options": [
                    "...",
                    "...",
                    "...",
                    "..."
                ],
                "correct_answer": "...",
                "explanation": "...",
                "start_time": 12.3,
                "end_time": 25.7
            }
        ]
    }

    RULES:
    - Generate 1 question per major concept.
    - Maximum 10 questions.
    - Exactly 4 options.
    - Only one correct answer.
    - Explanation should be short (1-2 sentences).
    - Questions must be answerable from the transcript.
    - Use the corresponding timestamps from the transcript.
    - Return ONLY valid JSON.
    - Do NOT use markdown.
    - Do NOT wrap JSON in ``` blocks.
    """

    human_prompt = f"""
    Generate quiz questions from this transcript:

    {transcript_text}
    """

    transcrit_count = count_tokens(transcript_text)
    system_prompt_count = count_tokens(system_prompt)

    print(f"Transcript tokens: {transcrit_count}")
    print(f"System prompt tokens: {system_prompt_count}")

    if transcrit_count + system_prompt_count > 6000:
        return {
            "is_educational": False,
            "reason": "Transcript too long to process",
            "quiz": []
        }

    # trim the transcript if it exceeds the token limit
    if transcrit_count + system_prompt_count > 5500:
        transcript_text = transcript_text[:5500 - system_prompt_count]

    response = llm.invoke([
        ("system", system_prompt),
        ("human", human_prompt),
    ])

    return json.loads(response.content)


def answer_query(embeddings, user_question):
    # Convert embeddings to a format suitable for the LLM
    embeddings_text = [doc.dict() for doc in embeddings]

    system_prompt = """
    You are an expert educational assistant.

    Your task is to answer user questions based on the provided video transcript embeddings.

    IMPORTANT:
    - Use the embeddings to find relevant information.
    - If the answer is not in the embeddings, respond with "I don't know."
    - Provide concise and accurate answers.
    - if embedding is in some different language, answer in a language the user asked question.
    """

    human_prompt = f"""
    Answer the following question based on the provided transcript embeddings:

    Embeddings:
    {embeddings_text}

    User Question:
    {user_question}
    """

    response = llm.invoke([
        ("system", system_prompt),
        ("human", human_prompt),
    ])

    return response.content