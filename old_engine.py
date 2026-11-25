from dotenv import load_dotenv, dotenv_values
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.messages import AIMessage, AIMessageChunk, ToolMessage

if not load_dotenv():
    print("Failed to load .env file")
    quit()


config = dotenv_values(".env")
llm_base_url = config["LLM_BASE_URL"]
llm_api_key = config["LLM_API_KEY"]
llm_model = config["LLM_MODEL"]
llm_model_provider = config["LLM_MODEL_PROVIDER"]

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

llm = ChatOpenAI(
    base_url=llm_base_url,
    api_key=llm_api_key,
    model=llm_model,
    temperature=0.1
)

agent = create_agent(
    model=llm,
    tools=[get_weather],
    system_prompt="You are a helpful assistant"
)

messages = []
try:
    while True:
        try:
            text = input(">> ").strip()
        except:
            break

        if not text:
            continue

        if text in ("quit", "exit"):
            print("Bye!")
            quit()

        if text == "clear":
            messages = []
            print("Storia azzerata")
            continue

        messages.append({
            "role": "user",
            "content": text
        })

        final_state = None
        shown = 0

        for mode, payload in agent.stream(
            {"messages": messages},
            stream_mode = ["messages", "values"]
        ):
            
            if mode == "messages":
                chunk, meta = payload
                if isinstance(chunk, AIMessageChunk):
                    if chunk.text:
                        print(chunk.text, end="", flush=True)
                    for tc in chunk.tool_call_chunks:
                        if tc.get("name"):
                            print(f"\n[tool] {tc['name']}...", end="", flush=True)
            else:
                final_state = payload
                for msg in payload["messages"][shown:]:
                    shown += 1
                    if isinstance(msg, AIMessage) and msg.tool_calls:
                        for tc in msg.tool_calls:
                            print(f"\n[tool call] {tc['name']}({tc['args']})")
                    elif isinstance(msg, ToolMessage):
                        print(f"\n[tool result] {msg.content}")

        print()
        messages = final_state["messages"]

except KeyboardInterrupt:
    pass

print("\nBye!")