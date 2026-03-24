"""
Sprint Report Page - Streamlit UI

Sprint bo'yicha task statistikasi va tahlil

Author: JASUR TURGUNOV
Version: 1.2
"""
import sys
import os
import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# DB fayl yo'li - project root/data papkasi
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DB_FILE = os.path.join(_PROJECT_ROOT, 'data', 'processing.db')


def _get_issue_types() -> list:
    """
    Sozlamalardan ruxsat etilgan issue type'larni olish.
    TZPRCheckerSettings.allowed_issue_types dan o'qiladi.

    Qaytaradi: ['DEV-BUG', 'DEV- PROD TASK', 'DEV-TECHTASK', 'DEV-CLIENT TASK']
    """
    try:
        if _PROJECT_ROOT not in sys.path:
            sys.path.insert(0, _PROJECT_ROOT)
        from config.app_settings import get_app_settings
        settings = get_app_settings()
        raw = settings.tz_pr_checker.allowed_issue_types
        if raw and raw.strip():
            return [t.strip() for t in raw.split(',') if t.strip()]
    except Exception:
        pass
    return []


# Feature nomlaridan shovqinli (ma'nosiz) papkalar filtri
_NOISE_FEATURES = {
    # Til fayllari
    'lang_ru', 'lang_en', 'lang_uz', 'lang_ar', 'lang_kk',
    'lang_ro', 'lang_tr', 'lang_de', 'lang_fr', 'lang_zh',
    # Umumiy papkalar
    'form', 'init', 'src', 'main', 'rep', 'pref', 'setup',
    'migr', 'test', 'tests', 'util', 'utils', 'common',
    'shared', 'base', 'core', 'config', 'resources',
    'assets', 'static', 'templates', 'page', 'pages',
    'view', 'views', 'api', 'web', 'module', 'ui', 'uis',
}


