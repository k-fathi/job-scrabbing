"""
CV Manager section – upload, version, and manage CV files.
"""

import os
import base64
from datetime import datetime

import streamlit as st

from utils.storage import (
    UPLOADS_DIR,
    add_cv_version,
    delete_cv_version,
    get_cv_filepath,
    load_cv_metadata,
    save_cv_metadata,
    set_active_cv,
)


@st.dialog("👀 معاينة الـ CV", width="large")
def preview_cv_dialog(filepath):
    with open(filepath, "rb") as f:
        pdf_bytes = f.read()
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    data_uri = f"data:application/pdf;base64,{base64_pdf}"

    # Use object + embed with fallback message for browsers that block data: URIs
    html_content = f"""
    <html><body style="margin:0;padding:0;overflow:hidden;">
    <object data="{data_uri}" type="application/pdf" width="100%" height="780px">
        <embed src="{data_uri}" type="application/pdf" width="100%" height="780px" />
        <p style="text-align:center;padding:2rem;font-family:sans-serif;color:#888;">
            المتصفح مش بيدعم معاينة PDF مباشرة. استخدم زرار التحميل بالأسفل.
        </p>
    </object>
    </body></html>
    """
    import streamlit.components.v1 as components
    components.html(html_content, height=800, scrolling=False)

    # Always provide a download fallback
    st.download_button(
        "⬇️ تحميل الـ CV",
        data=pdf_bytes,
        file_name=os.path.basename(filepath),
        mime="application/pdf",
        use_container_width=True,
    )


