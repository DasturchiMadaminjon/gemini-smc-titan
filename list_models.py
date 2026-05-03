import os
from google import genai

api_key = "AIzaSyAkProD9opDW7B2dupOc3xafbxbKpe1wvw"
client = genai.Client(api_key=api_key)
print("Available models for this key:")
try:
    for m in client.models.list():
        print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")
