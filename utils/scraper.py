"""
LinkedIn job scraping functions.
Extracted from the original app.py for modularity, including advanced search.
"""

import io
import re
import random
import string
import time
import requests
import pandas as pd
import PyPDF2
import docx
from bs4 import BeautifulSoup

try:
    import gdown
    GDOWN_AVAILABLE = True
except ImportError:
    GDOWN_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0"
]

STOPWORDS = set("""
a an the and or but if is are was were be been being to of in on at by for with
about against between into through during before after above below from up down
out off over under again further then once here there all any both each few more
most other some such no nor not only own same so than too very s t can will just
don should now this that these those i you he she it we they our your their
""".split())

TECH_SKILLS = {
    "python", "java", "javascript", "typescript", "cpp", "csharp", "php",
    "ruby", "go", "golang", "rust", "kotlin", "swift", "scala", "perl",
    "matlab", "dart", "objective", "vba", "sql", "nosql", "bash", "shell",
    "powershell", "assembly", "solidity", "html", "css", "sass", "scss", 
    "less", "react", "reactjs", "angular", "vue", "vuejs", "nextjs", "nuxt", 
    "svelte", "jquery", "bootstrap", "tailwind", "webpack", "vite", "babel", 
    "redux", "graphql", "node", "nodejs", "express", "django", "flask", 
    "fastapi", "spring", "springboot", "laravel", "symfony", "rails", "dotnet", 
    "aspnet", "nestjs", "rest", "restful", "api", "grpc", "soap", "microservices", 
    "websocket", "mysql", "postgresql", "postgres", "mongodb", "redis", 
    "elasticsearch", "cassandra", "dynamodb", "oracle", "sqlite", "mariadb", 
    "firebase", "firestore", "neo4j", "snowflake", "bigquery", "redshift",
    "aws", "azure", "gcp", "cloud", "ec2", "s3", "lambda", "cloudfront",
    "iam", "vpc", "eks", "aks", "gke", "heroku", "digitalocean", "cloudflare",
    "docker", "kubernetes", "k8s", "helm", "terraform", "ansible", "puppet",
    "chef", "jenkins", "gitlab", "github", "bitbucket", "circleci",
    "travisci", "argocd", "devops", "ci", "cd", "cicd", "linux", "unix",
    "windows", "nginx", "apache", "haproxy", "grafana", "prometheus",
    "datadog", "splunk", "elk", "logstash", "kibana", "vagrant",
    "virtualization", "vmware", "networking", "dns", "tcpip", "loadbalancing",
    "monitoring", "logging", "sre", "iac", "gitops", "security", "cybersecurity", 
    "penetration", "pentest", "firewall", "vpn", "encryption", "oauth", "jwt", 
    "ssl", "tls", "owasp", "siem", "compliance", "vulnerability", "pandas", 
    "numpy", "scikit", "sklearn", "tensorflow", "pytorch", "keras", "machine", 
    "learning", "deep", "nlp", "opencv", "spark", "hadoop", "kafka", "airflow", 
    "etl", "tableau", "powerbi", "excel", "statistics", "data", "analytics", 
    "visualization", "ai", "android", "ios", "flutter", "reactnative", "xamarin", 
    "swiftui", "testing", "selenium", "cypress", "junit", "pytest", "jest", 
    "postman", "qa", "automation", "unittest", "tdd", "bdd", "git", "jira", 
    "confluence", "agile", "scrum", "kanban", "trello", "figma", "uiux",
}

def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + " "
    except Exception:
        pass
    return text

def extract_text_from_docx(docx_file):
    text = ""
    try:
        doc = docx.Document(docx_file)
        for para in doc.paragraphs:
            text += para.text + " "
    except Exception:
        pass
    return text