def render_cv_manager():
    """Render the CV Manager tab."""

    metadata = load_cv_metadata()
    versions = metadata.get("versions", [])
    active = next((v for v in versions if v.get("is_active")), None)

    # ── Active CV banner ───────────────────────────────────────
    if active:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #667eea22 0%, #764ba222 100%);
                border: 1px solid #667eea44;
                border-radius: 16px;
                padding: 1.2rem 1.5rem;
                margin-bottom: 1.5rem;
                display: flex;
                align-items: center;
                gap: 1rem;
            ">
                <div style="font-size: 2.5rem;">📄</div>
                <div>
                    <div style="font-size: 1.1rem; font-weight: 700; color: #667eea;">
                        ✅ النسخة الحالية: {active['label']}
                    </div>
                    <div style="font-size: 0.85rem; color: #999;">
                        {active['file_type'].upper()} • {active['file_size_kb']} KB
                        • رُفعت {active['upload_date'][:10]}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        active_filepath = get_cv_filepath(active["filename"])
        if os.path.exists(active_filepath):
            if active["file_type"].lower() == "pdf":
                if st.button("👀 اضغط هنا لمعاينة الـ CV الحالي", use_container_width=True, type="primary"):
                    preview_cv_dialog(active_filepath)
            else:
                st.info("💡 المعاينة متاحة لملفات PDF فقط.")
    else:
        st.info("📄 مفيش نسخة CV مرفوعة لسه. ارفع أول نسخة من الفورم تحت.")

    # ── Upload form ────────────────────────────────────────────
    st.markdown("### ⬆️ رفع نسخة CV جديدة")

    with st.form("cv_upload_form", clear_on_submit=True):
        uploaded_file = st.file_uploader(
            "اختار ملف الـ CV",
            type=["pdf", "docx", "doc"],
            help="PDF أو Word",
        )
        col_a, col_b = st.columns(2)
        with col_a:
            cv_label = st.text_input(
                "اسم / وصف النسخة",
                placeholder="CV v3.2 - DevOps Focus",
            )
        with col_b:
            cv_notes = st.text_input(
                "ملاحظات (اختياري)",
                placeholder="ضفت شهادة Kubernetes",
            )
        drive_link = st.text_input(
            "🔗 لينك Google Drive (اختياري)",
            placeholder="https://drive.google.com/file/d/...",
        )
        submitted = st.form_submit_button("📤 رفع النسخة", use_container_width=True)

    if submitted:
        if not uploaded_file:
            st.error("لازم تختار ملف الأول!")
        elif not cv_label.strip():
            st.error("لازم تكتب اسم أو وصف للنسخة!")
        else:
            # Build a unique filename
            ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_label = cv_label.strip().replace(" ", "_")[:30]
            filename = f"{safe_label}_{timestamp}.{ext}"

            # Save file to disk
            filepath = get_cv_filepath(filename)
            with open(filepath, "wb") as f:
                f.write(uploaded_file.getbuffer())

            size_kb = len(uploaded_file.getbuffer()) / 1024
            add_cv_version(
                label=cv_label.strip(),
                filename=filename,
                file_type=ext,
                file_size_kb=size_kb,
                notes=cv_notes.strip(),
                drive_link=drive_link.strip(),
            )
            st.toast(f"✅ تم رفع «{cv_label.strip()}» بنجاح!")
            st.rerun()

    # ── Suggested filename helper ──────────────────────────────
    st.markdown("---")
    st.markdown("### 💡 اسم ملف مقترح لـ Google Drive")
    today = datetime.now().strftime("%Y-%m-%d")
    suggested = f"Karim_CV_{today}.pdf"
    st.code(suggested, language=None)
    st.caption("انسخ الاسم ده لما ترفع الملف على Drive عشان يبقى منظم.")

    # ── Version history table ──────────────────────────────────
    st.markdown("---")
    st.markdown("### 📚 كل نسخ الـ CV")

    if not versions:
        st.caption("مفيش نسخ لسه.")
        return

    # Reverse so newest first
    for idx, v in enumerate(reversed(versions)):
        is_active = v.get("is_active", False)
        badge = "✅ نشطة" if is_active else ""
        icon = "📗" if is_active else "📄"

        with st.expander(
            f"{icon} {v['label']}  {badge}  —  {v['upload_date'][:10]}", expanded=False
        ):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**النوع:** `{v['file_type'].upper()}`")
            c2.markdown(f"**الحجم:** {v['file_size_kb']} KB")
            c3.markdown(f"**التاريخ:** {v['upload_date'][:10]}")

            if v.get("notes"):
                st.markdown(f"**ملاحظات:** {v['notes']}")

            # Drive link
            if v.get("drive_link"):
                st.markdown(f"🔗 [فتح في Google Drive]({v['drive_link']})")
            else:
                # Allow adding a drive link later
                new_link = st.text_input(
                    "أضف لينك Drive",
                    key=f"drive_{v['id']}",
                    placeholder="https://drive.google.com/...",
                )
                if new_link and st.button("💾 حفظ اللينك", key=f"save_drive_{v['id']}"):
                    meta = load_cv_metadata()
                    for mv in meta["versions"]:
                        if mv["id"] == v["id"]:
                            mv["drive_link"] = new_link.strip()
                    save_cv_metadata(meta)
                    st.toast("✅ تم حفظ اللينك!")
                    st.rerun()

            # Action buttons
            btn_cols = st.columns(3)
            # Download
            fpath = get_cv_filepath(v["filename"])
            if os.path.exists(fpath):
                with open(fpath, "rb") as fp:
                    btn_cols[0].download_button(
                        "⬇️ تحميل",
                        data=fp.read(),
                        file_name=v["filename"],
                        key=f"dl_{v['id']}",
                    )
            else:
                btn_cols[0].caption("الملف مش موجود على السيرفر")

            # Set active
            if not is_active:
                if btn_cols[1].button("✅ تفعيل", key=f"act_{v['id']}"):
                    set_active_cv(v["id"])
                    st.toast(f"✅ تم تفعيل «{v['label']}»")
                    st.rerun()

            # Delete
            if btn_cols[2].button("🗑️ حذف", key=f"del_{v['id']}"):
                delete_cv_version(v["id"])
                st.toast(f"🗑️ تم حذف «{v['label']}»")
                st.rerun()
