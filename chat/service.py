import asyncio
import json
import aiohttp
async def stream_ollama(prompt: str, tone: str = "mean"):
    url = "http://localhost:11434/api/generate"
    # Compose an instruction that adjusts tone while enforcing basic safety constraints.
    # The instruction asks the model to be mean/curt/sarcastic depending on `tone`,
    # but forbids slurs, threats, or calls to violence.
    composed_prompt = (
        f"You are an assistant that should reply in a {tone} tone."
        " Be curt, sarcastic, and a bit rude if asked to be mean,"
        " but never use slurs, threats, or encourage harm."
        " Keep replies concise and directed at the user's message.\n\n"
        "User prompt:\n" + prompt
    )
    payload = {
        "model": 'llama3',
        'prompt': composed_prompt,
        'stream': True
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url,json=payload) as resp:
            async for line in resp.content:
                if line:
                    data = json.loads(line.decode("utf-8"))
                    yield data.get("response", "")


