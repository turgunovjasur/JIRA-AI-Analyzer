"""
Sprint Monitoring Dashboard — Streamlit UI

JIRA API dan sprint ma'lumotlarini olish va vizualizatsiya.
6 ta asosiy bo'lim (tab):
  1. Sprint Overview — umumiy holat, burndown, progress
  2. Developer Performance — samaradorlik, kechikish, velocity
  3. Task Pipeline — kanban ko'rinish
  4. Bottleneck Analyzer — tiqilish nuqtalari
  5. QA & Testing — test statistikasi
  6. Sprint Comparison — sprintlarni taqqoslash

Author: JASUR TURGUNOV
Version: 2.0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, List, Any

from services.sprint_data_service import (
    SprintDataService, WORK_HOURS_PER_DAY, STATUS_PIPELINE, STATUS_EXCEPTION,
    _status_group,
)


# ═════════════════════════════════════════════════════════════════════════════
# CACHE — API chaqiruvlarini kamaytirir
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_resource(ttl=300)
def _get_service(user_id: int = None, company_id: int = None) -> SprintDataService:
    return SprintDataService(user_id=user_id, company_id=company_id)


@st.cache_data(ttl=300)
def _fetch_boards(project_key: str, user_id: int = None):
    return _get_service(user_id=user_id).get_boards(project_key)


@st.cache_data(ttl=300)
def _fetch_sprints(board_id: int, state: str, user_id: int = None):
    return _get_service(user_id=user_id).get_sprints(board_id, state)


@st.cache_data(ttl=300)
def _fetch_sprint_issues(sprint_id: int, user_id: int = None):
    svc = _get_service(user_id=user_id)
    return svc.jira.get_sprint_issues_full(sprint_id)


def _get_user_id() -> int | None:
    from utils.auth.auth_manager import get_auth_info
    auth = get_auth_info()
    return auth.get('user_id') if auth.get('role') == 'user' else None


# ═════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

def render_sprint_report():
    st.title("📈 Sprint Monitoring Dashboard")

    _uid = _get_user_id()
    svc = _get_service(user_id=_uid)

    # ── SIDEBAR — Sprint tanlash ────────────────────────────────────────
    with st.sidebar:
        st.subheader("🎯 Sprint tanlash")

        project_key = st.text_input("Loyiha kaliti", value="DEV")
        boards = _fetch_boards(project_key, _uid)

        if not boards:
            st.warning("Board topilmadi. JIRA ulanishini tekshiring.")
            st.info("💡 Sozlamalar → API Kalitlar bo'limini tekshiring")
            return

        board_names = {b['name']: b['id'] for b in boards}
        selected_board_name = st.selectbox("Board", list(board_names.keys()))
        board_id = board_names[selected_board_name]

        sprint_state = st.selectbox("Sprint holati", ['active,closed', 'active', 'closed', 'future'])
        sprints = _fetch_sprints(board_id, sprint_state, _uid)

        if not sprints:
            st.warning("Sprint topilmadi.")
            return

        sprint_names = {s['name']: s for s in sprints}
        selected_sprint_name = st.selectbox(
            "Sprint",
            list(sprint_names.keys()),
            index=0,
        )
        selected_sprint = sprint_names[selected_sprint_name]

        # Developer kapasiteti
        st.divider()
        st.subheader("👤 Developer kapasiteti")
        st.caption("SP / kun (ish kuni = 8 soat)")

        # Sprint yuklash (cached)
        issues_raw = _fetch_sprint_issues(selected_sprint['id'], _uid)
        svc.load_sprint(selected_sprint, issues_raw)

        dev_names = sorted(set(
            t.assignee for t in svc.tasks if t.assignee != 'Unassigned'
        ))

        dev_caps: Dict[str, float] = {}
        default_cap = st.number_input(
            "Default kapasitet (barcha uchun)",
            min_value=0.5, max_value=20.0, value=2.0, step=0.5,
            key="default_cap",
        )
        for dev in dev_names:
            cap = st.number_input(
                dev, min_value=0.5, max_value=20.0, value=default_cap, step=0.5,
                key=f"cap_{dev}",
            )
            dev_caps[dev] = cap

        svc.set_dev_capacities(dev_caps)

        # Refresh
        st.divider()
        if st.button("🔄 Ma'lumotlarni yangilash", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ── MA'LUMOT YUKLANDI — SAHIFALAR ──────────────────────────────────

    if not svc.tasks:
        st.warning("Sprint da task topilmadi.")
        return

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Sprint Overview",
        "👤 Developer Performance",
        "📋 Task Pipeline",
        "🔍 Bottleneck Analyzer",
        "🧪 QA & Testing",
        "📈 Sprint Comparison",
    ])

    with tab1:
        _render_sprint_overview(svc)
    with tab2:
        _render_developer_performance(svc)
    with tab3:
        _render_task_pipeline(svc)
    with tab4:
        _render_bottleneck(svc)
    with tab5:
        _render_qa_testing(svc)
    with tab6:
        _render_sprint_comparison(svc, board_id, user_id=_uid)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — SPRINT OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════

def _render_sprint_overview(svc: SprintDataService):
    data = svc.get_sprint_overview()
    if not data:
        st.info("Ma'lumot yo'q")
        return

    # ── Sprint Info Card ────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sprint", data['sprint_name'])
    c2.metric("Boshlanish", data['start_date'].strftime('%d.%m') if data['start_date'] else '—')
    c3.metric("Tugash", data['end_date'].strftime('%d.%m') if data['end_date'] else '—')
    remaining = data['remaining_days']
    c4.metric("Qolgan kunlar", f"{remaining} kun",
              delta=f"{remaining} kun", delta_color="inverse" if remaining < 3 else "normal")

    # ── Progress Bar ────────────────────────────────────────────────────
    pct = data['progress_pct']
    color = '#4CAF50' if pct >= 80 else ('#FFC107' if pct >= 50 else '#F44336')
    st.markdown(f"""
    <div style="background:#333;border-radius:10px;height:30px;margin:10px 0;">
        <div style="background:{color};border-radius:10px;height:30px;width:{min(pct,100)}%;
                    display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;">
            {pct}%
        </div>
    </div>""", unsafe_allow_html=True)

    # ── SP Breakdown Metrics ────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Jami SP", data['total_sp'])
    m2.metric("Bajarilgan SP", data['completed_sp'])
    m3.metric("Jarayonda SP", data['in_progress_sp'])
    m4.metric("Qolgan SP", data['remaining_sp'])

    risk = data['risk_score']
    risk_label = "Yaxshi" if risk < 0.8 else ("O'rtacha" if risk < 1.0 else "Xavfli")
    risk_delta_color = "normal" if risk < 0.8 else ("off" if risk < 1.0 else "inverse")
    m5.metric("Risk", risk_label, delta=f"{risk:.2f}", delta_color=risk_delta_color)

    col_left, col_right = st.columns(2)

    # ── SP Breakdown Donut ──────────────────────────────────────────────
    with col_left:
        fig = go.Figure(data=[go.Pie(
            labels=['Bajarilgan', 'Jarayonda', 'Qolgan'],
            values=[data['completed_sp'], data['in_progress_sp'],
                    max(data['remaining_sp'] - data['in_progress_sp'], 0)],
            hole=0.45,
            marker_colors=['#4CAF50', '#2196F3', '#9E9E9E'],
        )])
        fig.update_layout(title='SP Taqsimoti', height=350, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    # ── Burndown Chart ──────────────────────────────────────────────────
    with col_right:
        bd = data['burndown']
        if bd['dates']:
            fig = go.Figure()
            fig.add_scatter(x=bd['dates'], y=bd['ideal'], name='Ideal',
                            line=dict(dash='dash', color='#9E9E9E'))
            if bd['actual']:
                fig.add_scatter(x=bd['dates'][:len(bd['actual'])], y=bd['actual'],
                                name='Haqiqiy', line=dict(color='#F44336', width=2))
            fig.update_layout(title='Burndown Chart', xaxis_title='Kun',
                              yaxis_title='Qolgan SP', height=350)
            st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)

    # ── Daily Velocity ──────────────────────────────────────────────────
    with col_a:
        dv = data['daily_velocity']
        if dv:
            fig = px.bar(
                pd.DataFrame(dv), x='date', y='sp',
                title='Kunlik bajarilgan SP', labels={'date': '', 'sp': 'SP'},
                color_discrete_sequence=['#2196F3'],
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # ── Status Distribution ─────────────────────────────────────────────
    with col_b:
        sd = data['status_distribution']
        if sd:
            df_sd = pd.DataFrame([
                {'Status': k, 'Tasklar': v} for k, v in sd.items()
            ])
            fig = px.bar(
                df_sd, y='Status', x='Tasklar', orientation='h',
                title='Status bo\'yicha task soni',
                color_discrete_sequence=['#FF9800'],
                text='Tasklar',
            )
            fig.update_traces(textposition='outside')
            fig.update_layout(height=300, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — DEVELOPER PERFORMANCE
# ═════════════════════════════════════════════════════════════════════════════

def _render_developer_performance(svc: SprintDataService):
    dev_stats = svc.get_developer_stats()
    if not dev_stats:
        st.info("Ma'lumot yo'q")
        return

    # ── Developer selector ──────────────────────────────────────────────
    dev_names = [d['name'] for d in dev_stats]
    selected_dev = st.selectbox("Developer tanlang", ["Barcha"] + dev_names)

    if selected_dev == "Barcha":
        _render_all_devs_summary(dev_stats)
    else:
        dev = next(d for d in dev_stats if d['name'] == selected_dev)
        _render_single_dev(dev, svc)


def _render_all_devs_summary(dev_stats: List[Dict]):
    """Barcha developerlar jadvali"""
    rows = []
    for d in dev_stats:
        delay_label = ""
        if d['total_delay_days'] > 1:
            delay_label = f"🔴 +{d['total_delay_days']:.1f} kun"
        elif d['total_delay_days'] > 0:
            delay_label = f"🟡 +{d['total_delay_days']:.1f} kun"
        else:
            delay_label = "🟢 Vaqtida"

        rows.append({
            'Developer': d['name'],
            'Tasklar': d['total_tasks'],
            'Jami SP': d['assigned_sp'],
            'Bajarilgan SP': d['completed_sp'],
            'Qolgan SP': d['remaining_sp'],
            'Velocity (SP/kun)': d['velocity_per_day'],
            'Kechikish (kun)': d['total_delay_days'],
            'Yo\'qotilgan SP': d['total_delay_sp'],
            'First Pass %': d['first_pass_rate'],
            'Qaytarilgan': d['returned_count'],
            'Holat': delay_label,
        })

    df = pd.DataFrame(rows)

    # ── Ajratilgan vs Bajarilgan bar chart ──────────────────────────────
    fig = go.Figure()
    fig.add_bar(name='Ajratilgan SP', x=df['Developer'], y=df['Jami SP'],
                marker_color='#4CAF50', text=df['Jami SP'], textposition='outside')
    fig.add_bar(name='Bajarilgan SP', x=df['Developer'], y=df['Bajarilgan SP'],
                marker_color='#2196F3', text=df['Bajarilgan SP'], textposition='outside')
    fig.update_layout(barmode='group', title='Developer SP holati',
                      yaxis_title='SP', height=400)
    st.plotly_chart(fig, use_container_width=True)

    # ── Jadval ──────────────────────────────────────────────────────────
    st.dataframe(df, hide_index=True, use_container_width=True)


def _render_single_dev(dev: Dict, svc: SprintDataService):
    """Bitta developer tafsiloti"""

    # ── Velocity Gauge ──────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jami SP", dev['assigned_sp'])
    c2.metric("Bajarilgan SP", dev['completed_sp'])
    c3.metric("Velocity", f"{dev['velocity_per_day']} SP/kun")
    c4.metric("First Pass Rate", f"{dev['first_pass_rate']}%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Jarayonda SP", dev['in_progress_sp'])
    c6.metric("Qolgan SP", dev['remaining_sp'])
    delay = dev['total_delay_days']
    c7.metric("Kechikish", f"{delay:.1f} kun",
              delta=f"+{delay:.1f}" if delay > 0 else f"{delay:.1f}",
              delta_color="inverse" if delay > 0.5 else "normal")
    c8.metric("Qaytarilgan", dev['returned_count'])

    # ── Kechikish jadvali ───────────────────────────────────────────────
    st.markdown("#### Task bo'yicha kechikish tahlili")
    tasks = dev['task_details']
    df = pd.DataFrame(tasks)

    if not df.empty:
        def _flag(row):
            d = row.get('delay_days')
            if d is None:
                return "⚪ Hali jarayonda"
            if d > 1:
                return f"🔴 +{d:.1f} kun kech"
            if d > 0:
                return f"🟠 +{d:.1f} kun kech"
            if d < -0.5:
                return f"🟢 {abs(d):.1f} kun erta"
            return "🟡 Vaqtida"

        df['Holat'] = df.apply(_flag, axis=1)
        df = df.rename(columns={
            'key': 'Task', 'summary': 'Sarlavha', 'status': 'Status',
            'story_points': 'SP', 'expected_days': 'Kerak edi (kun)',
            'actual_days': 'Ketdi (kun)', 'delay_days': 'Kechikish (kun)',
            'delay_sp': 'Yo\'qotilgan SP',
        })
        df = df.sort_values('Kechikish (kun)', ascending=False, na_position='last')
        st.dataframe(
            df[['Task', 'Sarlavha', 'SP', 'Kerak edi (kun)', 'Ketdi (kun)',
                'Kechikish (kun)', 'Yo\'qotilgan SP', 'Holat', 'Status']],
            hide_index=True, use_container_width=True,
        )

    # ── SP Progress stacked bar ─────────────────────────────────────────
    fig = go.Figure(data=[
        go.Bar(name='Bajarilgan', x=['SP'], y=[dev['completed_sp']], marker_color='#4CAF50'),
        go.Bar(name='Jarayonda', x=['SP'], y=[dev['in_progress_sp']], marker_color='#2196F3'),
        go.Bar(name='Qolgan', x=['SP'], y=[dev['remaining_sp']], marker_color='#9E9E9E'),
    ])
    fig.update_layout(barmode='stack', height=250, title='SP holati')
    st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — TASK PIPELINE (Kanban)
# ═════════════════════════════════════════════════════════════════════════════

def _render_task_pipeline(svc: SprintDataService):
    pipeline = svc.get_pipeline_data()

    # Filtrlash
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        dev_filter = st.selectbox(
            "Developer filtr",
            ["Barcha"] + sorted(set(t.assignee for t in svc.tasks if t.assignee != 'Unassigned')),
            key="pipeline_dev",
        )
    with col_f2:
        show_stuck = st.checkbox("Faqat tiqilganlarni ko'rsatish (3+ kun)", key="pipeline_stuck")

    # Kanban ustunlari
    all_statuses = [s for s in STATUS_PIPELINE + STATUS_EXCEPTION if pipeline.get(s)]
    if not all_statuses:
        st.info("Tasklar topilmadi")
        return

    cols = st.columns(len(all_statuses))
    for col, status in zip(cols, all_statuses):
        cards = pipeline[status]

        # Filtrlash
        if dev_filter != "Barcha":
            cards = [c for c in cards if c['assignee'] == dev_filter]
        if show_stuck:
            cards = [c for c in cards if c.get('is_stuck')]

        with col:
            st.markdown(f"**{status}** ({len(cards)})")
            st.markdown("---")

            for card in cards:
                bg = '#5c1010' if card.get('is_stuck') else '#1a1a2e'
                border = '#F44336' if card.get('is_stuck') else '#333'
                st.markdown(f"""
                <div style="background:{bg};border:1px solid {border};border-radius:8px;
                            padding:8px;margin-bottom:6px;font-size:0.85em;">
                    <b>{card['key']}</b> <span style="color:#aaa">({card['story_points']} SP)</span><br>
                    <span style="color:#bbb">{card['summary'][:40]}{'...' if len(card['summary'])>40 else ''}</span><br>
                    <span style="color:#888">👤 {card['assignee']}</span>
                    <span style="color:#888"> | ⏱ {card['days_in_status']} kun</span>
                </div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — BOTTLENECK ANALYZER
