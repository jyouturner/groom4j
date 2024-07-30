from langchain_anthropic import ChatAnthropic
import os
def query_anthropic(system_promot, user_prompt):

    llm = ChatAnthropic(
        model=os.environ.get("ANTHROPIC_MODEL"),
        temperature=0.0,
        max_decode_steps=40560,)

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