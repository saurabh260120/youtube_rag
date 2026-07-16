from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import tiktoken
from utility.logger import log

load_dotenv()

# ---------------------------------------------------------------------------
# Model fallback configuration
# ---------------------------------------------------------------------------
# Each entry is a tuple: (name, callable that returns a BaseChatModel instance)
def _groq_qwen():
    return ChatGroq(
        model="qwen/qwen3-32b",
        temperature=0,
        max_tokens=None,
        reasoning_format="parsed",
        timeout=None,
        max_retries=2,
    )


def _groq_llama():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )


def _openai_gpt4o_mini():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )


def _gemini_flash():
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )


# Ordered list of fallback models – first one that initialises successfully is used.
_MODEL_FALLBACKS = [
    ("Groq Qwen 32B", _groq_qwen),
    ("Groq Llama 3.3 70B", _groq_llama),
    ("OpenAI GPT-4o-mini", _openai_gpt4o_mini),
    ("Gemini 2.0 Flash", _gemini_flash),
]


def _init_llm():
    """Try each model in order and return the first one that works."""
    for name, factory in _MODEL_FALLBACKS:
        try:
            instance = factory()
            # Quick validation call (just to catch auth / network errors early)
            log(f"_init_llm: Successfully initialised {name}")
            return instance, name
        except Exception as e:
            log(f"_init_llm: Failed to initialise {name}: {e}")
            continue

    raise RuntimeError("All LLM backends failed to initialise – no model available.")


llm, _active_model_name = _init_llm()
log(f"llm.py: Active model = {_active_model_name}")


def count_tokens(text):
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def _invoke_with_fallback(system_prompt, human_prompt, max_retries=2):
    """
    Invoke the LLM with automatic fallback to the next model on failure.
    Tries each model in the fallback chain up to `max_retries` times per model.
    """
    global llm, _active_model_name

    models_to_try = list(_MODEL_FALLBACKS)

    # Start with the currently active model
    start_idx = 0
    for i, (name, _) in enumerate(models_to_try):
        if name == _active_model_name:
            start_idx = i
            break

    last_error = None

    for offset in range(len(models_to_try)):
        idx = (start_idx + offset) % len(models_to_try)
        name, factory = models_to_try[idx]

        for attempt in range(max_retries):
            try:
                # Re-initialise if we switched models
                if name != _active_model_name:
                    llm = factory()
                    _active_model_name = name
                    log(f"_invoke_with_fallback: Switched to {name}")

                response = llm.invoke([
                    ("system", system_prompt),
                    ("human", human_prompt),
                ])
                return response
            except Exception as e:
                last_error = e
                log(f"_invoke_with_fallback: {name} attempt {attempt + 1}/{max_retries} failed: {e}")
                continue

        log(f"_invoke_with_fallback: {name} exhausted all retries, trying next model...")

    raise RuntimeError(f"All LLM backends exhausted. Last error: {last_error}")


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

    log(f"generate_quiz: Transcript tokens={transcrit_count}, System prompt tokens={system_prompt_count}")

    if transcrit_count + system_prompt_count > 6000:
        return {
            "is_educational": False,
            "reason": "Transcript too long to process",
            "quiz": []
        }

    # trim the transcript if it exceeds the token limit
    if transcrit_count + system_prompt_count > 5500:
        transcript_text = transcript_text[:5500 - system_prompt_count]

    response = _invoke_with_fallback(system_prompt, human_prompt)

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

    response = _invoke_with_fallback(system_prompt, human_prompt)

    return response.content