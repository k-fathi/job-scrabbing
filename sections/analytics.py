"""
Analytics & Visualizations section – full-page interactive charts.
"""

from collections import Counter
from datetime import datetime

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.storage import load_applications, load_cv_metadata

# ── Color palette ──────────────────────────────────────────────

STATUS_COLORS = {
    "pending": "#FFB300",
    "interview": "#2979FF",
    "offer": "#AA00FF",
    "accepted": "#00C853",
    "rejected": "#FF1744",
}

STATUS_LABELS = {
    "pending": "في الانتظار / لم يتم الرد",
    "interview": "مقابلة",
    "offer": "عرض وظيفي",
    "accepted": "مقبول",
    "rejected": "مرفوض",
}

JOB_TYPE_LABELS = {
    "full_time": "وظيفة كاملة",
    "internship": "تدريب",
    "part_time": "جزئي",
    "contract": "عقد مؤقت",
}

CHART_PALETTE = [
    "#667eea", "#764ba2", "#f093fb", "#00bcd4",
    "#ff9100", "#00c853", "#ff1744", "#2979ff",
    "#aa00ff", "#ffd600",
]


def _parse_date(date_str):
    """Parse a date string into a date object or None."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str[:19], fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _plotly_layout(fig, height=350):
    """Apply a consistent clean layout to a plotly figure."""
    fig.update_layout(
        margin=dict(t=30, b=30, l=20, r=20),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
    )
    return fig


def render_analytics():
    """Render the Analytics & Visualizations tab."""

    apps = load_applications()

    if not apps:
        st.info("📈 مفيش بيانات لسه! ابدأ بإضافة تقديمات عشان الرسومات تظهر.")
        return

    st.markdown("### 📈 التحليلات والإحصائيات")

    # ── Date range filter ──────────────────────────────────────
    dates = [_parse_date(a.get("applied_date", "")) for a in apps]
    valid_dates = [d for d in dates if d is not None]

    if valid_dates:
        min_d, max_d = min(valid_dates), max(valid_dates)
        fc1, fc2 = st.columns(2)
        with fc1:
            start_filter = st.date_input("من تاريخ", value=min_d)
        with fc2:
            end_filter = st.date_input("لحد تاريخ", value=max_d)

        apps = [
            a for a in apps
            if _parse_date(a.get("applied_date", "")) is not None
            and start_filter <= _parse_date(a.get("applied_date", "")) <= end_filter
        ]
        st.caption(f"عدد التقديمات في الفترة المختارة: **{len(apps)}**")

    if not apps:
        st.warning("مفيش تقديمات في الفترة المختارة.")
        return

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    #  Row 1: Status donut + Job type bar
    # ══════════════════════════════════════════════════════════
    r1c1, r1c2 = st.columns(2)

    with r1c1:
        st.markdown("#### 📊 توزيع الحالات")
        status_cnt = Counter(a.get("status", "pending") for a in apps)
        labels = [STATUS_LABELS.get(k, k) for k in status_cnt.keys()]
        colors = [STATUS_COLORS.get(k, "#999") for k in status_cnt.keys()]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=list(status_cnt.values()),
                    hole=0.5,
                    marker=dict(colors=colors),
                    textinfo="label+percent",
                    textfont=dict(size=12),
                )
            ]
        )
        st.plotly_chart(_plotly_layout(fig, 320), use_container_width=True)

    with r1c2:
        st.markdown("#### 💼 نوع الشغل")
        type_cnt = Counter(a.get("job_type", "full_time") for a in apps)
        type_labels = [JOB_TYPE_LABELS.get(k, k) for k in type_cnt.keys()]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=list(type_cnt.values()),
                    y=type_labels,
                    orientation="h",
                    marker=dict(
                        color=CHART_PALETTE[: len(type_cnt)],
                        cornerradius=6,
                    ),
                    text=list(type_cnt.values()),
                    textposition="auto",
                )
            ]
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(_plotly_layout(fig, 320), use_container_width=True)

    # ══════════════════════════════════════════════════════════
    #  Row 2: Top companies + Job role distribution
    # ══════════════════════════════════════════════════════════
    r2c1, r2c2 = st.columns(2)

    with r2c1:
        st.markdown("#### 🏢 أكتر شركات قدمت فيها")
        company_cnt = Counter(a.get("company", "N/A") for a in apps)
        top_companies = company_cnt.most_common(10)
        if top_companies:
            c_names, c_vals = zip(*top_companies)
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=list(c_vals),
                        y=list(c_names),
                        orientation="h",
                        marker=dict(color="#667eea", cornerradius=6),
                        text=list(c_vals),
                        textposition="auto",
                    )
                ]
            )
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(_plotly_layout(fig, 350), use_container_width=True)

    with r2c2:
        st.markdown("#### 🎯 الأدوار الوظيفية")
        role_cnt = Counter(
            a.get("job_role", "غير محدد") or "غير محدد" for a in apps
        )
        top_roles = role_cnt.most_common(10)
        if top_roles:
            r_names, r_vals = zip(*top_roles)
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=list(r_vals),
                        y=list(r_names),
                        orientation="h",
                        marker=dict(color="#764ba2", cornerradius=6),
                        text=list(r_vals),
                        textposition="auto",
                    )
                ]
            )
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(_plotly_layout(fig, 350), use_container_width=True)

    # ══════════════════════════════════════════════════════════
    #  Row 3: Timeline – applications over time
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 📅 التقديمات عبر الزمن")

    dated_apps = [
        a for a in apps if _parse_date(a.get("applied_date", "")) is not None
    ]
    if dated_apps:
        date_counts = Counter(
            _parse_date(a["applied_date"]).strftime("%Y-%m-%d") for a in dated_apps
        )
        sorted_dates = sorted(date_counts.keys())
        fig = go.Figure(
            data=[
                go.Scatter(
                    x=sorted_dates,
                    y=[date_counts[d] for d in sorted_dates],
                    mode="lines+markers",
                    fill="tozeroy",
                    line=dict(color="#667eea", width=2.5),
                    marker=dict(size=7, color="#764ba2"),
                )
            ]
        )
        fig.update_xaxes(title_text="التاريخ")
        fig.update_yaxes(title_text="عدد التقديمات")
        st.plotly_chart(_plotly_layout(fig, 300), use_container_width=True)
    else:
        st.caption("مفيش تواريخ كافية لعرض الـ timeline.")

    # ══════════════════════════════════════════════════════════
    #  Row 4: Stacked status timeline
    # ══════════════════════════════════════════════════════════
    if dated_apps:
        st.markdown("#### 📊 حالات التقديم عبر الزمن")
        # Group by date + status
        date_status = {}
        for a in dated_apps:
            d = _parse_date(a["applied_date"]).strftime("%Y-%m-%d")
            s = a.get("status", "pending")
            date_status.setdefault(d, Counter())[s] += 1

        sorted_ds = sorted(date_status.keys())
        fig = go.Figure()
        for status_key in STATUS_COLORS:
            fig.add_trace(
                go.Bar(
                    x=sorted_ds,
                    y=[date_status[d].get(status_key, 0) for d in sorted_ds],
                    name=STATUS_LABELS.get(status_key, status_key),
                    marker=dict(color=STATUS_COLORS[status_key], cornerradius=4),
                )
            )
        fig.update_layout(barmode="stack")
        fig.update_xaxes(title_text="التاريخ")
        fig.update_yaxes(title_text="العدد")
        st.plotly_chart(_plotly_layout(fig, 320), use_container_width=True)

    # ══════════════════════════════════════════════════════════
    #  Row 5: Funnel chart + Response gauge
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    r5c1, r5c2 = st.columns(2)

    with r5c1:
        st.markdown("#### 🔻 قمع التقديمات")
        total = len(apps)
        responded = sum(
            1 for a in apps if a.get("status") in ("interview", "offer", "accepted", "rejected")
        )
        interviews = sum(1 for a in apps if a.get("status") in ("interview", "offer", "accepted"))
        offers = sum(1 for a in apps if a.get("status") in ("offer", "accepted"))
        accepted = sum(1 for a in apps if a.get("status") == "accepted")

        fig = go.Figure(
            go.Funnel(
                y=["قدّم", "رد", "مقابلة", "عرض", "قُبل"],
                x=[total, responded, interviews, offers, accepted],
                marker=dict(
                    color=["#667eea", "#2979FF", "#00bcd4", "#AA00FF", "#00C853"]
                ),
                textinfo="value+percent initial",
            )
        )
        st.plotly_chart(_plotly_layout(fig, 350), use_container_width=True)

    with r5c2:
        st.markdown("#### 📈 نسبة الردود")
        rate = round((responded / total) * 100, 1) if total else 0

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=rate,
                number=dict(suffix="%"),
                gauge=dict(
                    axis=dict(range=[0, 100]),
                    bar=dict(color="#667eea"),
                    steps=[
                        dict(range=[0, 30], color="#FFEBEE"),
                        dict(range=[30, 60], color="#FFF3E0"),
                        dict(range=[60, 100], color="#E8F5E9"),
                    ],
                    threshold=dict(
                        line=dict(color="#FF1744", width=3),
                        thickness=0.8,
                        value=50,
                    ),
                ),
                title=dict(text="نسبة الردود"),
            )
        )
        st.plotly_chart(_plotly_layout(fig, 350), use_container_width=True)

    # ══════════════════════════════════════════════════════════
    #  Row 6: Workplace pie + Heatmap
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    r6c1, r6c2 = st.columns(2)

    with r6c1:
        st.markdown("#### 🏠 طريقة العمل")
        wp_cnt = Counter(a.get("workplace_type", "غير محدد") or "غير محدد" for a in apps)
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=list(wp_cnt.keys()),
                    values=list(wp_cnt.values()),
                    hole=0.45,
                    marker=dict(colors=CHART_PALETTE),
                    textinfo="label+percent",
                )
            ]
        )
        st.plotly_chart(_plotly_layout(fig, 320), use_container_width=True)

    with r6c2:
        st.markdown("#### 🗓️ نشاط التقديم (يوم × أسبوع)")
        if dated_apps:
            day_names = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
            # Build week-number × day-of-week matrix
            week_day = {}
            for a in dated_apps:
                d = _parse_date(a["applied_date"])
                if d:
                    wk = d.isocalendar()[1]
                    dow = d.weekday()  # 0=Mon
                    week_day.setdefault(wk, Counter())[dow] += 1

            weeks = sorted(week_day.keys())
            z_matrix = []
            for dow in range(7):
                row = [week_day.get(wk, {}).get(dow, 0) for wk in weeks]
                z_matrix.append(row)

            fig = go.Figure(
                data=go.Heatmap(
                    z=z_matrix,
                    x=[f"W{w}" for w in weeks],
                    y=day_names,
                    colorscale=[[0, "#f5f5f5"], [1, "#667eea"]],
                    showscale=False,
                )
            )
            st.plotly_chart(_plotly_layout(fig, 320), use_container_width=True)
        else:
            st.caption("مفيش بيانات كافية للـ heatmap.")

    # ══════════════════════════════════════════════════════════
    #  Row 7: CV performance table
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 📄 أداء كل نسخة CV")

    cv_meta = load_cv_metadata()
    cv_versions = {v["id"]: v["label"] for v in cv_meta.get("versions", [])}

    if cv_versions:
        from sections.cv_manager import preview_cv_dialog
        from utils.storage import get_cv_filepath
        import os

        # Table header
        hc1, hc2, hc3, hc4, hc5 = st.columns([3, 2, 2, 2, 2])
        hc1.markdown("**نسخة الـ CV**")
        hc2.markdown("**عدد التقديمات**")
        hc3.markdown("**ردود**")
        hc4.markdown("**قُبل**")
        hc5.markdown("**نسبة الردود %**")
        st.markdown("<hr style='margin: 0.5rem 0;'/>", unsafe_allow_html=True)

        for cv_id, cv_label in cv_versions.items():
            cv_apps = [a for a in apps if a.get("cv_version_id") == cv_id]
            total_cv = len(cv_apps)
            responded_cv = sum(
                1 for a in cv_apps if a.get("status") in ("interview", "offer", "accepted", "rejected")
            )
            accepted_cv = sum(1 for a in cv_apps if a.get("status") == "accepted")
            rate_cv = round((responded_cv / total_cv) * 100, 1) if total_cv else 0

            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])
            with c1:
                if st.button(f"👀 {cv_label}", key=f"preview_btn_{cv_id}", use_container_width=True):
                    for v in cv_meta.get("versions", []):
                        if v["id"] == cv_id:
                            fpath = get_cv_filepath(v["filename"])
                            if os.path.exists(fpath):
                                if v.get("file_type", "").lower() == "pdf":
                                    preview_cv_dialog(fpath)
                                else:
                                    st.warning("المعاينة متاحة لملفات PDF فقط.")
                            else:
                                st.error("ملف الـ CV غير موجود.")
                            break
            
            c2.markdown(f"<div style='margin-top:0.4rem;'>{total_cv}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div style='margin-top:0.4rem;'>{responded_cv}</div>", unsafe_allow_html=True)
            c4.markdown(f"<div style='margin-top:0.4rem;'>{accepted_cv}</div>", unsafe_allow_html=True)
            c5.markdown(f"<div style='margin-top:0.4rem;'>{rate_cv}%</div>", unsafe_allow_html=True)

    else:
        st.caption("مفيش نسخ CV مسجلة.")
