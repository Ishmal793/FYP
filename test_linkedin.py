import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

search_key = "Data Analyst Python SQL"
location = "Remote"
url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(search_key)}&location={quote_plus(location)}"
print("URL:", url)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}
res = requests.get(url, headers=headers)
print("Status:", res.status_code)
soup = BeautifulSoup(res.text, "html.parser")
jobs = soup.find_all("div", class_="base-card")
print("Found jobs:", len(jobs))
for job in jobs[:2]:
    title_el = job.find("h3", class_="base-search-card__title")
    title = title_el.text.strip() if title_el else "No Title"
    link_el = job.find("a", class_="base-card__full-link")
    link = link_el["href"] if link_el else ""
    print("Title:", title)
    print("Link:", link)
