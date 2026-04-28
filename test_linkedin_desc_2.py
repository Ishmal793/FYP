import requests
from bs4 import BeautifulSoup

def test_desc(link):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    res = requests.get(link, headers=headers)
    print(f"Status: {res.status_code}")
    soup = BeautifulSoup(res.text, "html.parser")
    desc_div = soup.find("div", class_="show-more-less-html__markup")
    if desc_div:
        print("Found show-more-less-html__markup")
        print(desc_div.get_text()[:100])
    else:
        print("Did NOT find show-more-less-html__markup")
        alt = soup.find("div", class_="description__text")
        if alt:
            print("Found description__text")
        else:
            print("Did not find description__text either. Writing HTML to file for inspection.")
            with open("linkedin_job_test.html", "w", encoding="utf-8") as f:
                f.write(res.text)

if __name__ == "__main__":
    # A generic linkedin job url. I'll search for one or just use one of the ones the user provided before.
    link = "https://www.linkedin.com/jobs/view/4405235287"
    test_desc(link)
