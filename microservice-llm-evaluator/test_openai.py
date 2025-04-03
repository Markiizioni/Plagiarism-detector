from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Use the updated Chat Completions API
response = client.chat.completions.create(model="gpt-3.5-turbo",  # or "gpt-4" if you have access
messages=[
    {"role": "user", "content": "Say Hello World!"}
],
temperature=0)

# Print the result
print(response.choices[0].message.content.strip())
