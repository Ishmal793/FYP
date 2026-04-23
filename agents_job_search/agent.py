import os
import time
import requests
from urllib.parse import urlparse, parse_qs, unquote
from .models import JobResult
from langchain_groq import ChatGroq


def heal_url(raw_link: str) -> str:
    if not raw_link:
        return ""
    if "google.com/url" in raw_link:
        params_parsed = parse_qs(urlparse(raw_link).query)
        return unquote(params_parsed.get("q", [raw_link])[0])
    return raw_link


def scrape_job_description(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            for tag in soup(["script", "style"]):
                tag.decompose()
            for selector in [
                {"class": lambda c: c and any(x in " ".join(c).lower() for x in ["job-desc", "jobdescription", "job_desc", "jobsearch-jobdescriptiontext", "show-more-less-html"])},
                {"id": lambda i: i and any(x in i.lower() for x in ["job-desc", "description"])},
            ]:
                el = soup.find(["div", "section"], selector)
                if el:
                    text = el.get_text(separator=" ", strip=True)
                    if len(text) > 100:
                        return text[:3000]
            for tag in ["main", "article"]:
                el = soup.find(tag)
                if el:
                    text = el.get_text(separator=" ", strip=True)
                    if len(text) > 100:
                        return text[:3000]
    except Exception as e:
        print(f"[DEBUG] Scraping failed for {url}: {e}")
    return ""


def generate_missing_jd(title: str, company: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        try:
            llm = ChatGroq(api_key=api_key, model_name="llama-3.1-8b-instant", temperature=0.3)
            prompt = f"""Write a concise professional job description for '{title}' at '{company}'.
Include: job summary (2 sentences), key responsibilities (3-4 bullets), required skills (3-4 bullets).
Output plain text only, no placeholders."""
            response = llm.invoke(prompt)
            if response.content and len(response.content) > 50:
                return response.content
        except Exception as e:
            print(f"[DEBUG] LLM generation failed: {e}")

    return (
        f"Job Title: {title}\nCompany: {company}\n\n"
        f"We are looking for a skilled {title} to join {company}.\n\n"
        f"Key Responsibilities:\n"
        f"- Perform core duties related to {title}\n"
        f"- Collaborate with cross-functional teams\n"
        f"- Deliver high-quality results aligned with business goals\n"
        f"- Analyze and report on key metrics\n\n"
        f"Required Skills:\n"
        f"- Relevant technical skills for {title}\n"
        f"- Strong communication and problem-solving abilities\n"
        f"- Attention to detail and analytical thinking"
    )


def is_valid_job(title: str, company: str, description: str) -> bool:
    if not title or not company:
        return False
    desc_lower = str(description).lower()
    if len(desc_lower) < 50:
        return False
    spam_keywords = ["scam", "get rich quick", "pyramid scheme", "investment required", "multi-level marketing", "mlm"]
    if any(spam in desc_lower for spam in spam_keywords):
        return False
    return True


def extract_description(job: dict, link: str, job_title: str, company: str) -> tuple:
    description = ""
    is_generated = False

    # 1. job_highlights — SerpAPI mein aksar description se zyada reliable
    highlights = job.get("job_highlights", [])
    if highlights:
        highlight_text = []
        for h in highlights:
            items = h.get("items", [])
            if items:
                highlight_text.append(f"{h.get('title', '')}:")
                highlight_text.extend(items)
        joined = "\n".join(highlight_text)
        if len(joined) > 50:
            description = joined

    # 2. description field
    if not description:
        raw_desc = job.get("description", "")
        if len(str(raw_desc)) > 50:
            description = raw_desc

    # 3. snippet field
    if not description:
        snippet = job.get("snippet", "")
        if len(str(snippet)) > 50:
            description = snippet

    # 4. Scrape apply URL
    if not description and link:
        print(f"[DEBUG] Scraping: {link}")
        description = scrape_job_description(link)

    # 5. LLM / static fallback — NEVER empty
    if not description or len(str(description)) < 50:
        print(f"[DEBUG] Generating fallback JD for: {job_title}")
        description = generate_missing_jd(job_title, company)
        is_generated = True

    return description, is_generated


def fetch_jobs_from_serpapi(titles: list, location: str, job_type: str = "", time_filter: str = "", user=None, resume=None) -> dict:
    api_key = os.environ.get("SERPAPI_API_KEY")
    serp_url = "https://serpapi.com/search.json"

    all_jobs = []
    seen_links = set()
    api_failed = False

    if api_key:
        for title in titles[:2]:
            query = f"{title} in {location}"
            if job_type and job_type.lower() == "remote":
                query += " Remote"

            params = {
                "engine": "google_jobs",
                "q": query,
                "hl": "en",
                "api_key": api_key,
            }

            if time_filter:
                if "today" in time_filter.lower():
                    params["chips"] = "date_posted:today"
                elif "3 days" in time_filter.lower():
                    params["chips"] = "date_posted:3days"
                elif "week" in time_filter.lower():
                    params["chips"] = "date_posted:week"

            try:
                print(f"[DEBUG] SerpAPI query: {query}")
                response = requests.get(serp_url, params=params, timeout=10)

                if response.status_code == 429:
                    print("[DEBUG] SerpAPI rate limit hit.")
                    break

                response.raise_for_status()
                data = response.json()
                jobs = data.get("jobs_results", [])
                print(f"[DEBUG] SerpAPI returned {len(jobs)} jobs for '{title}'")

                for job in jobs:
                    job_title = job.get("title", "Unknown Title")
                    company = job.get("company_name", "Unknown Company")

                    # DEBUG — keys check
                    print(f"[DEBUG] Processing: {job_title} | keys: {list(job.keys())}")

                    # ── LINK EXTRACTION (FIXED) ──────────────────────────
                    link = ""
                    apply_options = job.get("apply_options", [])
                    if apply_options:
                        raw_link = apply_options[0].get("link", "")
                        link = heal_url(raw_link)
                        print(f"[DEBUG] apply_options link: {link}")

                    if not link:
                        link = heal_url(job.get("share_link", ""))

                    if not link and job.get("related_links"):
                        link = heal_url(job["related_links"][0].get("link", ""))

                    if not link:
                        print(f"[DEBUG] No link found for: {job_title}")

                    # Deduplicate
                    if link and link in seen_links:
                        continue
                    if link:
                        seen_links.add(link)

                    # ── LOCATION (FIXED) ─────────────────────────────────
                    job_location = job.get("location", "").strip()
                    if not job_location or job_location.lower() in ["anywhere", "remote", ""]:
                        job_location = location

                    # ── DESCRIPTION (FIXED) ──────────────────────────────
                    description, is_generated = extract_description(job, link, job_title, company)

                    # Validate
                    if not is_valid_job(job_title, company, description):
                        print(f"[DEBUG] Invalid job skipped: {job_title}")
                        continue

                    all_jobs.append({
                        "title": job_title,
                        "company": company,
                        "location": job_location,
                        "description": description,
                        "apply_link": link,
                        "is_valid_description": len(description.strip()) > 100,
                    })

                    if len(all_jobs) >= 8:
                        break

                time.sleep(0.5)
                if len(all_jobs) >= 8:
                    break

            except Exception as e:
                print(f"[DEBUG] SerpAPI error: {e}")
                api_failed = True
                break
    else:
        print("[DEBUG] No SERPAPI_API_KEY found.")
        api_failed = True

    # ── FALLBACK ─────────────────────────────────────────────────────────
    warning = None
    if len(all_jobs) == 0:
        print("[DEBUG] 0 jobs — trying DB cache.")
        if user and resume:
            cached = JobResult.objects.filter(user=user, resume=resume).order_by('-match_score')[:8]
            if cached.exists():
                all_jobs = [{"title": c.title, "company": c.company, "location": c.location,
                             "description": c.description, "apply_link": c.apply_link, 
                             "is_valid_description": len(c.description.strip()) > 100} for c in cached]
            else:
                warning = "No jobs found. Try different location, time range, or role."
        else:
            warning = "No jobs found. Try different location, time range, or role."
    elif len(all_jobs) < 6:
        warning = "Low job availability for this role/location."

    return {"jobs": all_jobs[:8], "warning": warning}
    print(f"[DEBUG] description value: '{str(job.get('description', ''))[:200]}'")