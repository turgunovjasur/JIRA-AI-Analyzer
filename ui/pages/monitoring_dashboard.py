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
        conn = sqlite3.connect(db_path, timeout=30.0)

        # WAL mode checkpoint - fresh data olish uchun
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        conn.execute("PRAGMA synchronous=FULL")

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

        st.markdown("---")

        # 5. BLOCKED TASKLAR
        _render_blocked_tasks(conn)

        st.markdown("---")

        # 6. TASK O'CHIRISH
        _render_task_delete(conn, db_path)

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
        SUM(CASE WHEN task_status = 'blocked' THEN 1 ELSE 0 END) as blocked,
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
    col1, col2, col3, col4, col5 = st.columns(5)

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
        blocked = df['blocked'].iloc[0]
        st.metric("🔒 Blocked", blocked)

    with col5:
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
        'blocked': '#4C9AFF',
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
            elif status == 'skip':
                st.warning(f"⏭️ Skip: {count}")
            elif status == 'blocked':
                st.info(f"🔒 Blocked: {count}")

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
            elif status == 'blocked':
                st.info(f"🔒 Blocked: {count}")
            elif status == 'skip':
                st.warning(f"⏭️ Skip: {count}")


def _render_recent_tasks_table(conn: sqlite3.Connection):
    """Barcha tasklar jadvali - task_status filter bilan"""

    st.markdown("### 📋 Barcha Tasklar")

    # Filter bo'yicha
    col1, col2 = st.columns([3, 1])

    with col1:
        # Task status filter
        status_options = ['Barchasi', 'completed', 'progressing', 'returned', 'error', 'blocked', 'none']
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
        elif val == 'blocked':
            return 'background-color: rgba(76, 154, 255, 0.2); color: #4C9AFF;'
        elif val == 'skip':
            return 'background-color: rgba(255, 171, 0, 0.15); color: #FFAB00;'
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


def _render_blocked_tasks(conn: sqlite3.Connection):
    """Blocked tasklar bo'limi"""

    st.markdown("### 🔒 Blocked Tasklar")

    query = """
    SELECT
        task_id,
        service1_status,
        service2_status,
        block_reason,
        blocked_at,
        blocked_retry_at,
        updated_at
    FROM task_processing
    WHERE task_status = 'blocked'
    ORDER BY blocked_retry_at ASC
    """

    df = pd.read_sql_query(query, conn)

    if df.empty:
        st.success("✅ Blocked tasklar yo'q!")
        return

    st.caption(f"🔒 Jami blocked: **{len(df)}** ta task")

    for _, row in df.iterrows():
        retry_at = row.get('blocked_retry_at', '')
        remaining = ""
        if retry_at:
            try:
                retry_dt = datetime.fromisoformat(retry_at)
                diff = retry_dt - datetime.now()
                if diff.total_seconds() > 0:
                    minutes = int(diff.total_seconds() / 60)
                    seconds = int(diff.total_seconds() % 60)
                    remaining = f"({minutes}m {seconds}s qoldi)"
                else:
                    remaining = "(qayta ishlash vaqti keldi!)"
            except:
                pass

        with st.expander(f"🔒 {row['task_id']} — s1={row['service1_status']}, s2={row['service2_status']} {remaining}"):
            st.markdown(f"**Sabab:** {row.get('block_reason', 'N/A')}")
            st.markdown(f"**Blocked vaqti:** {row.get('blocked_at', 'N/A')}")
            st.markdown(f"**Qayta ishlash vaqti:** {retry_at} {remaining}")