def extract_text_from_gdrive(link):
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', link)
    if not match:
        match = re.search(r'id=([a-zA-Z0-9_-]+)', link)
    if not match:
        return ""
    file_id = match.group(1)

    try:
        doc_url = f"https://docs.google.com/document/d/{file_id}/export?format=txt"
        resp = requests.get(doc_url, timeout=10)
        if resp.status_code == 200 and not resp.text.strip().startswith("<!DOCTYPE html>"):
            return resp.text
    except Exception:
        pass

    if GDOWN_AVAILABLE:
        try:
            tmp_path = f"/tmp/_gdrive_cv_{file_id}"
            gdown.download(id=file_id, output=tmp_path, quiet=True, fuzzy=True)
            if tmp_path and pd.io.common.file_exists(tmp_path):
                with open(tmp_path, "rb") as f:
                    raw = f.read()
                if raw[:4] == b"%PDF":
                    return extract_text_from_pdf(io.BytesIO(raw))
                elif raw[:2] == b"PK":  
                    return extract_text_from_docx(io.BytesIO(raw))
        except Exception:
            pass

    try:
        pdf_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        resp = requests.get(pdf_url, timeout=10)
        if resp.status_code == 200 and resp.content[:4] == b"%PDF":
            return extract_text_from_pdf(io.BytesIO(resp.content))
    except Exception:
        pass
    return ""

def clean_tokens(text):
    text = text.lower()
    text = re.sub(r'[%s]' % re.escape(string.punctuation), ' ', text)
    tokens = re.findall(r'\b[a-zA-Z]{2,}\b', text)
    return [t for t in tokens if t not in STOPWORDS]

def calculate_match(cv_text, job_desc):
    if not cv_text or not job_desc or job_desc == "غير متوفر":
        return 0.0

    cv_tokens = clean_tokens(cv_text)
    job_tokens = clean_tokens(job_desc)

    if not job_tokens:
        return 0.0

    cv_clean = " ".join(cv_tokens)
    job_clean = " ".join(job_tokens)

    tfidf_score = 0.0
    if SKLEARN_AVAILABLE and cv_clean and job_clean:
        try:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform([cv_clean, job_clean])
            tfidf_score = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
        except Exception:
            tfidf_score = 0.0
    else:
        cv_set, job_set = set(cv_tokens), set(job_tokens)
        union = cv_set | job_set
        tfidf_score = (len(cv_set & job_set) / len(union)) if union else 0.0

    job_skills = {t for t in job_tokens if t in TECH_SKILLS}
    cv_skills = {t for t in cv_tokens if t in TECH_SKILLS}
    skill_score = (len(job_skills & cv_skills) / len(job_skills)) if job_skills else tfidf_score

    final_score = (0.65 * tfidf_score + 0.35 * skill_score) * 100
    return round(min(final_score, 100.0), 2)

def extract_job_id(job_link):
    match = re.search(r'-(\d+)(?:[/?]|$)', job_link)
    if match:
        return match.group(1)
    return job_link.rstrip("/").split("/")[-1]

def detect_workplace_type(soup, title, description, location_text):
    haystack = f"{title or ''} {(description or '')[:500]} {location_text or ''}".lower()
    
    if "remote" in haystack or "عن بعد" in haystack:
        return "عن بُعد"
    if "hybrid" in haystack or "مختلط" in haystack:
        return "مختلط"
    if "on-site" in haystack or "onsite" in haystack or "من الشركة" in haystack:
        return "من الشركة"

    if soup:
        for item in soup.find_all("li", class_="description__job-criteria-item"):
            header = item.find("h3")
            value = item.find("span", class_="description__job-criteria-text")
            if header and value:
                header_txt = header.get_text(strip=True).lower()
                value_txt = value.get_text(strip=True).lower()
                if "workplace" in header_txt or "location" in header_txt:
                    if "remote" in value_txt: return "عن بُعد"
                    if "hybrid" in value_txt: return "مختلط"
                    if "on-site" in value_txt or "onsite" in value_txt: return "من الشركة"

    return "غير محدد"

