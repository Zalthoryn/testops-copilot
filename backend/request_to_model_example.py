import os

from openai import OpenAI

api_key="YTc5NDZhMTAtZjkwNi00OTlkLTgxM2QtOGNkZDUyYjAzOWY1.03eccda7c192ba2cbe8f5c94da06be64" # тянем из .env
url = "https://foundation-models.api.cloud.ru/v1"

client = OpenAI(
   api_key=api_key,
   base_url=url
)

response = client.chat.completions.create(
   model="openai/gpt-oss-120b",
   max_tokens=5000,
   temperature=0.5,
   presence_penalty=0,
   top_p=0.95,
   messages=[
      {
            "role": "user",
            "content":"Как написать хороший код?"
      }
   ]
)

print(response.choices[0].message.content)