def _render_task_delete(conn: sqlite3.Connection, db_path: str):
    """Task o'chirish funksiyasi"""

    st.markdown("### 🗑️ Task O'chirish")

    st.markdown("""
    <div style="background: rgba(222, 53, 11, 0.08); padding: 0.7rem; border-radius: 8px; margin-bottom: 0.7rem;">
        <p style="color: #8b949e; margin: 0; font-size: 0.85rem;">
            ⚠️ <strong>Diqqat:</strong> Task o'chirilgandan keyin qayta tiklab bo'lmaydi.
            O'chirilgan taskni qayta ishlash uchun JIRA da "Ready to Test" statusga o'tkazing.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Session state'dan delete holatini olish
    if 'delete_success' not in st.session_state:
        st.session_state.delete_success = None
    if 'delete_task_key' not in st.session_state:
        st.session_state.delete_task_key = ""

    # Success message ko'rsatish va input field'ni tozalash
    if st.session_state.delete_success:
        deleted_key = st.session_state.delete_task_key
        st.success(f"✅ `{deleted_key}` bazadan o'chirildi!")
        st.session_state.delete_success = None
        st.session_state.delete_task_key = ""
        # Input field'ni tozalash uchun key'ni o'zgartirish
        if 'delete_task_key_input_counter' not in st.session_state:
            st.session_state.delete_task_key_input_counter = 0
        st.session_state.delete_task_key_input_counter += 1

    col1, col2 = st.columns([3, 1])

    with col1:
        # Input field'ni tozalash uchun unique key ishlatish
        input_key = f"delete_task_key_input_{st.session_state.get('delete_task_key_input_counter', 0)}"
        task_key_input = st.text_input(
            "Task Key",
            placeholder="DEV-1234",
            key=input_key,
            value="",
            label_visibility="collapsed"
        )

    with col2:
        delete_clicked = st.button("🗑️ O'chirish", type="primary", key="delete_task_btn")

    # Delete confirmation state
    if 'delete_confirm_task' not in st.session_state:
        st.session_state.delete_confirm_task = None

    if delete_clicked and task_key_input:
        task_key = task_key_input.strip().upper()

        if not task_key:
            st.warning("⚠️ Task Key kiriting!")
        else:
            # Taskni tekshirish - yangi connection ochish (to'g'ri ma'lumot olish uchun)
            check_conn = None
            try:
                check_conn = sqlite3.connect(db_path, timeout=30.0)
                check_conn.row_factory = sqlite3.Row
                cursor = check_conn.cursor()
                cursor.execute("SELECT task_id, task_status, service1_status, service2_status FROM task_processing WHERE task_id = ?", (task_key,))
                task = cursor.fetchone()

                if not task:
                    st.warning(f"⚠️ Task `{task_key}` bazada topilmadi")
                    st.session_state.delete_confirm_task = None
                else:
                    # Tasdiqlash state'ga saqlash
                    st.session_state.delete_confirm_task = {
                        'task_id': task_key,
                        'task_status': task['task_status'],
                        'service1_status': task['service1_status'],
                        'service2_status': task['service2_status']
                    }
                    st.rerun()
            finally:
                if check_conn:
                    check_conn.close()

    # Tasdiqlash dialog (agar delete_confirm_task set bo'lsa)
    if st.session_state.delete_confirm_task:
        task_info = st.session_state.delete_confirm_task
        task_key = task_info['task_id']

        st.warning(
            f"**{task_key}** o'chiriladi: "
            f"status={task_info['task_status']}, "
            f"s1={task_info['service1_status']}, "
            f"s2={task_info['service2_status']}"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button(f"✅ Ha, o'chirish", type="primary", key="confirm_delete_yes"):
                try:
                    from utils.database.task_db import delete_task, DB_FILE
                    import logging

                    # Logger yaratish
                    logger = logging.getLogger(__name__)

                    # DB_FILE va db_path bir xil ekanligini tekshirish
                    if DB_FILE != db_path:
                        st.warning(f"⚠️ DB path mos kelmaydi: {DB_FILE} vs {db_path}")
                        logger.warning(f"DB path mismatch: {DB_FILE} vs {db_path}")

                    logger.info(f"[{task_key}] UI'dan delete qilish boshlandi...")

                    # Delete qilish
                    success = delete_task(task_key)
                    logger.info(f"[{task_key}] delete_task result: {success}")

                    if success:
                        # Kichik kutish (DB commit uchun)
                        import time
                        time.sleep(0.2)  # 200ms kutish

                        # Delete qilinganini tekshirish - yangi connection (fresh data uchun)
                        verify_conn = sqlite3.connect(db_path, timeout=30.0)
                        # WAL mode checkpoint (agar WAL mode bo'lsa)
                        verify_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                        verify_cursor = verify_conn.cursor()
                        verify_cursor.execute("SELECT task_id FROM task_processing WHERE task_id = ?", (task_key,))
                        still_exists = verify_cursor.fetchone()
                        verify_conn.close()

                        logger.info(f"[{task_key}] Verification: still_exists={still_exists}")

                        if still_exists:
                            st.error(f"❌ `{task_key}` o'chirilmadi - bazada hali ham mavjud! Qayta urinib ko'ring.")
                            logger.error(f"[{task_key}] Task hali ham DB da mavjud!")
                        else:
                            # Success state
                            st.session_state.delete_success = True
                            st.session_state.delete_task_key = task_key
                            st.session_state.delete_confirm_task = None  # Confirmation dialog'ni yopish
                            # Input field'ni tozalash uchun counter'ni oshirish
                            if 'delete_task_key_input_counter' not in st.session_state:
                                st.session_state.delete_task_key_input_counter = 0
                            st.session_state.delete_task_key_input_counter += 1
                            logger.info(f"[{task_key}] ✅ UI'dan muvaffaqiyatli o'chirildi")
                            st.rerun()
                    else:
                        st.error(f"❌ `{task_key}` o'chirishda xato - funksiya False qaytardi")
                        logger.error(f"[{task_key}] delete_task False qaytardi")
                except Exception as e:
                    st.error(f"❌ Xato: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
                    logger.error(f"[{task_key}] Delete exception: {e}", exc_info=True)

        with col2:
            if st.button("❌ Yo'q, bekor qilish", key="confirm_delete_no"):
                st.session_state.delete_confirm_task = None
                st.rerun()
