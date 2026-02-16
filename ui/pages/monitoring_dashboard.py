# ui/pages/monitoring_dashboard.py
"""
DB Monitoring Dashboard

data/processing.db ni real-time monitoring qilish uchun dashboard.
Task holatlari, servis statuslari, xatoliklar va statistika.

Author: JASUR TURGUNOV
Version: 1.0
"""
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional

from ui.components import render_header


def render_monitoring_dashboard():
    """Monitoring Dashboard - DB holatini real-time ko'rsatish"""

    render_header(
        title="📊 DB Monitoring Dashboard",
        subtitle="Task va servis holatlarini real-time kuzatish",
        version="v1.0",
        icon="📊"
    )

    st.markdown("---")

    # DB fayl yo'li - project root/data papkasi
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(project_root, 'data', 'processing.db')

    # DB mavjudligini tekshirish
    if not os.path.exists(db_path):
        st.error(f"❌ DB fayl topilmadi: `{db_path}`")
        st.info("💡 Webhook birinchi marta ishlagandan keyin DB yaratiladi.")

        # DB ni avtomatik yaratish tugmasi
        if st.button("🔧 DB yaratish", type="primary"):
            try:
                from utils.database.task_db import init_db
                init_db()
                st.success("✅ DB muvaffaqiyatli yaratildi!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Xato: {str(e)}")
        return

    # Auto-refresh checkbox
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown(f"**DB fayl:** `{db_path}`")
        st.caption(f"Hajmi: {os.path.getsize(db_path) / 1024:.2f} KB")

    with col2:
        auto_refresh = st.checkbox("🔄 Auto-refresh (5s)", value=False)
        if auto_refresh:
            st.rerun()

    with col3:
        if st.button("🔄 Yangilash", type="primary"):
            st.rerun()

    st.markdown("---")

    # DB dan ma'lumotlar olish
    try:
        conn = sqlite3.connect(db_path)

        # 1. UMUMIY STATISTIKA
        _render_overall_stats(conn)

        st.markdown("---")

        # 2. TASK HOLATLARI (Pie Chart)
        col1, col2 = st.columns(2)

        with col1:
            _render_task_status_chart(conn)

        with col2:
            _render_service_status_chart(conn)

        st.markdown("---")

        # 3. SO'NGGI TASKLAR (Table)
        _render_recent_tasks_table(conn)

        st.markdown("---")

        # 4. XATOLIKLAR (Error Log)
        _render_errors_log(conn)

        conn.close()

    except Exception as e:
        st.error(f"❌ DB o'qishda xato: {str(e)}")
        st.exception(e)


def _render_overall_stats(conn: sqlite3.Connection):
    """Umumiy statistika - Metrikalar"""

    st.markdown("### 📈 Umumiy Statistika")

    # Query
    query = """
    SELECT
        COUNT(*) as total_tasks,
        SUM(CASE WHEN task_status = 'completed' THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN task_status = 'progressing' THEN 1 ELSE 0 END) as progressing,
        SUM(CASE WHEN task_status = 'returned' THEN 1 ELSE 0 END) as returned,
        SUM(CASE WHEN task_status = 'error' THEN 1 ELSE 0 END) as error,
        SUM(CASE WHEN skip_detected = 1 THEN 1 ELSE 0 END) as skipped,
        AVG(compliance_score) as avg_compliance,
        SUM(return_count) as total_returns
    FROM task_processing
    """

    df = pd.read_sql_query(query, conn)

    if df.empty or df['total_tasks'].iloc[0] == 0:
        st.info("📭 Hozircha task yo'q. Webhook ishlagandan keyin ma'lumotlar ko'rinadi.")
        return

    # Metrikalar
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "🎯 Jami Tasklar",
            df['total_tasks'].iloc[0],
            delta=None
        )

    with col2:
        completed = df['completed'].iloc[0]
        total = df['total_tasks'].iloc[0]
        success_rate = (completed / total * 100) if total > 0 else 0
        st.metric(
            "✅ Completed",
            completed,
            delta=f"{success_rate:.1f}%"
        )

    with col3:
        avg_compliance = df['avg_compliance'].iloc[0]
        st.metric(
            "📊 O'rtacha Moslik",
            f"{avg_compliance:.1f}%" if avg_compliance else "N/A",
            delta=None
        )

    with col4:
        total_returns = df['total_returns'].iloc[0]
        st.metric(
            "🔄 Jami Return",
            total_returns,
            delta=None
        )

    # Qo'shimcha metrikalar
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        progressing = df['progressing'].iloc[0]
        st.metric("⏳ Progressing", progressing)

    with col2:
        returned = df['returned'].iloc[0]
        st.metric("🔙 Returned", returned)

    with col3:
        error = df['error'].iloc[0]
        st.metric("❌ Error", error)

    with col4:
        skipped = df['skipped'].iloc[0]
        st.metric("⏭️ Skipped", skipped)


