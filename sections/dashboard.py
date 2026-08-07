"""
Dashboard section – KPI boxes, mini chart, recent activity, active CV card.
"""

from collections import Counter
from datetime import datetime, timedelta

import plotly.graph_objects as go
import streamlit as st

from utils.storage import get_active_cv, load_applications


# ── Helpers ────────────────────────────────────────────────────

_KPI_CONFIGS = [
    ("📨", "إجمالي التقديمات", "total", "#667eea"),
    ("⏳", "في الانتظار / لم يتم الرد", "pending", "#FFB300"),
    ("🎙️", "مقابلات", "interview", "#2979FF"),
    ("🟣", "عروض", "offer", "#AA00FF"),
    ("✅", "مقبول", "accepted", "#00C853"),
    ("❌", "مرفوض", "rejected", "#FF1744"),
]


def _kpi_card_html(icon, label, value, color):
    return f"""
    <div style="
        background: linear-gradient(135deg, {color}18 0%, {color}08 100%);
        border: 1px solid {color}30;
        border-radius: 16px;
        padding: 1rem 0.8rem;
        text-align: center;
        min-height: 130px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    ">
        <div style="font-size: 1.6rem;">{icon}</div>
        <div style="font-size: 2rem; font-weight: 800; color: {color};">{value}</div>
        <div style="font-size: 0.8rem; color: #999; margin-top: 0.2rem;">{label}</div>
    </div>
    """


def render_dashboard():
    """Render the Dashboard tab."""

    apps = load_applications()
    active_cv = get_active_cv()

    total = len(apps)
    status_counts = Counter(a.get("status", "pending") for a in apps)

    responded = (
        status_counts.get("accepted", 0)
        + status_counts.get("rejected", 0)
        + status_counts.get("interview", 0)
        + status_counts.get("offer", 0)
    )
    response_rate = round((responded / total) * 100, 1) if total else 0

    # ── KPI cards ──────────────────────────────────────────────
    cols = st.columns(6)
    values = {
        "total": total,
        "pending": status_counts.get("pending", 0),
        "interview": status_counts.get("interview", 0),
        "offer": status_counts.get("offer", 0),
        "accepted": status_counts.get("accepted", 0),
        "rejected": status_counts.get("rejected", 0),
    }
    for col, (icon, label, key, color) in zip(cols, _KPI_CONFIGS):
        col.markdown(_kpi_card_html(icon, label, values[key], color), unsafe_allow_html=True)

    # Response rate card
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #667eea12 0%, #764ba212 100%);
            border: 1px solid #667eea30;
            border-radius: 12px;
            padding: 0.8rem 1.2rem;
            margin-top: 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        ">
            <span style="font-size: 1.3rem;">📊</span>
            <span style="color: #999;">نسبة الردود:</span>
            <span style="font-size: 1.3rem; font-weight: 800; color: #667eea;">
                {response_rate}%
            </span>
            <span style="color: #777; font-size: 0.85rem;">
                ({responded} رد من {total} تقديم)
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("")

    # ── Two-column layout: mini chart + active CV ──────────────
    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.markdown("#### 📊 توزيع الحالات")
        if total > 0:
            labels_ar = {
                "pending": "في الانتظار / لم يتم الرد",
                "interview": "مقابلة",
                "offer": "عرض",
                "accepted": "مقبول",
                "rejected": "مرفوض",
            }
            chart_labels = [labels_ar.get(k, k) for k in status_counts.keys()]
            chart_values = list(status_counts.values())
            chart_colors = []
            _color_map = {
                "pending": "#FFB300",
                "interview": "#2979FF",
                "offer": "#AA00FF",
                "accepted": "#00C853",
                "rejected": "#FF1744",
            }
            for k in status_counts.keys():
                chart_colors.append(_color_map.get(k, "#999"))

            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=chart_labels,
                        values=chart_values,
                        hole=0.55,
                        marker=dict(colors=chart_colors),
                        textinfo="label+value",
                        textfont=dict(size=13),
                    )
                ]
            )
            fig.update_layout(
                showlegend=False,
                margin=dict(t=10, b=10, l=10, r=10),
                height=280,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("مفيش بيانات لسه. ابدأ بإضافة تقديمات!")

    with right_col:
        st.markdown("#### 📄 الـ CV النشط")
        if active_cv:
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, #667eea18 0%, #764ba218 100%);
                    border: 1px solid #667eea30;
                    border-radius: 14px;
                    padding: 1.2rem;
                    margin-top: 0.5rem;
                ">
                    <div style="font-size: 1rem; font-weight: 700; color: #667eea;">
                        📄 {active_cv['label']}
                    </div>
                    <div style="font-size: 0.82rem; color: #999; margin-top: 0.5rem;">
                        {active_cv['file_type'].upper()} • {active_cv['file_size_kb']} KB
                    </div>
                    <div style="font-size: 0.82rem; color: #999;">
                        رُفعت: {active_cv['upload_date'][:10]}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("مفيش CV مرفوع. روح تاب 📄 CV Manager.")

        # This week summary
        st.markdown("#### 📅 هذا الأسبوع")
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        last_week_start = week_start - timedelta(days=7)

        this_week = sum(
            1
            for a in apps
            if _parse_date(a.get("applied_date", "")) is not None
            and _parse_date(a.get("applied_date", "")) >= week_start
        )
        last_week = sum(
            1
            for a in apps
            if _parse_date(a.get("applied_date", "")) is not None
            and last_week_start <= _parse_date(a.get("applied_date", "")) < week_start
        )

        delta = this_week - last_week
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        delta_color = "#00C853" if delta >= 0 else "#FF1744"

        st.markdown(
            f"""
            <div style="
                background: #f8f9fa10;
                border: 1px solid #ddd3;
                border-radius: 12px;
                padding: 1rem;
                margin-top: 0.5rem;
                text-align: center;
            ">
                <div style="font-size: 1.8rem; font-weight: 800; color: #667eea;">{this_week}</div>
                <div style="font-size: 0.8rem; color: #999;">تقديم هذا الأسبوع</div>
                <div style="font-size: 0.85rem; color: {delta_color}; margin-top: 0.3rem;">
                    {delta_str} مقارنة بالأسبوع الماضي
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Recent activity ────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🕐 آخر التقديمات")

    if apps:
        recent = sorted(apps, key=lambda a: a.get("applied_date", ""), reverse=True)[:5]
        for a in recent:
            status_icons = {
                "pending": "🟡",
                "interview": "🔵",
                "offer": "🟣",
                "accepted": "🟢",
                "rejected": "🔴",
            }
            s_icon = status_icons.get(a.get("status", ""), "⚪")
            st.markdown(
                f"{s_icon} **{a.get('job_title', '-')}** — {a.get('company', '-')} "
                f"• {a.get('applied_date', '-')}"
            )
    else:
        st.caption("مفيش تقديمات لسه.")


def _parse_date(date_str):
    """Try to parse a date string, return date object or None."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str[:19], fmt).date()
        except (ValueError, TypeError):
            continue
    return None
