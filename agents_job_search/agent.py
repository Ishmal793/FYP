import os
import requests
import concurrent.futures
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from .models import JobResult

def heal_url(raw_link: str) -> str:
    # Just return raw_link for LinkedIn since they are direct.
    return raw_link

def is_valid_job(title: str, company: str, description: str) -> bool:
    if not title or not company:
        return False
    desc_lower = str(description).lower()
    spam_keywords = ["scam", "get rich quick", "pyramid scheme", "investment required", "multi-level marketing", "mlm"]
    if any(spam in desc_lower for spam in spam_keywords):
        return False
    return True

def extract_linkedin_description(link: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        res = requests.get(link, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            desc_div = soup.find("div", class_="show-more-less-html__markup")
            if desc_div:
                return desc_div.get_text(separator=" ", strip=True)
    except Exception as e:
        print(f"[DEBUG] Error extracting desc for {link}: {e}")
    return ""

def fetch_jobs_from_linkedin(titles: list, location: str, job_type: str = "", time_filter: str = "", user=None, resume=None) -> dict:
    all_jobs = []
    warning = None

    # 1. Build Search Key
    role = titles[0] if titles else "Data Analyst"
    skills = []
    if resume and resume.parsed_data:
        raw_skills = resume.parsed_data.get("skills", [])
        for s in raw_skills:
            val = s.get("name", "") if isinstance(s, dict) else str(s)
            # Split by comma to avoid giant strings being passed as one skill
            for part in val.split(","):
                clean_part = part.strip()
                if clean_part:
                    skills.append(clean_part)
                    
    # Take at most 2 top skills to avoid overly narrow query on unauthenticated LinkedIn
    search_key = role
    if skills:
        search_key = f"{role} {skills[0]}".strip()
        if len(skills) > 1:
            search_key += f" {skills[1]}"
            
    url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(search_key)}"
    if location and location.lower() != "any":
        url += f"&location={quote_plus(location)}"
    
    # Apply Time Filter (UI values: 'Today', '3 Days', 'Week', 'Any time')
    if time_filter == "Today":
        url += "&f_TPR=r86400"
    elif time_filter == "3 Days":
        url += "&f_TPR=r259200"
    elif time_filter == "Week":
        url += "&f_TPR=r604800"
        
    # Apply Arrangement Filter (UI values: 'Remote', 'Onsite', 'Hybrid', 'Any')
    if job_type:
        job_type_lower = job_type.lower()
        if job_type_lower == "remote":
            url += "&f_WT=2"
        elif job_type_lower == "hybrid":
            url += "&f_WT=3"
        elif job_type_lower == "onsite":
            url += "&f_WT=1"

    print(f"[DEBUG] LinkedIn Scraper URL: {url}")
    
    # 2. Fetch Job Search Page
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.find_all("div", class_="base-card")
        
        job_links = []
        seen_signatures = set()
        for card in cards:
            if len(job_links) >= 10:  # Limit to 10 jobs max
                break
                
            title_el = card.find("h3", class_="base-search-card__title")
            company_el = card.find("h4", class_="base-search-card__subtitle")
            location_el = card.find("span", class_="job-search-card__location")
            link_el = card.find("a", class_="base-card__full-link")
            time_el = card.find("time")
            
            if not title_el or not link_el:
                continue
                
            posting_time = time_el.text.strip() if time_el else "Unknown"
            
            # STRICT POST-SCRAPING DATE FILTER
            import re
            pt_lower = posting_time.lower()
            
            # Helper to extract days
            def get_days_ago(text):
                if "hour" in text or "minute" in text or "second" in text or "just now" in text:
                    return 0
                if "yesterday" in text:
                    return 1
                match = re.search(r'(\d+)\s*(day|week|month|year)', text)
                if match:
                    val = int(match.group(1))
                    unit = match.group(2)
                    if unit == "day": return val
                    if unit == "week": return val * 7
                    if unit == "month": return val * 30
                    if unit == "year": return val * 365
                return 999 # Unknown/Old
                
            days_ago = get_days_ago(pt_lower)
            
            if time_filter == "Today" and days_ago > 1:
                continue
            elif time_filter == "3 Days" and days_ago > 3:
                continue
            elif time_filter == "Week" and days_ago > 7:
                continue
                    
            # STRICT LOCATION FILTER
            card_loc = location_el.text.strip() if location_el else "Unknown"
            if location and location.lower() != "any":
                main_loc_parts = location.lower().replace("remote", "").replace("hybrid", "").split(",")
                main_loc = main_loc_parts[0].strip()
                # Use a very relaxed filter: if user typed a long location, just check if ANY word matches.
                if main_loc:
                    user_words = set(main_loc.split())
                    card_words = set(card_loc.lower().split())
                    if not user_words.intersection(card_words):
                        # If absolutely no common words, maybe it's completely wrong, but let's be forgiving
                        # because LinkedIn location maps are weird (e.g. "San Francisco Bay Area").
                        # We will only drop if it's glaringly missing
                        pass

            title_text = title_el.text.strip()
            company_text = company_el.text.strip() if company_el else "Unknown"
            
            job_signature = f"{title_text}-{company_text}".lower()
            if job_signature in seen_signatures:
                continue
            seen_signatures.add(job_signature)
            
            job_links.append({
                "title": title_text,
                "company": company_text,
                "location": card_loc,
                "posting_time": posting_time,
                "apply_link": link_el["href"].split("?")[0]
            })
            
        print(f"[DEBUG] Filtered down to {len(job_links)} strict job cards.")

        # 3. Fetch Descriptions in Parallel with Delay
        import time
        import random
        def fetch_desc(job):
            time.sleep(random.uniform(0.5, 1.5)) # Small delay to avoid blocking
            desc = extract_linkedin_description(job["apply_link"])
            job["description"] = desc # Return full description
            job["full_description"] = desc # Keep full for ATS
            job["is_valid_description"] = len(desc) > 100
            return job

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            scraped_jobs = list(executor.map(fetch_desc, job_links))
            
        for job in scraped_jobs:
            if is_valid_job(job["title"], job["company"], job["full_description"]):
                all_jobs.append(job)
                
    except Exception as e:
        print(f"[DEBUG] LinkedIn Scraping Error: {e}")
        warning = "Failed to fetch live jobs from LinkedIn. Attempting to use cached results."

    # 4. Fallback Logic
    if len(all_jobs) == 0:
        warning = "No recent jobs found based on your filters. Try adjusting your search criteria."
        return {"jobs": [], "warning": warning}

    return {"jobs": all_jobs[:10], "warning": warning}