# ═════════════════════════════════════════════════════════════════════════════

def _render_bottleneck(svc: SprintDataService):
    data = svc.get_bottleneck_data()
    if not data:
        st.info("Ma'lumot yo'q")
        return

    # ── Alertlar ────────────────────────────────────────────────────────
    alerts = data['alerts']
    if alerts:
        st.markdown(f"### ⚠️ Ogohlantirish ({len(alerts)} ta)")
        for a in sorted(alerts, key=lambda x: x['days'], reverse=True):
            icon = '🔴' if a['days'] > 3 else '🟡'
            st.warning(f"{icon} **{a['task']}** — {a['message']} (👤 {a['assignee']})")
    else:
        st.success("✅ Hozircha tiqilish yo'q")

    col1, col2 = st.columns(2)

    # ── Status bo'yicha o'rtacha vaqt ───────────────────────────────────
    with col1:
        ast_data = data['avg_status_time']
        if ast_data:
            df = pd.DataFrame([
                {'Status': k, "O'rtacha (kun)": v['avg_days'],
                 'Jami (soat)': v['total_hours'], 'Bottleneck score': v['bottleneck_score']}
                for k, v in ast_data.items()
            ]).sort_values('Bottleneck score', ascending=False)

            fig = px.bar(df, x='Status', y="O'rtacha (kun)",
                         color='Bottleneck score',
                         color_continuous_scale='YlOrRd',
                         title="Status bo'yicha o'rtacha vaqt (ish kun)",
                         text="O'rtacha (kun)")
            fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig.update_layout(height=400, coloraxis_showscale=False, xaxis_tickangle=-25)
            st.plotly_chart(fig, use_container_width=True)

    # ── Cycle Time ──────────────────────────────────────────────────────
    with col2:
        st.metric("O'rtacha Cycle Time", f"{data['avg_cycle_time_days']:.1f} ish kun",
                   help="IN PROGRESS → CLOSED")

        ct = data['cycle_times']
        if ct:
            fig = px.histogram(
                pd.DataFrame({'Cycle Time (kun)': ct}),
                x='Cycle Time (kun)', nbins=10,
                title='Cycle Time taqsimoti (ish kun)',
                color_discrete_sequence=['#2196F3'],
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # ── Heatmap ─────────────────────────────────────────────────────────
    hm = data['heatmap']
    if hm:
        st.markdown("### Developer × Status Heatmap (o'rtacha ish kun)")
        hm_df = pd.DataFrame(hm).T.fillna(0)
        ordered_cols = sorted(hm_df.columns.tolist(), key=lambda s: STATUS_PIPELINE.index(s) if s in STATUS_PIPELINE else 99)
        hm_df = hm_df[[c for c in ordered_cols if c in hm_df.columns]]

        fig = px.imshow(
            hm_df.round(1), text_auto='.1f', aspect='auto',
            color_continuous_scale='YlOrRd',
            labels={'color': 'Ish kun'},
        )
        fig.update_layout(height=max(300, len(hm_df) * 50), xaxis_tickangle=-25)
        st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — QA & TESTING
# ═════════════════════════════════════════════════════════════════════════════

def _render_qa_testing(svc: SprintDataService):
    qa = svc.get_qa_stats()
    if not qa:
        st.info("Ma'lumot yo'q")
        return

    # ── KPI lar ─────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Tekshirilgan", qa['total_tested'])
    c2.metric("First Pass Rate", f"{qa['first_pass_rate']}%")
    c3.metric("Qaytarilgan", qa['returned'],
              delta=str(qa['returned']), delta_color="inverse" if qa['returned'] > 0 else "normal")
    c4.metric("Clarification", qa['need_clarification'])
    c5.metric("O'rtacha QA vaqt", f"{qa['avg_qa_time_days']:.1f} kun")

    col1, col2 = st.columns(2)

    # ── Return Rate Pie ─────────────────────────────────────────────────
    with col1:
        fig = go.Figure(data=[go.Pie(
            labels=['CLOSED (sof)', 'RETURN TEST', 'NEED CLARIFICATION', 'REJECTED'],
            values=[qa['closed_clean'], qa['returned'],
                    qa['need_clarification'], qa['rejected']],
            hole=0.4,
            marker_colors=['#4CAF50', '#F44336', '#FFC107', '#9E9E9E'],
        )])
        fig.update_layout(title='Test natijalari taqsimoti', height=350)
        st.plotly_chart(fig, use_container_width=True)

    # ── Defect by Dev ───────────────────────────────────────────────────
    with col2:
        dbd = qa['defect_by_dev']
        if dbd:
            df = pd.DataFrame([
                {'Developer': k, 'Qaytarilgan': v} for k, v in dbd.items()
            ]).sort_values('Qaytarilgan', ascending=False)

            fig = px.bar(df, x='Developer', y='Qaytarilgan',
                         title='Developer bo\'yicha qaytarilgan tasklar',
                         color='Qaytarilgan', color_continuous_scale='Reds',
                         text='Qaytarilgan')
            fig.update_traces(textposition='outside')
            fig.update_layout(height=350, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("Qaytarilgan task yo'q!")

    # ── QA Queue ────────────────────────────────────────────────────────
    st.markdown("### QA navbati")
    if qa['qa_queue']:
        df = pd.DataFrame(qa['qa_queue']).rename(columns={
            'key': 'Task', 'summary': 'Sarlavha', 'assignee': 'Developer',
            'story_points': 'SP', 'status': 'Status',
        })
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("QA navbati bo'sh.")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 6 — SPRINT COMPARISON
# ═════════════════════════════════════════════════════════════════════════════

def _render_sprint_comparison(svc: SprintDataService, board_id: int, user_id: int = None):
    st.markdown("### Sprintlarni taqqoslash")

    all_sprints = _fetch_sprints(board_id, 'active,closed', user_id)
    if len(all_sprints) < 2:
        st.info("Taqqoslash uchun kamida 2 ta sprint kerak.")
        return

    sprint_options = {s['name']: s for s in all_sprints}
    selected_names = st.multiselect(
        "Sprintlarni tanlang (2-5 ta)",
        list(sprint_options.keys()),
        default=list(sprint_options.keys())[:2],
        max_selections=5,
    )

    if len(selected_names) < 2:
        st.info("Kamida 2 ta sprint tanlang.")
        return

    # Har bir sprint uchun summary olish
    summaries = []
    for name in selected_names:
        sp_meta = sprint_options[name]
        temp_svc = SprintDataService(user_id=user_id)
        temp_issues = _fetch_sprint_issues(sp_meta['id'], user_id)
        temp_svc.load_sprint(sp_meta, temp_issues)
        # Kapasitetlarni joriy sprint dan olish
        temp_svc.set_dev_capacities({d: c.velocity_per_day for d, c in svc.dev_capacities.items()})
        summaries.append(temp_svc.get_sprint_summary_for_comparison())

    df = pd.DataFrame(summaries)

    # ── Velocity Comparison ─────────────────────────────────────────────
    fig = go.Figure()
    fig.add_bar(name='Bajarilgan SP', x=df['sprint_name'], y=df['completed_sp'],
                marker_color='#4CAF50', text=df['completed_sp'], textposition='outside')
    fig.add_bar(name='Jami SP', x=df['sprint_name'], y=df['total_sp'],
                marker_color='#9E9E9E', text=df['total_sp'], textposition='outside')
    fig.update_layout(barmode='group', title='Sprint bo\'yicha SP holati',
                      yaxis_title='SP', height=400)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    # ── Quality Comparison ──────────────────────────────────────────────
    with col1:
        fig = px.bar(
            df, x='sprint_name', y='first_pass_rate',
            title='First Pass Rate (%)',
            color='first_pass_rate', color_continuous_scale='Greens',
            text='first_pass_rate',
        )
        fig.update_traces(texttemplate='%{text:.0f}%', textposition='outside')
        fig.update_layout(coloraxis_showscale=False, height=350)
        st.plotly_chart(fig, use_container_width=True)

    # ── Cycle Time ──────────────────────────────────────────────────────
    with col2:
        fig = px.bar(
            df, x='sprint_name', y='avg_cycle_time',
            title="O'rtacha Cycle Time (ish kun)",
            color='avg_cycle_time', color_continuous_scale='Blues',
            text='avg_cycle_time',
        )
        fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig.update_layout(coloraxis_showscale=False, height=350)
        st.plotly_chart(fig, use_container_width=True)

    # ── Umumiy jadval ───────────────────────────────────────────────────
    display = df.rename(columns={
        'sprint_name': 'Sprint',
        'total_sp': 'Jami SP',
        'completed_sp': 'Bajarilgan SP',
        'completion_pct': 'Bajarilish %',
        'team_velocity': 'Velocity (SP/kun)',
        'first_pass_rate': 'First Pass %',
        'avg_cycle_time': 'Cycle Time (kun)',
        'return_count': 'Qaytarilgan',
        'total_tasks': 'Tasklar',
        'developers_count': 'Developerlar',
    })
    st.dataframe(display, hide_index=True, use_container_width=True)
