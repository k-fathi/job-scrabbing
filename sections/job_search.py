"""
Enhanced Job Search section – LinkedIn scraper with 'Track This' integration and advanced CV matching.
"""

import io
from datetime import date
import pandas as pd
import streamlit as st

from utils.scraper import (
    scrape_linkedin_jobs,
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_gdrive
)
from utils.storage import add_application, get_active_cv, load_cv_metadata, get_cv_filepath
import os

def render_job_search():
    """Render the Job Search tab."""
    st.markdown("### 🔍 البحث عن وظائف على LinkedIn")
    st.caption("اكتب اسم الوظيفة، واختار الفلاتر، وارفع السيرة الذاتية لو حابب، ودوس بحث.")

    cv_meta = load_cv_metadata()
    cv_versions = cv_meta.get("versions", [])
    cv_labels = {v["id"]: v["label"] for v in cv_versions}
    
    # Optional CV upload for matching
    cv_text = ""
    with st.expander("📄 سيرة ذاتية لمطابقة المهارات (Match Score) - اختياري", expanded=False):
        cv_source = st.radio("اختار الطريقة:", ["بدون", "النسخة الحالية (CV Manager)", "رفع ملف جديد", "لينك جوجل درايف"], horizontal=True)
        
        if cv_source == "النسخة الحالية (CV Manager)":
            active_cv = get_active_cv()
            if active_cv:
                fpath = get_cv_filepath(active_cv["filename"])
                if os.path.exists(fpath):
                    with open(fpath, "rb") as f:
                        if active_cv["file_type"].lower() == "pdf":
                            cv_text = extract_text_from_pdf(f)
                        elif active_cv["file_type"].lower() in ["docx", "doc"]:
                            cv_text = extract_text_from_docx(fpath)
                    if cv_text:
                        st.success(f"تم تحميل السيرة الذاتية الحالية ({active_cv['label']}) بنجاح!")
                    else:
                        st.error("مش قادرين نقرأ الكلام من الـ CV الحالي.")
            else:
                st.warning("مفيش CV متفعل حالياً في إدارة الـ CV.")
        elif cv_source == "رفع ملف جديد":
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
        elif cv_source == "لينك جوجل درايف":
            gdrive_link = st.text_input("حط اللينك هنا (لازم يكون مفتوح للكل)")
            if gdrive_link:
                cv_text = extract_text_from_gdrive(gdrive_link)
                if cv_text:
                    st.success("تم قراية الملف من درايف بنجاح!")
                else:
                    st.error("مش قادرين نوصل للملف.")

    # ── Search form ────────────────────────────────────────────
    with st.form("search_form"):
        keywords_input = st.text_input(
            "اسم الوظيفة (لو أكتر من واحدة افصل بفاصلة)",
            placeholder="Data Analyst, Python Developer",
        )
        location = st.text_input("المكان", value="Egypt")

        col1, col2 = st.columns(2)
        with col1:
            time_filter = st.selectbox("وقت النشر", ["أي وقت", "آخر ٢٤ ساعة", "آخر أسبوع", "آخر شهر"])
            fetch_full_desc = st.checkbox("سحب التفاصيل بالكامل؟", help="ضروري عشان يحسب التطابق لو رافع سيرة ذاتية.")
        with col2:
            workplace = st.selectbox("نوع الشغل", ["الكل", "عن بُعد", "من الشركة", "مختلط"])

        pages_per_keyword = st.slider("عدد الصفحات", min_value=1, max_value=10, value=4)
        submitted = st.form_submit_button("ابحث يا وحش")

    # ── Execute search ─────────────────────────────────────────
    if submitted:
        keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

        if not keywords:
            st.error("اكتب اسم وظيفة واحدة على الأقل يا هندسة.")
            return

        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(fraction, message):
            progress_bar.progress(fraction)
            status_text.text(message)

        with st.spinner("جاري سحب الوظايف..."):
            jobs = scrape_linkedin_jobs(
                keywords,
                location,
                pages_per_keyword,
                workplace,
                time_filter,
                fetch_full_desc,
                cv_text,
                update_progress,
            )

        progress_bar.empty()
        status_text.empty()

        if not jobs:
            st.warning("مفيش نتايج! جرب تغير الكلمات أو قلل الفلاتر.")
            st.session_state.pop("scraped_jobs", None)
            return

        st.success(f"عاش! جبنالك **{len(jobs)}** وظيفة.")
        st.session_state["scraped_jobs"] = jobs
        st.session_state["job_results_keyword"] = keywords[0]

    # ── Display results ────────────────────────────────────────
    jobs = st.session_state.get("scraped_jobs", [])
    if not jobs:
        return

    df = pd.DataFrame(jobs)
    
    sort_choices = ["بدون ترتيب", "الوقت (الأحدث)"]
    if "Match Score (%)" in df.columns:
        sort_choices.append("أعلى نسبة تطابق")
        
    sort_option = st.selectbox("رتب الجدول بناءً على:", sort_choices)

    if sort_option == "الوقت (الأحدث)":
        df = df.sort_values(by="Post Date", ascending=False).reset_index(drop=True)
    elif sort_option == "أعلى نسبة تطابق" and "Match Score (%)" in df.columns:
        df = df.sort_values(by="Match Score (%)", ascending=False).reset_index(drop=True)

    df_display = df.drop(columns=["Job ID"], errors="ignore")

    col_config = {
        "Job Link": st.column_config.LinkColumn(
            label="تقديم (Apply)",
            help="اضغط هنا للتقديم على الوظيفة على لينكد إن",
            display_text="قدم الآن",
        )
    }
    if "Match Score (%)" in df.columns:
        col_config["Match Score (%)"] = st.column_config.NumberColumn(
            label="التطابق (%)",
            format="%.2f %%"
        )

    st.dataframe(df_display, use_container_width=True, column_config=col_config)

    # ── Download buttons ───────────────────────────────────────
    dl1, dl2 = st.columns(2)
    safe_kw = st.session_state.get("job_results_keyword", "jobs").lower().replace(" ", "_")
    with dl1:
        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇ تحميل كـ CSV",
            data=csv_data,
            file_name=f"linkedin_jobs_{safe_kw}.csv",
            mime="text/csv",
        )
    with dl2:
        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Jobs")
        st.download_button(
            "⬇ تحميل كـ Excel",
            data=excel_buf.getvalue(),
            file_name=f"linkedin_jobs_{safe_kw}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ── Track This section ─────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📌 تتبع وظيفة من النتائج")
    st.caption("اختار وظيفة من القايمة وهنسجلها في المتابعات تلقائياً.")

    job_options = {
        f"{j['Job Title']} — {j['Company']}": idx for idx, j in enumerate(jobs)
    }
    selected_label = st.selectbox(
        "اختار الوظيفة",
        options=list(job_options.keys()),
        key="track_job_select",
    )

    if selected_label:
        selected_job = jobs[job_options[selected_label]]

        with st.form("track_form"):
            st.markdown(
                f"**{selected_job.get('Job Title', '')}** في "
                f"**{selected_job.get('Company', '')}**"
            )

            tc1, tc2 = st.columns(2)
            with tc1:
                job_type = st.selectbox(
                    "نوع الشغل",
                    ["full_time", "internship", "part_time", "contract"],
                    format_func=lambda k: {
                        "full_time": "وظيفة كاملة",
                        "internship": "تدريب (Intern)",
                        "part_time": "جزئي",
                        "contract": "عقد مؤقت",
                    }.get(k, k),
                )
            with tc2:
                job_role = st.text_input(
                    "الدور",
                    value=selected_job.get("Keyword", ""),
                    placeholder="DevOps, Backend, …",
                )

            tc3, tc4 = st.columns(2)
            with tc3:
                applied_date = st.date_input("تاريخ التقديم", value=date.today())
            with tc4:
                if cv_versions:
                    cv_choice = st.selectbox(
                        "نسخة الـ CV",
                        options=[v["id"] for v in cv_versions],
                        format_func=lambda vid: cv_labels.get(vid, vid),
                        index=next(
                            (i for i, v in enumerate(cv_versions) if v.get("is_active")),
                            0,
                        ),
                    )
                else:
                    cv_choice = None
                    st.caption("ارفع CV من تاب CV Manager الأول.")

            notes = st.text_input("ملاحظات", placeholder="Easy Apply / Referral …")

            track_btn = st.form_submit_button(
                "📌 سجّل التقديم", use_container_width=True
            )

        if track_btn:
            wp = selected_job.get("Workplace", "غير محدد")
            if wp == "عن بُعد (Remote)":
                wp = "Remote"
            elif wp == "من الشركة (On-site)":
                wp = "On-site"
            elif wp == "مختلط (Hybrid)":
                wp = "Hybrid"

            add_application(
                {
                    "job_title": selected_job.get("Job Title", ""),
                    "company": selected_job.get("Company", ""),
                    "job_type": job_type,
                    "job_role": job_role.strip(),
                    "location": selected_job.get("Location", ""),
                    "workplace_type": wp,
                    "post_link": selected_job.get("Job Link", ""),
                    "post_date": selected_job.get("Post Date", ""),
                    "applied_date": str(applied_date),
                    "status": "pending",
                    "cv_version_id": cv_choice or "",
                    "cv_version_label": cv_labels.get(cv_choice, ""),
                    "notes": notes.strip(),
                    "source": "scraper",
                    "scraped_job_id": selected_job.get("Job ID", ""),
                }
            )
            st.toast(
                f"✅ تم تسجيل التقديم لـ «{selected_job.get('Job Title', '')}» "
                f"في «{selected_job.get('Company', '')}»"
            )
