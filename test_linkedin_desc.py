import requests
from bs4 import BeautifulSoup

url = "https://in.linkedin.com/jobs/view/data-analyst-stata-remote-at-crossing-hurdles-4403960305?position=1&pageNum=0&refId=y1VAq6gDzALOzUy0oX6n0A%3D%3D&trackingId=8FlUaL7SV3Z0QjBHBF2XQQ%3D%3D"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
res = requests.get(url, headers=headers)
print("Status:", res.status_code)
soup = BeautifulSoup(res.text, "html.parser")
desc = soup.find("div", class_="show-more-less-html__markup")
if desc:
    print("Description length:", len(desc.text))
    print(desc.text.strip()[:200])
else:
    print("Description not found")
