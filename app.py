"""
💼 Job Tracker Hub — Main Entry Point

A unified Streamlit platform for tracking job applications
and searching LinkedIn for new opportunities.
"""

import json

import streamlit as st

from sections.analytics import render_analytics
from sections.cv_manager import render_cv_manager
from sections.dashboard import render_dashboard
from sections.job_search import render_job_search
from sections.tracker import render_tracker
from utils.storage import export_all_data, import_all_data

# ── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="💼 Job Tracker Hub",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Import font ─────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Fix for Streamlit icons rendering as text */
    .material-symbols-rounded,
    [data-testid="stIconMaterial"],
    i,
    svg,
    .stIcon {
        font-family: 'Material Symbols Rounded' !important;
    }

    /* ── Header styling ──────────────────────────────────── */
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .main-subtitle {
        color: #999;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    /* ── Expander styling ────────────────────────────────── */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 0.95rem;
    }

    /* ── Form buttons ────────────────────────────────────── */
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        padding: 0.6rem 2rem;
        transition: opacity 0.2s ease;
    }
    .stFormSubmitButton > button:hover {
        opacity: 0.85;
    }

    /* ── Download buttons ────────────────────────────────── */
    .stDownloadButton > button {
        border-radius: 10px;
        font-weight: 600;
    }

    /* ── Sidebar ─────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea08 0%, #764ba208 100%);
    }

    /* ── Hide Streamlit branding ─────────────────────────── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ── Smooth scrolling ────────────────────────────────── */
    html {
        scroll-behavior: smooth;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ─────────────────────────────────────────────────────
st.markdown('<div class="main-title">💼 Job Tracker Hub</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="main-subtitle">منصة متابعة التقديمات والبحث عن وظائف</div>',
    unsafe_allow_html=True,
)

# ── Sidebar: Data management ──────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ إدارة البيانات")
    st.caption(
        "بيانات التقديمات والـ CV محفوظة كـ JSON. "
        "لو بتشغّل على Streamlit Cloud، اعمل Export بانتظام."
    )

    st.markdown("---")

    # Export
    st.markdown("#### 📥 تصدير البيانات")
    data_export = export_all_data()
    export_json = json.dumps(data_export, ensure_ascii=False, indent=2)
    st.download_button(
        "⬇️ تحميل نسخة احتياطية (JSON)",
        data=export_json.encode("utf-8"),
        file_name="job_tracker_backup.json",
        mime="application/json",
        use_container_width=True,
    )

    st.markdown("---")

    # Import
    st.markdown("#### 📤 استيراد بيانات")
    uploaded = st.file_uploader(
        "ارفع ملف النسخة الاحتياطية",
        type=["json"],
        key="import_file",
    )
    if uploaded:
        if st.button("📤 استيراد", use_container_width=True):
            try:
                imported = json.load(uploaded)
                import_all_data(imported)
                st.toast("✅ تم استيراد البيانات بنجاح!")
                st.rerun()
            except Exception as e:
                st.error(f"خطأ في الاستيراد: {e}")

    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #999; font-size: 0.75rem; margin-top: 2rem;">
            Built with ❤️ using Streamlit   
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Main tabs ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📊 Dashboard",
        "🔍 بحث عن وظائف",
        "📝 متابعة التقديمات",
        "📄 إدارة الـ CV",
        "📈 التحليلات",
    ]
)

with tab1:
    render_dashboard()

with tab2:
    render_job_search()

with tab3:
    render_tracker()

with tab4:
    render_cv_manager()

with tab5:
    render_analytics()
