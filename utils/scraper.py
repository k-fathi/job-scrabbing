"""
LinkedIn job scraping functions.
Extracted from the original app.py for modularity.
"""

import random
import time

import requests
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) "
    "Gecko/20100101 Firefox/127.0",
]

WORKPLACE_MAP = {
    "عن بُعد (Remote)": "2",
    "من الشركة (On-site)": "1",
    "مختلط (Hybrid)": "3",
}


def get_job_description(job_id, headers):
    """Fetch the full job description from LinkedIn's guest API."""
    try:
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "html.parser")
            div = soup.find("div", class_="show-more-less-html__markup")
            if div:
                return div.get_text(separator="\n", strip=True)
    except Exception:
        pass
    return "N/A"


def scrape_linkedin_jobs(
    keywords,
    location,
    pages_per_keyword,
    sort_by_newest,
    workplace,
    fetch_full_desc,
    progress_callback=None,
):
    """
    Scrape LinkedIn public job listings.

    Parameters
    ----------
    keywords : list[str]
    location : str
    pages_per_keyword : int
    sort_by_newest : bool
    workplace : str          – one of the Arabic labels or "الكل"
    fetch_full_desc : bool
    progress_callback : callable(fraction, message) | None

    Returns
    -------
    list[dict]  – each dict represents one scraped job posting.
    """
    all_jobs = []
    seen_job_ids = set()
    total_steps = len(keywords) * pages_per_keyword
    step = 0

    for keyword in keywords:
        for page in range(pages_per_keyword):
            step += 1
            if progress_callback:
                progress_callback(
                    step / total_steps,
                    f"بيدور على '{keyword}' - صفحة {page + 1}/{pages_per_keyword}",
                )

            start = page * 25
            url = (
                "https://www.linkedin.com/jobs-guest/jobs/api/"
                "seeMoreJobPostings/search"
                f"?keywords={keyword}&location={location}&start={start}"
            )

            if sort_by_newest:
                url += "&sortBy=DD"
            if workplace != "الكل" and workplace in WORKPLACE_MAP:
                url += f"&f_WT={WORKPLACE_MAP[workplace]}"

            max_retries = 3
            job_cards = []
            for _attempt in range(max_retries):
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept-Language": "en-US,en;q=0.9",
                }
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, "html.parser")
                        job_cards = soup.find_all("li")
                        if job_cards:
                            break
                    time.sleep(random.uniform(2.0, 4.0))
                except Exception:
                    time.sleep(2)

            if not job_cards:
                break

            for card in job_cards:
                link_elem = card.find("a", class_="base-card__full-link")
                if not link_elem:
                    continue

                job_link = link_elem["href"].split("?")[0]
                job_id = (
                    job_link.split("-")[-1]
                    if "-" in job_link
                    else job_link.split("/")[-1]
                )

                if job_id in seen_job_ids:
                    continue
                seen_job_ids.add(job_id)

                title_elem = card.find("h3", class_="base-search-card__title")
                title = title_elem.text.strip() if title_elem else "N/A"

                company_elem = card.find("h4", class_="base-search-card__subtitle")
                company = company_elem.text.strip() if company_elem else "N/A"

                location_elem = card.find("span", class_="job-search-card__location")
                loc = location_elem.text.strip() if location_elem else "N/A"

                date_elem = card.find("time")
                post_date = (
                    date_elem["datetime"]
                    if date_elem and date_elem.has_attr("datetime")
                    else (date_elem.text.strip() if date_elem else "N/A")
                )

                job_data = {
                    "Job ID": job_id,
                    "Keyword": keyword,
                    "Job Title": title,
                    "Company": company,
                    "Location": loc,
                    "Post Date": post_date,
                    "Workplace": workplace if workplace != "الكل" else "غير محدد",
                    "Job Link": job_link,
                }

                if fetch_full_desc:
                    desc_headers = {"User-Agent": random.choice(USER_AGENTS)}
                    job_data["Job Description"] = get_job_description(
                        job_id, desc_headers
                    )
                    time.sleep(random.uniform(0.5, 1.5))

                all_jobs.append(job_data)

            time.sleep(random.uniform(1.5, 3.0))

    return all_jobs
