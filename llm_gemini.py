from langchain_google_genai import ChatGoogleGenerativeAI
import os


def query_gemini(
    prompt: str,
    retries: int = 10,
) -> str:
    llm = ChatGoogleGenerativeAI(model=os.environ.get("GEMINI_MODEL"))
    result = llm.invoke(prompt)
    return result.content

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(override=True)
    print(query_gemini("hello world!"))