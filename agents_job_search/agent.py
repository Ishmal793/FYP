import os
import requests
import time
from agents_jd_validator.agent import validate_job_description

def fetch_jobs_from_serpapi(titles: list, location: str) -> list:
    """
    Fetches real-time market jobs from Google Jobs using SerpAPI based on top predicted titles.
    Rules applied:
    - API key from environment
    - Remove duplicates (via link parsing)
    - Handling rate limits (sleep between requests and catching 429)
    """
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY is missing. Please add it to your .env file.")
        
    url = "https://serpapi.com/search.json"
    all_jobs = []
    seen_links = set()
    
    # We query the top 2 titles to surface enough jobs without excessive API costs
    for title in titles[:2]: 
        params = {
            "engine": "google_jobs",
            "q": f"{title} in {location}",
            "hl": "en",
            "api_key": api_key
        }
        
        try:
            print(f"[DEBUG - JOB_SEARCH] Searching SerpAPI for: {params['q']}")
            response = requests.get(url, params=params, timeout=10)
            
            # Rate limit catch
            if response.status_code == 429:
                print("[DEBUG - JOB_SEARCH] Rate limit hit on SerpAPI.")
                break
                
            response.raise_for_status()
            data = response.json()
            
            jobs = data.get("jobs_results", [])
            for job in jobs:
                # Resolve link smartly
                link = job.get("share_link", "")
                if not link and job.get("related_links"):
                    link = job.get("related_links")[0].get("link", "")

                # Remove duplicates
                if link and link not in seen_links:
                    seen_links.add(link)
                    
                    description = job.get("description", "")
                    title = job.get("title", "Unknown Title")
                    
                    # Validate the job via LLM before allowing it
                    is_valid = validate_job_description(title, description)
                    if not is_valid:
                        continue
                        
                    if len(description) > 300:
                        description = description[:300] + "..."
                        
                    job_obj = {
                        "title": title,
                        "company": job.get("company_name", "Unknown Company"),
                        "location": job.get("location", location),
                        "description": description,
                        "url": link,
                        "via": job.get("via", "Google Jobs")
                    }
                    all_jobs.append(job_obj)
                    
                    if len(all_jobs) >= 8:
                        break # Stop if we have enough valid jobs
                        
            # Basic rate limit throttling between multiple titles
            time.sleep(1)
            if len(all_jobs) >= 8:
                break
            
        except Exception as e:
            print(f"[DEBUG - JOB_SEARCH] SerpAPI error: {str(e)}")
            
    # Return valid unique jobs
    return all_jobs[:8]