def _load_data_from_db(days: int, limit: int, issue_types: list) -> dict:
    """SQLite DB dan sprint ma'lumotlarini to'g'ridan-to'g'ri o'qish"""
    conn = sqlite3.connect(_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

    # 1. Jami tasklar soni
    cursor.execute(
        "SELECT COUNT(*) as total FROM task_processing WHERE created_at >= ?",
        (cutoff_date,)
    )
    total_tasks = cursor.fetchone()['total']

    # 2. Task turi bo'yicha taqsimot — DB dagi barcha haqiqiy qiymatlar
    cursor.execute("""
        SELECT
            COALESCE(task_type, 'Noma''lum') as task_type,
            COUNT(*) as count
        FROM task_processing
        WHERE created_at >= ?
        GROUP BY task_type
        ORDER BY count DESC
    """, (cutoff_date,))
    task_by_type = [
        {
            'task_type': row['task_type'],
            'count': row['count'],
            'percentage': round(row['count'] / total_tasks * 100, 2) if total_tasks > 0 else 0
        }
        for row in cursor.fetchall()
    ]

    # 3. Top features — feature_name CSV ni split qilib individual modullarni hisoblash
    # feature_name DB da: "anor, mkw, mfm" → split → anor +1, mkw +1, mfm +1
    cursor.execute("""
        SELECT
            feature_name,
            COALESCE(task_type, 'Noma''lum') as task_type,
            COUNT(*) as task_count
        FROM task_processing
        WHERE created_at >= ?
          AND feature_name IS NOT NULL
          AND feature_name != ''
        GROUP BY feature_name, task_type
    """, (cutoff_date,))
    raw_rows = cursor.fetchall()

    # Pivot: {module_name: {task_type: count, '_total': n}}
    feature_data: dict = {}
    all_task_types: set = set()

    for row in raw_rows:
        feature_csv = row['feature_name']
        ttype       = row['task_type']
        cnt         = row['task_count']

        # CSV string → individual modullar
        modules = [m.strip() for m in feature_csv.split(',') if m.strip()]

        for mod in modules:
            # Shovqinli va juda qisqa nomlarni o'tkazib yuborish
            if mod in _NOISE_FEATURES or len(mod) <= 2:
                continue
            if mod not in feature_data:
                feature_data[mod] = {'_total': 0}
            feature_data[mod][ttype]  = feature_data[mod].get(ttype, 0) + cnt
            feature_data[mod]['_total'] += cnt
            all_task_types.add(ttype)

    # Total bo'yicha tartiblash va limit qo'llash
    sorted_features = sorted(
        feature_data.items(),
        key=lambda x: x[1]['_total'],
        reverse=True
    )[:limit]

    # Ustunlar tartibi: settings → DB → fallback
    known_types = [t for t in issue_types if t in all_task_types]
    if not known_types:
        # Eski format (product/error/bug) yoki settings mos kelmasa
        known_types = sorted(all_task_types - {'Noma\'lum'})
        if 'Noma\'lum' in all_task_types:
            known_types.append('Noma\'lum')

    top_features = []
    for fname, types in sorted_features:
        entry = {'feature_name': fname, 'total_tasks': types['_total']}
        known_sum = 0
        for itype in known_types:
            val = types.get(itype, 0)
            entry[itype] = val
            known_sum += val
        other_val = types['_total'] - known_sum
        if other_val > 0:
            entry['other'] = other_val
        top_features.append(entry)

    actual_types = known_types

    # 4. PR topilmagan tasklar
    cursor.execute("""
        SELECT COUNT(*) as n
        FROM task_processing
        WHERE created_at >= ?
          AND service1_status = 'error'
          AND service1_error LIKE '%PR topilmadi%'
    """, (cutoff_date,))
    no_pr_count = cursor.fetchone()['n']

    # 5. Developer workload — DB dagi haqiqiy status qiymatlariga moslashgan
    cursor.execute("""
        SELECT
            COALESCE(assignee, 'Unassigned') as assignee,
            COUNT(*) as total_tasks,
            SUM(CASE WHEN task_status = 'completed'   THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN task_status = 'progressing' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN task_status = 'returned'    THEN 1 ELSE 0 END) as returned,
            SUM(CASE WHEN task_status = 'error'       THEN 1 ELSE 0 END) as processing_error,
            AVG(compliance_score) as avg_compliance_score
        FROM task_processing
        WHERE created_at >= ?
          AND assignee IS NOT NULL
        GROUP BY assignee
        ORDER BY total_tasks DESC
    """, (cutoff_date,))
    developer_workload = [
        {
            'assignee':            row['assignee'],
            'total_tasks':         row['total_tasks'],
            'completed':           row['completed'],
            'in_progress':         row['in_progress'],
            'returned':            row['returned'],
            'processing_error':    row['processing_error'],
            'avg_compliance_score': round(row['avg_compliance_score'], 2)
                                    if row['avg_compliance_score'] else None
        }
        for row in cursor.fetchall()
    ]

    conn.close()

    return {
        'period':             f"So'nggi {days} kun",
        'total_tasks':        total_tasks,
        'no_pr_count':        no_pr_count,
        'task_by_type':       task_by_type,
        'top_features':       top_features,
        'developer_workload': developer_workload,
        'issue_types':        issue_types,
        'actual_types':       actual_types,
        'generated_at':       datetime.now().isoformat()
    }


def render_sprint_report():
    """Main entry point for Sprint Report page"""
    st.title("📈 Sprint Report")
    st.markdown("Sprint bo'yicha task statistikasi va tahlil")

    # Issue types sozlamalardan
    issue_types = _get_issue_types()

    # Sidebar controls
    with st.sidebar:
        st.subheader("⚙️ Sozlamalar")
        days = st.slider("Davr (kunlar)", 1, 90, 7, help="Qancha kunlik ma'lumot ko'rsatilsin")
        limit = st.slider("Top features soni", 5, 50, 10, help="Eng ko'p ishlangan features soni")

        st.divider()
        if issue_types:
            st.caption("📋 Faol Issue Type'lar:")
            for itype in issue_types:
                st.caption(f"• {itype}")
        else:
            st.warning("⚠️ Sozlamada Issue Type'lar yo'q.\nTizim Sozlamalari → TZ-PR Checker → Ruxsat etilgan Issue Type'lar")

    # DB mavjudligini tekshirish
    if not os.path.exists(_DB_FILE):
        st.error(f"❌ DB fayl topilmadi: `{_DB_FILE}`")
        st.info("💡 Webhook birinchi marta ishlagandan keyin DB yaratiladi.")
        return

    # DB dan ma'lumot o'qish
    try:
        with st.spinner("Ma'lumotlar yuklanmoqda..."):
            data = _load_data_from_db(days=days, limit=limit, issue_types=issue_types)
    except Exception as e:
        st.error(f"❌ DB xatosi: {e}")
        return

    if data['total_tasks'] == 0:
        st.info(f"📭 So'nggi {days} kunda ma'lumot topilmadi. Davr filterini kengaytiring.")
        return

    # Render sections
    _render_overview_metrics(data)
    st.divider()
    _render_task_type_chart(data)
    st.divider()
    _render_top_features(data)
    st.divider()
    _render_developer_workload(data)

    # Footer
    st.caption(
        f"📅 Generatsiya vaqti: "
        f"{datetime.fromisoformat(data['generated_at']).strftime('%Y-%m-%d %H:%M:%S')}"
    )


def _render_overview_metrics(data):
    """Overview KPIs — DB dagi haqiqiy task type'lar bo'yicha metric kartalar"""
    st.subheader("📊 Umumiy Ko'rinish")

    task_by_type = data.get('task_by_type', [])
    no_pr_count  = data.get('no_pr_count', 0)

    # Jami + har bir task_type + PR yo'q
    items = [('📦 Jami Tasklar', data['total_tasks'], None)]
    for item in task_by_type:
        items.append((item['task_type'], item['count'], None))
    items.append(('🔗 PR topilmadi', no_pr_count, 'inverse' if no_pr_count > 0 else None))

    # Har qatorda max 6 ta ustun
    for row_start in range(0, len(items), 6):
        row_items = items[row_start:row_start + 6]
        cols = st.columns(len(row_items))
        for col, (label, value, delta_color) in zip(cols, row_items):
            with col:
                if delta_color:
                    # PR topilmadi — qizil rang bilan ko'rsatish
                    st.metric(label, value, delta=f"{value} ta", delta_color=delta_color)
                else:
                    st.metric(label, value)


def _render_task_type_chart(data):
    """Donut pie chart — task turlari taqsimoti"""
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
            hole=0.35,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.dataframe(
            df[['task_type', 'count', 'percentage']].rename(columns={
                'task_type': 'Tur',
                'count': 'Soni',
                'percentage': 'Foiz %'
            }),
            width='stretch',
            hide_index=True
        )


def _render_top_features(data):
    """
    Top Features — gorizontal stacked bar chart + jadval.

    Yaxshilanishlar (v1.2):
    - Dinamik ustunlar (allowed_issue_types dan)
    - Gorizontal chart (uzun feature nomlari uchun qulay)
    - Avtomatik balandlik (feature soni bo'yicha)
    - Jadvalda ProgressColumn (Jami ustuni)
    """
    st.subheader("🏗️ Top Features (eng ko'p ishlangan)")

    if not data['top_features']:
        st.info("Ma'lumot yo'q")
        return

    # DB dagi haqiqiy type'lar (settings emas)
    actual_types = data.get('actual_types', data.get('issue_types', []))
    df = pd.DataFrame(data['top_features'])

    # Gorizontal stacked bar chart
    fig = go.Figure()

    palette = px.colors.qualitative.Plotly

    # Faqat qiymati > 0 bo'lgan ustunlarni ko'rsatish
    cols_to_show = [t for t in actual_types if t in df.columns and df[t].sum() > 0]
    if 'other' in df.columns and df['other'].sum() > 0:
        cols_to_show.append('other')

    for i, col in enumerate(cols_to_show):
        label = col if col != 'other' else '🔹 Boshqa'
        fig.add_trace(go.Bar(
            name=label,
            y=df['feature_name'],
            x=df[col],
            orientation='h',
            marker_color=palette[i % len(palette)],
            text=df[col].apply(lambda v: str(int(v)) if v > 0 else ''),
            textposition='inside',
            insidetextanchor='middle'
        ))

    chart_height = max(350, len(df) * 42 + 130)
    fig.update_layout(
        barmode='stack',
        title=f"Feature bo'yicha Task Taqsimoti ({data['period']})",
        xaxis_title='Task soni',
        yaxis_title='',
        height=chart_height,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        yaxis=dict(autorange='reversed'),  # Yuqori — eng ko'p ishlangan
        margin=dict(l=10, r=10, t=80, b=30)
    )

    st.plotly_chart(fig, width='stretch')

    # Jadval — ProgressColumn bilan
    display_cols = {'feature_name': 'Feature', 'total_tasks': 'Jami'}
    for t in actual_types:
        if t in df.columns:
            display_cols[t] = t
    if 'other' in df.columns:
        display_cols['other'] = 'Boshqa'

    max_total = int(df['total_tasks'].max()) if not df.empty else 1

    st.dataframe(
        df[list(display_cols.keys())].rename(columns=display_cols),
        column_config={
            'Jami': st.column_config.ProgressColumn(
                'Jami',
                help="Jami task soni",
                min_value=0,
                max_value=max_total,
                format="%d"
            )
        },
        width='stretch',
        hide_index=True
    )


def _render_developer_workload(data):
    """Developer Workload — haqiqiy DB status'lar asosida jadval"""
    st.subheader("👥 Developer Workload")

    if not data['developer_workload']:
        st.info("Ma'lumot yo'q")
        return

    df = pd.DataFrame(data['developer_workload'])

    # Compliance score formatlash
    df['avg_compliance_score'] = df['avg_compliance_score'].apply(
        lambda x: f"{x}%" if x is not None else "—"
    )

    # Faqat qiymati > 0 bo'lgan statuslarni ko'rsatish
    rename_map = {
        'assignee':         'Developer',
        'total_tasks':      'Jami',
        'completed':        '✅ Tugallangan',
        'avg_compliance_score': "📊 Moslik",
    }
    cols_to_show = ['assignee', 'total_tasks', 'completed', 'avg_compliance_score']

    if df['in_progress'].sum() > 0:
        rename_map['in_progress'] = '🔄 Jarayonda'
        cols_to_show.insert(3, 'in_progress')

    if df['returned'].sum() > 0:
        rename_map['returned'] = '↩️ Qaytarilgan'
        cols_to_show.insert(-1, 'returned')

    if df['processing_error'].sum() > 0:
        rename_map['processing_error'] = '⚠️ Xatolik'
        cols_to_show.insert(-1, 'processing_error')

    max_total = int(df['total_tasks'].max()) if not df.empty else 1

    st.dataframe(
        df[cols_to_show].rename(columns=rename_map),
        column_config={
            'Jami': st.column_config.ProgressColumn(
                'Jami',
                help="Jami task soni",
                min_value=0,
                max_value=max_total,
                format="%d"
            )
        },
        width='stretch',
        hide_index=True
    )
