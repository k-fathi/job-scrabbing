import csv
import io
import random
import time
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="LinkedIn Jobs Scraper", page_icon="💼", layout="centered")

st.title("💼 LinkedIn Jobs Scraper")
st.write("اكتب اسم الوظيفة، واختار الفلاتر اللي على مزاجك، ودوس بحث.")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0"
]

# ============================================================
#   نموذج الإدخال والفلاتر
# ============================================================
with st.form("search_form"):
    keywords_input = st.text_input("اسم الوظيفة (لو أكتر من واحدة افصل بفاصلة)", placeholder="Data Analyst, Python Developer")
    location = st.text_input("المكان", value="Egypt")
    
    col1, col2 = st.columns(2)
    with col1:
        sort_by_newest = st.checkbox("أحدث الوظايف الأول؟")
        fetch_full_desc = st.checkbox("سحب تفاصيل الوظيفة بالكامل؟ (هياخد وقت أطول)")
    with col2:
        workplace = st.selectbox("نوع الشغل", ["الكل", "عن بُعد (Remote)", "من الشركة (On-site)", "مختلط (Hybrid)"])
    
    pages_per_keyword = st.slider("عدد الصفحات لكل وظيفة (الحد الأقصى 10)", min_value=1, max_value=10, value=4)
    submitted = st.form_submit_button("ندوس بحث يخويا ؟")

# ============================================================
#   دوال السكرابنج
# ============================================================
def get_job_description(job_id, headers):
    try:
        desc_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
        resp = requests.get(desc_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "html.parser")
            div = soup.find("div", class_="show-more-less-html__markup")
            if div:
                return div.get_text(separator="\n", strip=True)
    except Exception:
        pass
    return "N/A"

def scrape_linkedin_jobs(keywords, location, pages_per_keyword, sort_by_newest, workplace, fetch_full_desc, progress_callback):
    all_jobs = []
    seen_job_ids = set()
    
    wt_map = {"عن بُعد (Remote)": "2", "من الشركة (On-site)": "1", "مختلط (Hybrid)": "3"}
    
    total_steps = len(keywords) * pages_per_keyword
    step = 0

    for keyword in keywords:
        for page in range(pages_per_keyword):
            step += 1
            if progress_callback:
                progress_callback(step / total_steps, f"بيدور على '{keyword}' - صفحة {page + 1}/{pages_per_keyword}")
            
            start = page * 25
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keyword}&location={location}&start={start}"
            
            if sort_by_newest:
                url += "&sortBy=DD"
            if workplace != "الكل":
                url += f"&f_WT={wt_map[workplace]}"
            
            max_retries = 3
            job_cards = []
            for attempt in range(max_retries):
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
                job_id = job_link.split("-")[-1] if "-" in job_link else job_link.split("/")[-1]
                
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
                post_date = date_elem["datetime"] if date_elem and date_elem.has_attr("datetime") else (date_elem.text.strip() if date_elem else "N/A")
                
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
                    job_data["Job Description"] = get_job_description(job_id, desc_headers)
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
        st.error("اكتب اسم وظيفة واحدة على الأقل يا هندسة.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(fraction, message):
            progress_bar.progress(fraction)
            status_text.text(message)

        with st.spinner("جاري سحب الوظايف..."):
            jobs = scrape_linkedin_jobs(keywords, location, pages_per_keyword, sort_by_newest, workplace, fetch_full_desc, update_progress)

        progress_bar.empty()
        status_text.empty()

        if not jobs:
            st.warning("مفيش نتايج! جرب تغير الكلمات أو قلل الفلاتر.")
        else:
            st.success(f"عاش! جبنالك {len(jobs)} وظيفة.")
            
            df = pd.DataFrame(jobs)
            
            # الترتيب الإجباري بالتاريخ لو متعلم على أحدث الوظايف
            if sort_by_newest:
                df = df.sort_values(by="Post Date", ascending=False).reset_index(drop=True)
            
            # إخفاء العمود من الجدول المطبوع بس
            df_display = df.drop(columns=["Job ID"], errors='ignore')

            st.dataframe(
                df_display, 
                use_container_width=True,
                column_config={
                    "Job Link": st.column_config.LinkColumn(
                        label="تقديم (Apply)",
                        help="اضغط هنا للتقديم على الوظيفة على لينكد إن",
                        display_text="قدم الآن (Apply Now)" 
                    )
                }
            )

            col1, col2 = st.columns(2)
            safe_keyword = keywords[0].lower().replace(" ", "_")
            
            with col1:
                csv_data = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="⬇ تحميل كـ CSV",
                    data=csv_data,
                    file_name=f"linkedin_jobs_{safe_keyword}.csv",
                    mime="text/csv",
                )
            
            with col2:
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name="Jobs")
                
                st.download_button(
                    label="⬇ تحميل كـ Excel",
                    data=excel_buffer.getvalue(),
                    file_name=f"linkedin_jobs_{safe_keyword}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
