import csv
import io
import random
import string
import time
import re
import requests
import pandas as pd
import streamlit as st
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

st.set_page_config(page_title="LinkedIn Jobs Scraper", page_icon="💼", layout="centered")

st.title("💼 LinkedIn Jobs Scraper")
st.write("اكتب اسم الوظيفة، واختار الفلاتر، وارفع السيرة الذاتية لو حابب، ودوس بحث.")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0"
]

# ============================================================
#   دوال مساعدة لقرأة السيرة الذاتية
# ============================================================
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

# ============================================================
#   مطابقة السيرة الذاتية بالوظيفة
# ============================================================
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

# ============================================================
#   الواجهة والفلاتر
# ============================================================
st.subheader("📄 رفع السيرة الذاتية")
cv_source = st.radio("اختار الطريقة:", ["ملف", "لينك جوجل درايف"])

cv_text = ""
if cv_source == "ملف":
    cv_file = st.file_uploader("ارفع الملف هنا", type=["pdf", "docx"])
    if cv_file:
        if cv_file.name.endswith('.pdf'):
            cv_text = extract_text_from_pdf(cv_file)
        elif cv_file.name.endswith('.docx'):
            cv_text = extract_text_from_docx(cv_file)
        if cv_text:
            st.success("تم قراية الملف بنجاح!")
        else:
            st.error("مش قادرين نقرا الكلام من الملف ده.")
else:
    gdrive_link = st.text_input("حط اللينك هنا (لازم يكون مفتوح للكل)")
    if gdrive_link:
        cv_text = extract_text_from_gdrive(gdrive_link)
        if cv_text:
            st.success("تم قراية الملف من درايف بنجاح!")
        else:
            st.error("مش قادرين نوصل للملف.")

with st.form("search_form"):
    keywords_input = st.text_input("اسم الوظيفة", placeholder="Data Analyst")
    location = st.text_input("المكان", value="Egypt")

    col1, col2 = st.columns(2)
    with col1:
        time_filter = st.selectbox("وقت النشر", ["أي وقت", "آخر ٢٤ ساعة", "آخر أسبوع", "آخر شهر"])
        fetch_full_desc = st.checkbox("سحب التفاصيل بالكامل؟", help="ضروري عشان يحسب التطابق لو رافع سيرة ذاتية.")
    with col2:
        workplace = st.selectbox("نوع الشغل", ["الكل", "عن بُعد", "من الشركة", "مختلط"])

    pages_per_keyword = st.slider("عدد الصفحات", min_value=1, max_value=10, value=4)
    submitted = st.form_submit_button("ابحث يا وحش")

# ============================================================
#   دوال السحب
# ============================================================
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

def scrape_linkedin_jobs(keywords, location, pages_per_keyword, workplace, time_filter, fetch_full_desc, cv_text, progress_callback):
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
                params["f_WT"] = wt_map[workplace]

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

# ============================================================
#   تنفيذ البحث
# ============================================================
if submitted:
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

    if not keywords:
        st.error("اكتب اسم وظيفة واحدة على الأقل.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(fraction, message):
            progress_bar.progress(fraction)
            status_text.text(message)

        with st.spinner("جاري سحب الوظايف..."):
            jobs = scrape_linkedin_jobs(keywords, location, pages_per_keyword, workplace, time_filter, fetch_full_desc, cv_text, update_progress)

        progress_bar.empty()
        status_text.empty()

        if not jobs:
            st.warning("مفيش نتايج! جرب تغير الكلمات أو قلل الفلاتر.")
            st.session_state.pop("job_results_df", None)
        else:
            df = pd.DataFrame(jobs)
            st.session_state.job_results_df = df
            st.session_state.job_results_keyword = keywords[0]

# ============================================================
#   الترتيب والعرض (بره الفورم عشان يشتغل مباشر)
# ============================================================
if "job_results_df" in st.session_state:
    df = st.session_state.job_results_df.copy()
    safe_keyword = st.session_state.job_results_keyword.lower().replace(" ", "_")

    st.success(f"عاش! جبنالك {len(df)} وظيفة.")
    
    sort_choices = ["بدون ترتيب", "الوقت (الأحدث)"]
    if "Match Score (%)" in df.columns:
        sort_choices.append("أعلى نسبة تطابق")
        
    sort_option = st.selectbox("رتب الجدول بناءً على:", sort_choices)

    if sort_option == "الوقت (الأحدث)":
        df = df.sort_values(by="Post Date", ascending=False).reset_index(drop=True)
    elif sort_option == "أعلى نسبة تطابق" and "Match Score (%)" in df.columns:
        df = df.sort_values(by="Match Score (%)", ascending=False).reset_index(drop=True)

    df_display = df.drop(columns=["Job ID"], errors='ignore')

    st.dataframe(
        df_display,
        use_container_width=True,
        column_config={
            "Job Link": st.column_config.LinkColumn(
                label="تقديم",
                display_text="قدم دلوقتي"
            ),
            "Match Score (%)": st.column_config.NumberColumn(
                label="التطابق (%)",
                format="%.2f %%"
            )
        }
    )

    col1, col2 = st.columns(2)

    with col1:
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="⬇ تحميل CSV",
            data=csv_data,
            file_name=f"linkedin_jobs_{safe_keyword}.csv",
            mime="text/csv",
        )

    with col2:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Jobs")

        st.download_button(
            label="⬇ تحميل Excel",
            data=excel_buffer.getvalue(),
            file_name=f"linkedin_jobs_{safe_keyword}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
