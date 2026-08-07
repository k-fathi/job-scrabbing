"""
Application Tracker section – CRUD table, filters, manual add form.
"""

from datetime import date, datetime

import pandas as pd
import streamlit as st

from utils.storage import (
    add_application,
    delete_application,
    load_applications,
    load_cv_metadata,
    update_application,
)

# ── Constants ──────────────────────────────────────────────────
STATUS_OPTIONS = {
    "pending": "⏳ في الانتظار / لم يتم الرد",
    "interview": "🎙️ مقابلة",
    "offer": "🟣 عرض وظيفي",
    "accepted": "✅ مقبول",
    "rejected": "❌ مرفوض",
}

JOB_TYPE_OPTIONS = {
    "full_time": "وظيفة كاملة",
    "internship": "تدريب (Intern)",
    "part_time": "جزئي",
    "contract": "عقد مؤقت",
}

WORKPLACE_OPTIONS = ["Remote", "On-site", "Hybrid", "غير محدد"]


def _status_badge(status_key):
    """Return an HTML badge for a status."""
    colors = {
        "pending": ("#FFF3E0", "#E65100"),
        "accepted": ("#E8F5E9", "#1B5E20"),
        "rejected": ("#FFEBEE", "#B71C1C"),
        "interview": ("#E3F2FD", "#0D47A1"),
        "offer": ("#F3E5F5", "#4A148C"),
    }
    bg, fg = colors.get(status_key, ("#F5F5F5", "#333"))
    label = STATUS_OPTIONS.get(status_key, status_key)
    return (
        f'<span style="background:{bg};color:{fg};padding:3px 10px;'
        f'border-radius:12px;font-size:0.82rem;font-weight:600;">'
        f"{label}</span>"
    )


@st.dialog("✏️ تعديل التقديم")
def edit_application_dialog(app):
    st.write(f"تعديل تقديم: **{app.get('job_title', '')}** في **{app.get('company', '')}**")
    e_title = st.text_input("المسمى الوظيفي *", value=app.get("job_title", ""))
    e_company = st.text_input("الشركة *", value=app.get("company", ""))
    
    c1, c2, c3 = st.columns(3)
    with c1:
        e_type = st.selectbox(
            "نوع الشغل",
            options=list(JOB_TYPE_OPTIONS.keys()),
            format_func=lambda k: JOB_TYPE_OPTIONS[k],
            index=list(JOB_TYPE_OPTIONS.keys()).index(app.get("job_type", "full_time")) if app.get("job_type") in JOB_TYPE_OPTIONS else 0
        )
    with c2:
        e_role = st.text_input("الدور", value=app.get("job_role", ""))
    with c3:
        e_workplace = st.selectbox("طريقة العمل", WORKPLACE_OPTIONS, index=WORKPLACE_OPTIONS.index(app.get("workplace_type", "Remote")) if app.get("workplace_type") in WORKPLACE_OPTIONS else 0)
    
    c4, c5 = st.columns(2)
    with c4:
        e_loc = st.text_input("المكان", value=app.get("location", ""))
    with c5:
        e_link = st.text_input("لينك البوست", value=app.get("post_link", ""))
        
    e_notes = st.text_area("ملاحظات", value=app.get("notes", ""))
    
    if st.button("💾 حفظ التعديلات", use_container_width=True):
        if not e_title.strip() or not e_company.strip():
            st.error("لازم تكتب المسمى الوظيفي واسم الشركة!")
        else:
            update_application(app["id"], {
                "job_title": e_title.strip(),
                "company": e_company.strip(),
                "job_type": e_type,
                "job_role": e_role.strip(),
                "workplace_type": e_workplace,
                "location": e_loc.strip(),
                "post_link": e_link.strip(),
                "notes": e_notes.strip()
            })
            st.toast("✅ تم تعديل التقديم بنجاح!")
            st.rerun()


