from langchain_anthropic import ChatAnthropic
import phoenix as px
from phoenix.trace.langchain import LangChainInstrumentor

LangChainInstrumentor().instrument()

def query_anthropic(system_promot, user_prompt):

    llm = ChatAnthropic(model='claude-3-opus-20240229')

    messages = [
    (
        "system",
        system_promot,
    ),
        ("human", user_prompt),
    ]
    ai_msg = llm.invoke(messages)
    return ai_msg.content

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(override=True)
    print(query_anthropic("hello world!", "hello world!"))