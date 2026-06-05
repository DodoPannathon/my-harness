import urllib.request, json, os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("URLS").split(',')[0]

req = urllib.request.Request(
    f"{url}/api/tags"
)

with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print("Models:", [m["name"] for m in data["models"]])