def render_tracker():
    """Render the My Applications tab."""

    apps = load_applications()
    cv_meta = load_cv_metadata()
    cv_versions = cv_meta.get("versions", [])
    cv_labels = {v["id"]: v["label"] for v in cv_versions}

    # ── Filters bar ────────────────────────────────────────────
    st.markdown("### 📝 متابعة التقديمات")

    with st.expander("🔎 فلترة وبحث", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            filter_status = st.multiselect(
                "الحالة",
                options=list(STATUS_OPTIONS.keys()),
                format_func=lambda k: STATUS_OPTIONS[k],
            )
        with fc2:
            filter_type = st.multiselect(
                "نوع الشغل",
                options=list(JOB_TYPE_OPTIONS.keys()),
                format_func=lambda k: JOB_TYPE_OPTIONS[k],
            )
        with fc3:
            companies = sorted(set(a.get("company", "") for a in apps if a.get("company")))
            filter_company = st.multiselect("الشركة", options=companies)
        with fc4:
            search_text = st.text_input("🔍 بحث حر", placeholder="DevOps, Google…")

    # Apply filters
    filtered = apps
    if filter_status:
        filtered = [a for a in filtered if a.get("status") in filter_status]
    if filter_type:
        filtered = [a for a in filtered if a.get("job_type") in filter_type]
    if filter_company:
        filtered = [a for a in filtered if a.get("company") in filter_company]
    if search_text.strip():
        q = search_text.strip().lower()
        filtered = [
            a
            for a in filtered
            if q in a.get("job_title", "").lower()
            or q in a.get("company", "").lower()
            or q in a.get("job_role", "").lower()
        ]

    st.caption(f"عدد النتائج: **{len(filtered)}** من إجمالي **{len(apps)}**")

    # ── Applications list ──────────────────────────────────────
    if filtered:
        # Sort newest first
        filtered_sorted = sorted(
            filtered,
            key=lambda a: a.get("applied_date", ""),
            reverse=True,
        )

        for app in filtered_sorted:
            status_key = app.get("status", "pending")
            badge_html = _status_badge(status_key)
            title_text = f"{app.get('job_title', 'N/A')} — {app.get('company', 'N/A')}"

            with st.expander(title_text, expanded=False):
                # Header with badge
                st.markdown(badge_html, unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**المسمى الوظيفي:** {app.get('job_title', '-')}")
                c2.markdown(f"**الشركة:** {app.get('company', '-')}")
                c3.markdown(f"**الدور:** {app.get('job_role', '-')}")

                c4, c5, c6 = st.columns(3)
                c4.markdown(
                    f"**نوع الشغل:** {JOB_TYPE_OPTIONS.get(app.get('job_type', ''), app.get('job_type', '-'))}"
                )
                c5.markdown(f"**المكان:** {app.get('location', '-')}")
                c6.markdown(f"**طريقة العمل:** {app.get('workplace_type', '-')}")

                c7, c8, c9 = st.columns(3)
                c7.markdown(f"**تاريخ البوست:** {app.get('post_date', '-')}")
                c8.markdown(f"**تاريخ التقديم:** {app.get('applied_date', '-')}")
                cv_label = cv_labels.get(app.get("cv_version_id", ""), app.get("cv_version_label", "-"))
                c9.markdown(f"**نسخة الـ CV:** {cv_label}")

                if app.get("post_link"):
                    st.markdown(f"🔗 [فتح البوست على LinkedIn]({app['post_link']})")

                if app.get("notes"):
                    st.markdown(f"📝 **ملاحظات:** {app['notes']}")

                # Quick status update
                st.markdown("---")
                uc1, uc2, uc3, uc4 = st.columns([2, 1, 1, 1])
                with uc1:
                    new_status = st.selectbox(
                        "تحديث الحالة",
                        options=list(STATUS_OPTIONS.keys()),
                        format_func=lambda k: STATUS_OPTIONS[k],
                        index=list(STATUS_OPTIONS.keys()).index(status_key)
                        if status_key in STATUS_OPTIONS
                        else 0,
                        key=f"status_{app['id']}",
                        label_visibility="collapsed"
                    )
                with uc2:
                    if st.button("💾 حفظ", key=f"save_{app['id']}", use_container_width=True):
                        update_application(app["id"], {"status": new_status})
                        st.toast("✅ تم تحديث الحالة!")
                        st.rerun()
                with uc3:
                    if st.button("✏️ تعديل", key=f"edit_{app['id']}", use_container_width=True):
                        edit_application_dialog(app)
                with uc4:
                    if st.button("🗑️ حذف", key=f"del_{app['id']}", use_container_width=True):
                        delete_application(app["id"])
                        st.toast("🗑️ تم حذف التقديم!")
                        st.rerun()
    else:
        st.info("مفيش تقديمات تتطابق مع الفلتر. جرب تضيف تقديم جديد أو غير الفلاتر.")

    # ── Manual add form ────────────────────────────────────────
    st.markdown("---")
    st.markdown("### ➕ إضافة تقديم جديد يدوي")

    with st.form("add_application_form", clear_on_submit=True):
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            job_title = st.text_input("المسمى الوظيفي *", placeholder="DevOps Engineer")
        with r1c2:
            company = st.text_input("الشركة *", placeholder="Google")

        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            job_type = st.selectbox(
                "نوع الشغل",
                options=list(JOB_TYPE_OPTIONS.keys()),
                format_func=lambda k: JOB_TYPE_OPTIONS[k],
            )
        with r2c2:
            job_role = st.text_input("الدور", placeholder="DevOps, Backend, …")
        with r2c3:
            workplace_type = st.selectbox("طريقة العمل", WORKPLACE_OPTIONS)

        r3c1, r3c2 = st.columns(2)
        with r3c1:
            location_input = st.text_input("المكان", placeholder="Cairo, Egypt")
        with r3c2:
            post_link = st.text_input(
                "لينك البوست",
                placeholder="https://linkedin.com/jobs/view/...",
            )

        r4c1, r4c2 = st.columns(2)
        with r4c1:
            post_date = st.date_input("تاريخ نزول البوست", value=date.today())
        with r4c2:
            applied_date = st.date_input("تاريخ التقديم", value=date.today())

        r5c1, r5c2 = st.columns(2)
        with r5c1:
            status = st.selectbox(
                "حالة الطلب",
                options=list(STATUS_OPTIONS.keys()),
                format_func=lambda k: STATUS_OPTIONS[k],
            )
        with r5c2:
            if cv_versions:
                cv_id_choice = st.selectbox(
                    "نسخة الـ CV المستخدمة",
                    options=[v["id"] for v in cv_versions],
                    format_func=lambda vid: cv_labels.get(vid, vid),
                    index=next(
                        (
                            i
                            for i, v in enumerate(cv_versions)
                            if v.get("is_active")
                        ),
                        0,
                    ),
                )
            else:
                cv_id_choice = None
                st.caption("مفيش نسخ CV مرفوعة. ارفع واحدة من تاب CV Manager.")

        notes = st.text_area("ملاحظات", placeholder="قدمت عن طريق Easy Apply")

        submitted = st.form_submit_button(
            "➕ إضافة التقديم", use_container_width=True
        )

    if submitted:
        if not job_title.strip() or not company.strip():
            st.error("لازم تكتب المسمى الوظيفي واسم الشركة!")
        else:
            add_application(
                {
                    "job_title": job_title.strip(),
                    "company": company.strip(),
                    "job_type": job_type,
                    "job_role": job_role.strip(),
                    "location": location_input.strip(),
                    "workplace_type": workplace_type,
                    "post_link": post_link.strip(),
                    "post_date": str(post_date),
                    "applied_date": str(applied_date),
                    "status": status,
                    "cv_version_id": cv_id_choice or "",
                    "cv_version_label": cv_labels.get(cv_id_choice, ""),
                    "notes": notes.strip(),
                    "source": "manual",
                }
            )
            st.toast("✅ تم إضافة التقديم بنجاح!")
            st.rerun()

    # ── Bulk export ────────────────────────────────────────────
    if apps:
        st.markdown("---")
        df = pd.DataFrame(apps)
        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ تحميل كل التقديمات كـ CSV",
            data=csv_data,
            file_name=f"applications_export_{date.today()}.csv",
            mime="text/csv",
        )
