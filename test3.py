import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('API_KEY')

def test_break(n):
 print(f"{api_key} {n}")
 if n>=5:
  break

n=0
while True:
 test_break(n)
 n+=1