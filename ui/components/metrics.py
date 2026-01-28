"""
Metrics Component - Statistika ko'rsatish

Bu component statistika va metrikalarni ko'rsatish uchun
komponentlarni taqdim etadi.
"""

import streamlit as st
from typing import List, Dict, Optional


def render_metric_card(
        value: str,
        label: str,
        icon: str = "",
        color: str = "default"
):
    """
    Metrika kartasini ko'rsatish

    Args:
        value: Metrika qiymati (masalan: "658" yoki "92%")
        label: Metrika nomi (masalan: "Jami Issue")
        icon: Icon emoji (optional)
        color: Rang ("default", "success", "warning", "error")

    Example:
        >>> render_metric_card(
        >>>     value="658",
        >>>     label="Jami Issue",
        >>>     icon="📊"
        >>> )
    """
    # Color mapping
    color_map = {
        "default": "#238636",
        "success": "#2ea043",
        "warning": "#d29922",
        "error": "#da3633"
    }

    bg_color = color_map.get(color, color_map["default"])

    icon_html = f'<div class="metric-icon">{icon}</div>' if icon else ""

    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid {bg_color};">
        {icon_html}
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_metrics_grid(metrics: List[Dict]):
    """
    Metrikalar gridini ko'rsatish

    Args:
        metrics: Metrikalar ro'yxati
            Har bir metric: {
                'value': str,
                'label': str,
                'icon': str (optional),
                'color': str (optional)
            }

    Example:
        >>> metrics = [
        >>>     {'value': '658', 'label': 'Jami Issue', 'icon': '📊'},
        >>>     {'value': '92%', 'label': 'Accuracy', 'icon': '🎯', 'color': 'success'},
        >>>     {'value': '15-30 min', 'label': 'Vaqt', 'icon': '⏱️'}
        >>> ]
        >>> render_metrics_grid(metrics)
    """
    # Calculate columns
    num_metrics = len(metrics)
    cols = st.columns(num_metrics)

    for col, metric in zip(cols, metrics):
        with col:
            render_metric_card(
                value=metric['value'],
                label=metric['label'],
                icon=metric.get('icon', ''),
                color=metric.get('color', 'default')
            )


