import asyncio
import os
import re
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv("backend/.env")

async def test():
    client = AsyncOpenAI(
        api_key=os.getenv("NEBIUS_TOKEN_FACTORY_API_KEY"),
        base_url=os.getenv("NEBIUS_TOKEN_FACTORY_BASE_URL"),
    )
    
    # Try different temperatures and prompt styles
    # Usually temperature=0.0 or 0.1 makes reasoning models much more concise
    prompts = [
        "Respond ONLY with a JSON object. No preamble, no explanation, no reasoning text. {"
    ]
    
    res = await client.chat.completions.create(
        model="nvidia/Nemotron-3_5-Lightning",
        messages=[
            {
                "role": "system",
                "content": "/no_thinking\nYou are a strict JSON API. You MUST output ONLY raw JSON starting with '{' and ending with '}'. Never explain your thoughts."
            },
            {
                "role": "user",
                "content": 'Analyze accessibility: <img src="hero.png" />. Output JSON {"has_violation": bool, "type": str}.'
            },
        ],
        temperature=0.0,
        max_tokens=1200,
    )
    print("RAW OUTPUT:")
    print(res.choices[0].message.content)
    print("USAGE:", res.usage)

if __name__ == "__main__":
    asyncio.run(test())
