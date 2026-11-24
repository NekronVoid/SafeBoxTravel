import os
import httpx
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print("Token:", bool(token), "| Chat ID:", chat_id)

url = f"https://api.telegram.org/bot{token}/sendMessage"
resp = httpx.post(url, json={"chat_id": chat_id, "text": "Prueba directa desde Python"})
print("Status:", resp.status_code)
print("Respuesta:", resp.text)