def render_stat_box(
        title: str,
        stats: Dict[str, str],
        icon: str = "📊"
):
    """
    Statistika qutisi

    Args:
        title: Sarlavha
        stats: Statistikalar dict (key: label, value: qiymat)
        icon: Icon emoji

    Example:
        >>> render_stat_box(
        >>>     title="PR Tahlili",
        >>>     stats={
        >>>         "PR'lar": "3 ta",
        >>>         "Fayllar": "25 ta",
        >>>         "Qo'shildi": "+150 qator"
        >>>     },
        >>>     icon="📊"
        >>> )
    """
    st.markdown(f"""
    <div class="stat-box">
        <div class="stat-box-header">
            <span class="stat-box-icon">{icon}</span>
            <span class="stat-box-title">{title}</span>
        </div>
        <div class="stat-box-content">
    """, unsafe_allow_html=True)

    for label, value in stats.items():
        st.markdown(f"""
            <div class="stat-item">
                <span class="stat-label">{label}:</span>
                <span class="stat-value">{value}</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)


def render_progress_metric(
        current: int,
        total: int,
        label: str,
        show_percentage: bool = True
):
    """
    Progress metrika

    Args:
        current: Joriy qiymat
        total: Jami qiymat
        label: Nomi
        show_percentage: Foizni ko'rsatish

    Example:
        >>> render_progress_metric(
        >>>     current=45,
        >>>     total=100,
        >>>     label="Test Cases"
        >>> )
    """
    percentage = (current / total * 100) if total > 0 else 0

    st.markdown(f"""
    <div class="progress-metric">
        <div class="progress-metric-header">
            <span class="progress-metric-label">{label}</span>
            <span class="progress-metric-value">{current}/{total}</span>
        </div>
        <div class="progress-metric-bar">
            <div class="progress-metric-fill" style="width: {percentage}%"></div>
        </div>
        {f'<div class="progress-metric-percentage">{percentage:.1f}%</div>' if show_percentage else ''}
    </div>
    """, unsafe_allow_html=True)


def render_comparison_metric(
        old_value: str,
        new_value: str,
        label: str,
        improvement: bool = True
):
    """
    Taqqoslash metrikasi

    Args:
        old_value: Eski qiymat
        new_value: Yangi qiymat
        label: Nomi
        improvement: Yaxshilanish (True) yoki yomonlashuv (False)

    Example:
        >>> render_comparison_metric(
        >>>     old_value="2-4 soat",
        >>>     new_value="15-30 min",
        >>>     label="Bug Investigation Time",
        >>>     improvement=True
        >>> )
    """
    arrow = "↓" if improvement else "↑"
    color = "#2ea043" if improvement else "#da3633"

    st.markdown(f"""
    <div class="comparison-metric">
        <div class="comparison-label">{label}</div>
        <div class="comparison-values">
            <span class="comparison-old">{old_value}</span>
            <span class="comparison-arrow" style="color: {color};">{arrow}</span>
            <span class="comparison-new" style="color: {color};">{new_value}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# CSS Styles
METRICS_STYLES = """
<style>
/* Metric Card */
.metric-card {
    background: linear-gradient(135deg, #161b22 0%, #21262d 100%);
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    border-left: 4px solid #238636;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    transition: transform 0.2s;
}

.metric-card:hover {
    transform: translateY(-2px);
}

.metric-icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
}

.metric-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: #e6edf3;
    margin-bottom: 0.5rem;
}

.metric-label {
    font-size: 0.95rem;
    color: #8b949e;
    font-weight: 500;
}

/* Stat Box */
.stat-box {
    background: #161b22;
    border-radius: 8px;
    padding: 1.5rem;
    margin: 1rem 0;
}

.stat-box-header {
    display: flex;
    align-items: center;
    margin-bottom: 1rem;
    border-bottom: 2px solid #21262d;
    padding-bottom: 0.5rem;
}

.stat-box-icon {
    font-size: 1.5rem;
    margin-right: 0.5rem;
}

.stat-box-title {
    font-size: 1.2rem;
    font-weight: 600;
    color: #e6edf3;
}

.stat-item {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem 0;
}

.stat-label {
    color: #8b949e;
}

.stat-value {
    color: #e6edf3;
    font-weight: 600;
}

/* Progress Metric */
.progress-metric {
    margin: 1rem 0;
}

.progress-metric-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
}

.progress-metric-label {
    color: #8b949e;
}

.progress-metric-value {
    color: #e6edf3;
    font-weight: 600;
}

.progress-metric-bar {
    height: 8px;
    background: #21262d;
    border-radius: 4px;
    overflow: hidden;
}

.progress-metric-fill {
    height: 100%;
    background: linear-gradient(90deg, #238636 0%, #2ea043 100%);
    transition: width 0.3s;
}

.progress-metric-percentage {
    text-align: right;
    color: #8b949e;
    font-size: 0.85rem;
    margin-top: 0.3rem;
}

/* Comparison Metric */
.comparison-metric {
    background: #161b22;
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
}

.comparison-label {
    color: #8b949e;
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
}

.comparison-values {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
}

.comparison-old {
    color: #6e7681;
    text-decoration: line-through;
}

.comparison-arrow {
    font-size: 1.5rem;
    font-weight: 700;
}

.comparison-new {
    font-weight: 700;
    font-size: 1.2rem;
}
</style>
"""


def inject_metrics_styles():
    """Metrics styles ni inject qilish"""
    st.markdown(METRICS_STYLES, unsafe_allow_html=True)

def render_results_info(top_n, found, filtered, min_similarity):
    """Qidiruv natijasi info (Bug Analyzer uchun)"""
    st.markdown(f"""
    <div class="results-info">
        ...
    </div>
    """, unsafe_allow_html=True)