def get_job_description(job_id, headers):
    try:
        desc_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
        resp = requests.get(desc_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "html.parser")
            div = soup.find("div", class_="show-more-less-html__markup")
            description = div.get_text(separator="\n", strip=True) if div else "غير متوفر"
            return description, soup
    except Exception:
        pass
    return "غير متوفر", None

def scrape_linkedin_jobs(
    keywords,
    location,
    pages_per_keyword,
    workplace,
    time_filter,
    fetch_full_desc,
    cv_text,
    progress_callback=None
):
    all_jobs = []
    seen_job_ids = set()

    wt_map = {"عن بُعد": "2", "من الشركة": "1", "مختلط": "3"}
    time_map = {"آخر ٢٤ ساعة": "r86400", "آخر أسبوع": "r604800", "آخر شهر": "r2592000"}
    
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    total_steps = len(keywords) * pages_per_keyword
    step = 0

    force_fetch_desc = True if (cv_text or workplace == "الكل") else fetch_full_desc

    for keyword in keywords:
        for page in range(pages_per_keyword):
            step += 1
            if progress_callback:
                progress_callback(step / total_steps, f"بنسحب '{keyword}' - صفحة {page + 1}/{pages_per_keyword}")

            start = page * 25
            params = {
                "keywords": keyword,
                "location": location,
                "start": start,
            }
            
            if time_filter != "أي وقت":
                params["f_TPR"] = time_map[time_filter]
                
            if workplace != "الكل":
                params["f_WT"] = wt_map.get(workplace, "")

            max_retries = 3
            job_cards = []
            for attempt in range(max_retries):
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept-Language": "en-US,en;q=0.9",
                }
                try:
                    response = requests.get(base_url, headers=headers, params=params, timeout=10)
                    if response.status_code == 200 and "authwall" not in response.url:
                        soup = BeautifulSoup(response.content, "html.parser")
                        job_cards = soup.find_all("li")
                        if job_cards: break
                    elif response.status_code == 429:
                        time.sleep((2 ** attempt) + random.uniform(1, 2))
                        continue
                    time.sleep(random.uniform(2.0, 4.0))
                except Exception:
                    time.sleep(2 * (attempt + 1))

            if not job_cards:
                break

            for card in job_cards:
                link_elem = card.find("a", class_="base-card__full-link")
                if not link_elem: continue

                job_link = link_elem["href"].split("?")[0]
                job_id = extract_job_id(job_link)

                if job_id in seen_job_ids: continue
                seen_job_ids.add(job_id)

                title_elem = card.find("h3", class_="base-search-card__title")
                title = title_elem.text.strip() if title_elem else "غير متوفر"

                company_elem = card.find("h4", class_="base-search-card__subtitle")
                company = company_elem.text.strip() if company_elem else "غير متوفر"

                location_elem = card.find("span", class_="job-search-card__location")
                loc = location_elem.text.strip() if location_elem else "غير متوفر"

                date_elem = card.find("time")
                post_date = date_elem["datetime"] if date_elem and date_elem.has_attr("datetime") else (date_elem.text.strip() if date_elem else "غير متوفر")

                detected_wp = detect_workplace_type(None, title, "", loc)

                job_data = {
                    "Job ID": job_id,
                    "Keyword": keyword,
                    "Job Title": title,
                    "Company": company,
                    "Location": loc,
                    "Post Date": post_date,
                    "Workplace": workplace if workplace != "الكل" else detected_wp,
                    "Job Link": job_link,
                }

                if force_fetch_desc:
                    desc_headers = {"User-Agent": random.choice(USER_AGENTS)}
                    job_desc, job_soup = get_job_description(job_id, desc_headers)
                    job_data["Job Description"] = job_desc

                    if workplace == "الكل":
                        job_data["Workplace"] = detect_workplace_type(job_soup, title, job_desc, loc)

                    if cv_text:
                        job_data["Match Score (%)"] = calculate_match(cv_text, job_desc)

                    time.sleep(random.uniform(0.5, 1.5))

                all_jobs.append(job_data)

            time.sleep(random.uniform(1.5, 3.0))

    return all_jobs
