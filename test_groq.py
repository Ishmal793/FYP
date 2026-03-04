import os
from dotenv import load_dotenv
from groq import Groq

# Load .env file
load_dotenv(override=True)

api_key = os.environ.get("GROQ_API_KEY")
print(f"Loaded API Key: {api_key[:10]}...{api_key[-5:]}" if api_key else "No API key loaded")

try:
    client = Groq(api_key=api_key)

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "Explain the importance of fast language models",
            }
        ],
        model="llama-3.3-70b-versatile",
    )

    print("Success:")
    print(chat_completion.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")
