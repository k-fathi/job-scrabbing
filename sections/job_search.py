"""
Enhanced Job Search section – LinkedIn scraper with 'Track This' integration.
"""

import io
from datetime import date

import pandas as pd
import streamlit as st

from utils.scraper import scrape_linkedin_jobs
from utils.storage import add_application, get_active_cv, load_cv_metadata


def render_job_search():
    """Render the Job Search tab."""

    st.markdown("### 🔍 البحث عن وظائف على LinkedIn")
    st.caption("اكتب اسم الوظيفة، واختار الفلاتر، ودوس بحث.")

    cv_meta = load_cv_metadata()
    cv_versions = cv_meta.get("versions", [])
    cv_labels = {v["id"]: v["label"] for v in cv_versions}
    active_cv = get_active_cv()

    # ── Search form ────────────────────────────────────────────
    with st.form("search_form"):
        keywords_input = st.text_input(
            "اسم الوظيفة (لو أكتر من واحدة افصل بفاصلة)",
            placeholder="Data Analyst, Python Developer",
        )
        location = st.text_input("المكان", value="Egypt")

        col1, col2 = st.columns(2)
        with col1:
            sort_by_newest = st.checkbox("أحدث الوظايف الأول؟")
            fetch_full_desc = st.checkbox(
                "سحب تفاصيل الوظيفة بالكامل؟ (هياخد وقت أطول)"
            )
        with col2:
            workplace = st.selectbox(
                "نوع الشغل",
                ["الكل", "عن بُعد (Remote)", "من الشركة (On-site)", "مختلط (Hybrid)"],
            )

        pages_per_keyword = st.slider(
            "عدد الصفحات لكل وظيفة (الحد الأقصى 10)",
            min_value=1,
            max_value=10,
            value=4,
        )
        submitted = st.form_submit_button("ندوس بحث يخويا ؟")

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
                sort_by_newest,
                workplace,
                fetch_full_desc,
                update_progress,
            )

        progress_bar.empty()
        status_text.empty()

        if not jobs:
            st.warning("مفيش نتايج! جرب تغير الكلمات أو قلل الفلاتر.")
            return

        st.success(f"عاش! جبنالك **{len(jobs)}** وظيفة.")
        st.session_state["scraped_jobs"] = jobs

    # ── Display results ────────────────────────────────────────
    jobs = st.session_state.get("scraped_jobs", [])
    if not jobs:
        return

    df = pd.DataFrame(jobs)
    if "Post Date" in df.columns:
        df = df.sort_values(by="Post Date", ascending=False).reset_index(drop=True)

    df_display = df.drop(columns=["Job ID"], errors="ignore")

    st.dataframe(
        df_display,
        use_container_width=True,
        column_config={
            "Job Link": st.column_config.LinkColumn(
                label="تقديم (Apply)",
                help="اضغط هنا للتقديم على الوظيفة على لينكد إن",
                display_text="قدم الآن",
            )
        },
    )

    # ── Download buttons ───────────────────────────────────────
    dl1, dl2 = st.columns(2)
    safe_kw = jobs[0].get("Keyword", "jobs").lower().replace(" ", "_") if jobs else "jobs"
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
