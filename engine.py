import os
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.messages import AIMessage, AIMessageChunk, ToolMessage
from dotenv import dotenv_values
from langchain.messages import AIMessageChunk

root_path = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(root_path, '.env')

class Engine:
    def __init__(self, agent):
        self.agent = agent
        self.messages = []

    async def stream_turn(self, text: str):
        self.messages.append({"role": "user", "content": text})

        final_state = None
        async for mode, payload in self.agent.astream(
            {"messages": self.messages},
            stream_mode=["messages", "values"],
        ):
            if mode == "messages":
                chunk, _meta = payload
                if isinstance(chunk, AIMessageChunk) and chunk.text:
                    yield chunk.text
            else:
                final_state = payload

        if final_state is not None:
            self.messages = final_state["messages"]

    def reset(self):
        self.messages = []

def create_engine() -> Engine:
    env = dotenv_values(env_path)

    if not env:
        raise RuntimeError(f".env non trovato in {env_path}")

    llm_base_url = env["LLM_BASE_URL"]
    llm_api_key = env["LLM_API_KEY"]
    llm_model = env["LLM_MODEL"]

    llm = ChatOpenAI(
        base_url=llm_base_url,
        api_key=llm_api_key,
        model=llm_model,
        temperature=0.1
    )

    agent = create_agent(
        model=llm,
        tools=[],
        system_prompt="You are a helpful assistant"
    )

    return Engine(agent)

