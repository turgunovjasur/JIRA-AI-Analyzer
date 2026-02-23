"""
Sprint Report Page - Streamlit UI

Sprint bo'yicha task statistikasi va tahlil

Author: JASUR TURGUNOV
Version: 1.0
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime


def render_sprint_report():
    """Main entry point for Sprint Report page"""
    st.title("📈 Sprint Report")
    st.markdown("Sprint bo'yicha task statistikasi va tahlil")

    # Sidebar controls
    with st.sidebar:
        st.subheader("⚙️ Sozlamalar")
        days = st.slider("Davr (kunlar)", 1, 90, 7, help="Qancha kunlik ma'lumot ko'rsatilsin")
        limit = st.slider("Top features soni", 5, 50, 10, help="Eng ko'p ishlangan features soni")

    # Fetch data from API
    try:
        with st.spinner("Ma'lumotlar yuklanmoqda..."):
            response = requests.get(
                "http://localhost:8000/api/sprint-report",
                params={"days": days, "limit": limit},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ API xatosi: Webhook service ishlamayapti. "
                "Iltimos, `python services/webhook/jira_webhook_handler.py` orqali ishga tushiring.")
        return
    except requests.exceptions.Timeout:
        st.error("❌ API javob bermadi (timeout). Qaytadan urinib ko'ring.")
        return
    except Exception as e:
        st.error(f"❌ API xatosi: {e}")
        return

    # Render sections
    _render_overview_metrics(data)
    st.divider()
    _render_task_type_chart(data)
    st.divider()
    _render_top_features(data)
    st.divider()
    _render_bug_distribution(data)
    st.divider()
    _render_developer_workload(data)

    # Footer
    st.caption(f"📅 Generatsiya vaqti: {datetime.fromisoformat(data['generated_at']).strftime('%Y-%m-%d %H:%M:%S')}")


def _render_overview_metrics(data):
    """Overview KPIs - metric cards"""
    st.subheader("📊 Umumiy Ko'rinish")

    # Convert list to dict for easier access
    task_by_type = {item['task_type']: item['count'] for item in data['task_by_type']}

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric("📦 Jami Tasklar", data['total_tasks'])

    with col2:
        st.metric("🚀 Product", task_by_type.get('product', 0))

    with col3:
        st.metric("👤 Client", task_by_type.get('client', 0))

    with col4:
        st.metric("🐛 Bug", task_by_type.get('bug', 0))

    with col5:
        st.metric("❌ Error", task_by_type.get('error', 0))

    with col6:
        st.metric("🔍 Analiz", task_by_type.get('analiz', 0))


def _render_task_type_chart(data):
    """Pie chart - task types distribution"""
    st.subheader("📊 Task Turlari Taqsimoti")

    if not data['task_by_type']:
        st.info("Ma'lumot yo'q")
        return

    df = pd.DataFrame(data['task_by_type'])

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.pie(
            df,
            values='count',
            names='task_type',
            title=f"Task Turlari ({data['period']})",
            hole=0.3,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.dataframe(
            df[['task_type', 'count', 'percentage']].rename(columns={
                'task_type': 'Turi',
                'count': 'Soni',
                'percentage': 'Foiz'
            }),
            width='stretch',
            hide_index=True
        )


def _render_top_features(data):
    """Top features table + stacked bar chart"""
    st.subheader("🏗️ Top Features (eng ko'p ishlangan)")

    if not data['top_features']:
        st.info("Ma'lumot yo'q")
        return

    df = pd.DataFrame(data['top_features'])

    # Stacked bar chart
    fig = go.Figure()

    colors = {
        'product': '#1f77b4',
        'client': '#ff7f0e',
        'bug': '#d62728',
        'error': '#e377c2',
        'analiz': '#17becf',
        'other': '#bcbd22'
    }

    for col in ['product', 'client', 'bug', 'error', 'analiz', 'other']:
        fig.add_trace(go.Bar(
            name=col.capitalize(),
            x=df['feature_name'],
            y=df[col],
            marker_color=colors.get(col, '#7f7f7f'),
            text=df[col],
            textposition='inside'
        ))

    fig.update_layout(
        barmode='stack',
        title='Task Taqsimoti (Feature bo\'yicha)',
        xaxis_title='Feature',
        yaxis_title='Task soni',
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, width='stretch')

    # Table
    st.dataframe(
        df.rename(columns={
            'feature_name': 'Feature',
            'total_tasks': 'Jami',
            'product': 'Product',
            'client': 'Client',
            'bug': 'Bug',
            'error': 'Error',
            'analiz': 'Analiz',
            'other': 'Boshqa'
        }),
        width='stretch',
        hide_index=True
    )


def _render_bug_distribution(data):
    """Bug/error distribution by feature"""
    st.subheader("🐛 Bug/Error Taqsimoti")

    if not data['bug_distribution']:
        st.success("✅ Buglar topilmadi!")
        return

    df = pd.DataFrame(data['bug_distribution'])

    # Grouped bar chart
    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Bug',
        x=df['feature_name'],
        y=df['bug_count'],
        marker_color='#d62728',
        text=df['bug_count'],
        textposition='outside'
    ))

    fig.add_trace(go.Bar(
        name='Error',
        x=df['feature_name'],
        y=df['error_count'],
        marker_color='#e377c2',
        text=df['error_count'],
        textposition='outside'
    ))

    fig.update_layout(
        barmode='group',
        title='Bug va Error soni (Feature bo\'yicha)',
        xaxis_title='Feature',
        yaxis_title='Soni',
        height=400,
        showlegend=True
    )

    st.plotly_chart(fig, width='stretch')


def _render_developer_workload(data):
    """Developer workload statistics table"""
    st.subheader("👥 Developer Workload")

    if not data['developer_workload']:
        st.info("Ma'lumot yo'q")
        return

    df = pd.DataFrame(data['developer_workload'])

    # Format compliance score
    df['avg_compliance_score'] = df['avg_compliance_score'].apply(
        lambda x: f"{x}%" if x is not None else "N/A"
    )

    # Display styled table
    st.dataframe(
        df.rename(columns={
            'assignee': 'Developer',
            'total_tasks': 'Jami',
            'completed': 'Tugallangan',
            'in_progress': 'Jarayonda',
            'returned': 'Qaytarilgan',
            'avg_compliance_score': 'O\'rtacha Moslik'
        }).style.background_gradient(subset=['Jami'], cmap='Blues'),
        width='stretch',
        hide_index=True
    )