def _render_task_status_chart(conn: sqlite3.Connection):
    """Task holatlari Pie Chart"""

    st.markdown("#### 📊 Task Holatlari")

    query = """
    SELECT
        task_status,
        COUNT(*) as count
    FROM task_processing
    GROUP BY task_status
    """

    df = pd.read_sql_query(query, conn)

    if df.empty:
        st.info("📭 Ma'lumot yo'q")
        return

    # Color mapping
    color_map = {
        'completed': '#36B37E',
        'progressing': '#FFAB00',
        'returned': '#FF5630',
        'error': '#DE350B',
        'none': '#8993A4'
    }

    df['color'] = df['task_status'].map(color_map)

    # Plotly Pie Chart
    import plotly.express as px

    fig = px.pie(
        df,
        values='count',
        names='task_status',
        color='task_status',
        color_discrete_map=color_map,
        hole=0.4
    )

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#8b949e'),
        showlegend=True,
        height=300
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_service_status_chart(conn: sqlite3.Connection):
    """Servis holatlari (Service1 + Service2)"""

    st.markdown("#### 🔧 Servis Holatlari")

    query = """
    SELECT
        service1_status,
        service2_status,
        COUNT(*) as count
    FROM task_processing
    GROUP BY service1_status, service2_status
    """

    df = pd.read_sql_query(query, conn)

    if df.empty:
        st.info("📭 Ma'lumot yo'q")
        return

    # Service1 va Service2 alohida ko'rsatish
    service1_counts = df.groupby('service1_status')['count'].sum().reset_index()
    service2_counts = df.groupby('service2_status')['count'].sum().reset_index()

    col1, col2 = st.columns(2)

    with col1:
        st.caption("🔵 Service1 (TZ-PR)")
        for _, row in service1_counts.iterrows():
            status = row['service1_status']
            count = row['count']

            if status == 'done':
                st.success(f"✅ Done: {count}")
            elif status == 'pending':
                st.info(f"⏳ Pending: {count}")
            elif status == 'error':
                st.error(f"❌ Error: {count}")

    with col2:
        st.caption("🟢 Service2 (Testcase)")
        for _, row in service2_counts.iterrows():
            status = row['service2_status']
            count = row['count']

            if status == 'done':
                st.success(f"✅ Done: {count}")
            elif status == 'pending':
                st.info(f"⏳ Pending: {count}")
            elif status == 'error':
                st.error(f"❌ Error: {count}")


def _render_recent_tasks_table(conn: sqlite3.Connection):
    """Barcha tasklar jadvali - task_status filter bilan"""

    st.markdown("### 📋 Barcha Tasklar")

    # Filter bo'yicha
    col1, col2 = st.columns([3, 1])

    with col1:
        # Task status filter
        status_options = ['Barchasi', 'completed', 'progressing', 'returned', 'error']
        selected_status = st.selectbox(
            "📊 Status bo'yicha filter:",
            status_options,
            index=0,
            key='task_status_filter'
        )

    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing

    # Query - filter asosida
    if selected_status == 'Barchasi':
        query = """
        SELECT
            task_id,
            task_status,
            service1_status,
            service2_status,
            compliance_score,
            return_count,
            skip_detected,
            last_processed_at,
            updated_at
        FROM task_processing
        ORDER BY updated_at DESC
        """
    else:
        query = f"""
        SELECT
            task_id,
            task_status,
            service1_status,
            service2_status,
            compliance_score,
            return_count,
            skip_detected,
            last_processed_at,
            updated_at
        FROM task_processing
        WHERE task_status = '{selected_status}'
        ORDER BY updated_at DESC
        """

    df = pd.read_sql_query(query, conn)

    if df.empty:
        st.info(f"📭 {selected_status} statusda task yo'q")
        return

    # Natija soni
    st.caption(f"📊 Jami tasklar: **{len(df)}**")

    # Status color-coding
    def style_status(val):
        if val == 'completed' or val == 'done':
            return 'background-color: rgba(54, 179, 126, 0.2); color: #36B37E;'
        elif val == 'progressing' or val == 'pending':
            return 'background-color: rgba(255, 171, 0, 0.2); color: #FFAB00;'
        elif val == 'returned':
            return 'background-color: rgba(255, 86, 48, 0.2); color: #FF5630;'
        elif val == 'error':
            return 'background-color: rgba(222, 53, 11, 0.2); color: #DE350B;'
        return ''

    # Apply styling
    styled_df = df.style.applymap(
        style_status,
        subset=['task_status', 'service1_status', 'service2_status']
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        height=500
    )

    # Download button
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "💾 CSV yuklab olish",
        csv,
        f"tasks_{selected_status.lower()}.csv",
        "text/csv",
        key='download-csv'
    )


def _render_errors_log(conn: sqlite3.Connection):
    """Xatoliklar logi"""

    st.markdown("### ❌ Xatoliklar Logi")

    query = """
    SELECT
        task_id,
        task_status,
        error_message,
        service1_error,
        service2_error,
        updated_at
    FROM task_processing
    WHERE error_message IS NOT NULL
       OR service1_error IS NOT NULL
       OR service2_error IS NOT NULL
    ORDER BY updated_at DESC
    LIMIT 10
    """

    df = pd.read_sql_query(query, conn)

    if df.empty:
        st.success("✅ Xatoliklar yo'q!")
        return

    # Xatoliklar ro'yxati
    for _, row in df.iterrows():
        with st.expander(f"❌ {row['task_id']} — {row['updated_at']}"):
            st.markdown(f"**Status:** {row['task_status']}")

            if row['error_message']:
                st.error(f"**Task Error:** {row['error_message']}")

            if row['service1_error']:
                st.error(f"**Service1 Error:** {row['service1_error']}")

            if row['service2_error']:
                st.error(f"**Service2 Error:** {row['service2_error']}")
