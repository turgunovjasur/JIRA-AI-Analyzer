"""
Sprint Data Service — JIRA dan sprint ma'lumotlarini olish va hisob-kitob

Barcha dashboard sahifalari uchun yagona data source.
JIRA API dan olingan xom ma'lumotlarni qayta ishlab,
tayyor metrikalar va jadvallar qaytaradi.

Author: JASUR TURGUNOV
Version: 1.0
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import math

from core.logger import get_logger

_log = get_logger("sprint.data")

# ── Status guruhlari ────────────────────────────────────────────────────────
WORK_HOURS_PER_DAY = 8.0
SPRINT_WORK_DAYS = 10

STATUS_TODO = {'TO DO', 'BACKLOG', 'OPEN'}
STATUS_IN_PROGRESS = {'IN PROGRESS', 'IN DEVELOPMENT'}
STATUS_CODE_REVIEW = {'PULL REQUEST', 'CODE REVIEW'}
STATUS_MERGED = {'MERGED'}
STATUS_READY_TEST = {'READY TO TEST'}
STATUS_TESTING = {'TESTING'}
STATUS_DONE = {'CLOSED', 'DONE', 'RESOLVED'}
STATUS_RETURN = {'NEED CLARIFICATION/RETURN TEST', 'RETURN TEST'}
STATUS_REJECTED = {'REJECTED'}

# Tartibli ro'yxat (pipeline ketma-ketligi)
STATUS_PIPELINE = [
    'TO DO', 'IN PROGRESS', 'PULL REQUEST', 'MERGED',
    'READY TO TEST', 'TESTING', 'CLOSED',
]

STATUS_EXCEPTION = ['NEED CLARIFICATION/RETURN TEST', 'RETURN TEST', 'REJECTED']


def _upper(s: str) -> str:
    return (s or '').upper().strip()


def _status_group(status: str) -> str:
    """Status ni guruhga aylantirish"""
    s = _upper(status)
    if s in STATUS_TODO:
        return 'TO DO'
    if s in STATUS_IN_PROGRESS:
        return 'IN PROGRESS'
    if s in STATUS_CODE_REVIEW:
        return 'PULL REQUEST'
    if s in STATUS_MERGED:
        return 'MERGED'
    if s in STATUS_READY_TEST:
        return 'READY TO TEST'
    if s in STATUS_TESTING:
        return 'TESTING'
    if s in STATUS_DONE:
        return 'CLOSED'
    if s in STATUS_RETURN:
        return 'RETURN TEST'
    if s in STATUS_REJECTED:
        return 'REJECTED'
    return status


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    """JIRA timestamp ni datetime ga aylantirish"""
    if not ts:
        return None
    try:
        # '2026-03-20T09:15:00.000+0500' formatini parse
        clean = ts.replace('Z', '+00:00')
        if '.' in clean:
            # milliseconds + offset
            dt = datetime.fromisoformat(clean)
        else:
            dt = datetime.fromisoformat(clean)
        return dt.replace(tzinfo=None)  # naive datetime ga
    except Exception:
        try:
            return datetime.fromisoformat(ts[:19])
        except Exception:
            return None


def _pipeline_index(status: str) -> int:
    """Status ni pipeline tartib raqamiga"""
    g = _status_group(status)
    for i, s in enumerate(STATUS_PIPELINE):
        if g == s:
            return i
    return len(STATUS_PIPELINE)


def _work_days_between(start: datetime, end: datetime) -> float:
    """
    Ikki datetime orasidagi ish kunlari sonini hisoblash.
    Shanba-yakshanba hisobga olinmaydi, 1 ish kuni = 8 soat.
    """
    if end <= start:
        return 0.0

    total_work_hours = 0.0
    current = start

    while current < end:
        if current.weekday() < 5:  # Dushanba-Juma
            # Shu kundagi qolgan soatlar
            day_end = current.replace(hour=23, minute=59, second=59)
            chunk_end = min(end, day_end)
            hours = (chunk_end - current).total_seconds() / 3600
            total_work_hours += min(hours, WORK_HOURS_PER_DAY)

        # Keyingi kun boshiga
        current = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0)

    return round(total_work_hours / WORK_HOURS_PER_DAY, 2)


# ═════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class TaskTransition:
    from_status: str
    to_status: str
    timestamp: datetime
    author: str = ''


@dataclass
class TaskData:
    key: str
    summary: str
    issue_type: str
    status: str
    assignee: str
    story_points: float
    created: Optional[datetime]
    updated: Optional[datetime]
    resolved: Optional[datetime]
    transitions: List[TaskTransition] = field(default_factory=list)


@dataclass
class SprintInfo:
    id: int
    name: str
    state: str  # active, closed, future
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    total_days: int = SPRINT_WORK_DAYS


@dataclass
class StatusDuration:
    """Bitta task ning bitta statusda turgan vaqti"""
    task_key: str
    status: str
    hours: float
    assignee: str
    story_points: float


@dataclass
class DevCapacity:
    """Developer kapasiteti"""
    name: str
    velocity_per_day: float  # SP/kun
    capacity_per_sprint: float  # Jami SP sprint uchun


# ═════════════════════════════════════════════════════════════════════════════
# SPRINT DATA SERVICE
# ═════════════════════════════════════════════════════════════════════════════

class SprintDataService:
    """
    JIRA dan sprint ma'lumotlarini olish va qayta ishlash.

    Foydalanish:
        svc = SprintDataService()
        svc.load_sprint(board_id=123, sprint_id=456)
        overview = svc.get_sprint_overview()
        devs = svc.get_developer_stats()
    """

    def __init__(self, company_id: int = None, user_id: int = None):
        self._jira = None
        self._company_id = company_id
        self._user_id = user_id
        self.sprint: Optional[SprintInfo] = None
        self.tasks: List[TaskData] = []
        self.dev_capacities: Dict[str, DevCapacity] = {}
        self._status_durations: Optional[List[StatusDuration]] = None

    @property
    def jira(self):
        if self._jira is None:
            from utils.jira.jira_client import JiraClient
            if self._user_id is not None:
                from utils.auth.auth_db import get_user_credentials_for_service
                creds = get_user_credentials_for_service(self._user_id)
                self._jira = JiraClient(
                    server=creds['jira_server'],
                    email=creds['jira_email'],
                    token=creds['jira_token'],
                )
            elif self._company_id is not None:
                from utils.auth.auth_db import get_company_credentials
                creds = get_company_credentials(self._company_id)
                self._jira = JiraClient(
                    server=creds['jira_server'],
                    email=creds['jira_email'],
                    token=creds['jira_token'],
                )
            else:
                self._jira = JiraClient()
        return self._jira

    # ── Yuklab olish ────────────────────────────────────────────────────

    def get_boards(self, project_key: str = 'DEV') -> List[Dict]:
        return self.jira.get_boards(project_key)

    def get_sprints(self, board_id: int, state: str = 'active,closed') -> List[Dict]:
        return self.jira.get_sprints(board_id, state=state)

    def load_sprint(self, sprint_meta: Dict, issues_raw: Optional[List[Dict]] = None):
        """
        Sprint ma'lumotlarini yuklash va parse qilish.

        Args:
            sprint_meta: {'id', 'name', 'state', 'start_date', 'end_date'}
            issues_raw: Agar allaqachon yuklangan bo'lsa, qayta yuklamaslik uchun
        """
        self.sprint = SprintInfo(
            id=sprint_meta['id'],
            name=sprint_meta['name'],
            state=sprint_meta.get('state', 'unknown'),
            start_date=_parse_ts(sprint_meta.get('start_date')),
            end_date=_parse_ts(sprint_meta.get('end_date')),
        )

        # Kunlar hisobi
        if self.sprint.start_date and self.sprint.end_date:
            delta = (self.sprint.end_date - self.sprint.start_date).days
            # Faqat ish kunlari (shanba-yakshanba chiqariladi)
            work_days = 0
            d = self.sprint.start_date
            while d <= self.sprint.end_date:
                if d.weekday() < 5:
                    work_days += 1
                d += timedelta(days=1)
            self.sprint.total_days = work_days if work_days > 0 else delta

        if issues_raw is None:
            issues_raw = self.jira.get_sprint_issues_full(self.sprint.id)

        self.tasks = []
        for raw in issues_raw:
            transitions = []
            for t in raw.get('transitions', []):
                ts = _parse_ts(t.get('timestamp'))
                if ts:
                    transitions.append(TaskTransition(
                        from_status=t.get('from_status', ''),
                        to_status=t.get('to_status', ''),
                        timestamp=ts,
                        author=t.get('author', ''),
                    ))
            transitions.sort(key=lambda x: x.timestamp)

            self.tasks.append(TaskData(
                key=raw['key'],
                summary=raw.get('summary', ''),
                issue_type=raw.get('type', ''),
                status=raw.get('status', ''),
                assignee=raw.get('assignee', 'Unassigned'),
                story_points=float(raw.get('story_points', 0) or 0),
                created=_parse_ts(raw.get('created')),
                updated=_parse_ts(raw.get('updated')),
                resolved=_parse_ts(raw.get('resolved')),
                transitions=transitions,
            ))

        self._status_durations = None  # Cache tozalash
        _log.info(f"Sprint '{self.sprint.name}': {len(self.tasks)} task yuklandi")

    def set_dev_capacities(self, capacities: Dict[str, float]):
        """
        Developer kapasitetlarini o'rnatish.
        Args:
            capacities: {'Alisher': 2.0, 'Bobur': 3.0} — SP/kun
        """
        self.dev_capacities = {}
        sprint_days = self.sprint.total_days if self.sprint else SPRINT_WORK_DAYS
        for name, vel in capacities.items():
            self.dev_capacities[name] = DevCapacity(
                name=name,
                velocity_per_day=vel,
                capacity_per_sprint=vel * sprint_days,
            )

    # ── Status davomiyliklari (barcha hisoblar uchun asos) ──────────────

    def compute_status_durations(self) -> List[StatusDuration]:
        """Har bir task × status uchun sarflangan soatni hisoblash"""
        if self._status_durations is not None:
            return self._status_durations

        results = []
        now = datetime.now()

        for task in self.tasks:
            if not task.transitions:
                continue

            for i, tr in enumerate(task.transitions):
                start = tr.timestamp
                if i + 1 < len(task.transitions):
                    end = task.transitions[i + 1].timestamp
                else:
                    # Oxirgi status — hozirgi vaqtgacha (yoki resolved gacha)
                    end = task.resolved or now

                days = _work_days_between(start, end)
                hours = round(days * WORK_HOURS_PER_DAY, 2)

                results.append(StatusDuration(
                    task_key=task.key,
                    status=tr.to_status,
                    hours=hours,
                    assignee=task.assignee,
                    story_points=task.story_points,
                ))

        self._status_durations = results
        return results

    # ═════════════════════════════════════════════════════════════════════
    # 1. SPRINT OVERVIEW
    # ═════════════════════════════════════════════════════════════════════

    def get_sprint_overview(self) -> Dict[str, Any]:
        """Sprint umumiy holati"""
        if not self.sprint or not self.tasks:
            return {}

        total_sp = sum(t.story_points for t in self.tasks)
        completed_sp = sum(
            t.story_points for t in self.tasks
            if _upper(t.status) in STATUS_DONE
        )
        in_progress_sp = sum(
            t.story_points for t in self.tasks
            if _upper(t.status) in STATUS_IN_PROGRESS
        )
        remaining_sp = total_sp - completed_sp
        rejected_sp = sum(
            t.story_points for t in self.tasks
            if _upper(t.status) in STATUS_REJECTED
        )

        now = datetime.now()
        start = self.sprint.start_date or now
        end = self.sprint.end_date or now
        elapsed_days = max((now - start).days, 0) if self.sprint.state == 'active' else self.sprint.total_days
        remaining_days = max((end - now).days, 0) if self.sprint.state == 'active' else 0

        # Status distribution
        status_dist = {}
        for t in self.tasks:
            g = _status_group(t.status)
            status_dist[g] = status_dist.get(g, 0) + 1

        # Daily velocity (kunlik bajarilgan SP)
        daily_velocity = self._compute_daily_velocity()

        # Team o'rtacha velocity
        team_velocity = (completed_sp / elapsed_days) if elapsed_days > 0 else 0

        # Risk score
        remaining_capacity = remaining_days * team_velocity if team_velocity > 0 else 0
        risk_score = (remaining_sp / remaining_capacity) if remaining_capacity > 0 else (
            0.0 if remaining_sp == 0 else 2.0
        )

        # Burndown data
        burndown = self._compute_burndown()

        progress_pct = round((completed_sp / total_sp * 100), 1) if total_sp > 0 else 0

        return {
            'sprint_name': self.sprint.name,
            'sprint_state': self.sprint.state,
            'start_date': self.sprint.start_date,
            'end_date': self.sprint.end_date,
            'total_days': self.sprint.total_days,
            'elapsed_days': elapsed_days,
            'remaining_days': remaining_days,
            'total_sp': total_sp,
            'completed_sp': completed_sp,
            'in_progress_sp': in_progress_sp,
            'remaining_sp': remaining_sp,
            'rejected_sp': rejected_sp,
            'progress_pct': progress_pct,
            'total_tasks': len(self.tasks),
            'completed_tasks': sum(1 for t in self.tasks if _upper(t.status) in STATUS_DONE),
            'developers_count': len(set(t.assignee for t in self.tasks if t.assignee != 'Unassigned')),
            'status_distribution': status_dist,
            'daily_velocity': daily_velocity,
            'team_velocity': round(team_velocity, 2),
            'risk_score': round(risk_score, 2),
            'burndown': burndown,
        }

    def _compute_daily_velocity(self) -> List[Dict]:
        """Kunlik bajarilgan SP (CLOSED ga o'tgan tasklar)"""
        daily = {}
        for task in self.tasks:
            for tr in task.transitions:
                if _upper(tr.to_status) in STATUS_DONE:
                    day = tr.timestamp.strftime('%Y-%m-%d')
                    daily[day] = daily.get(day, 0) + task.story_points
                    break  # Birinchi CLOSED transition yetarli

        return [{'date': d, 'sp': v} for d, v in sorted(daily.items())]

    def _compute_burndown(self) -> Dict[str, List]:
        """Burndown chart uchun ideal va actual liniyalar"""
        if not self.sprint or not self.sprint.start_date or not self.sprint.end_date:
            return {'dates': [], 'ideal': [], 'actual': []}

        total_sp = sum(t.story_points for t in self.tasks)
        start = self.sprint.start_date
        end = self.sprint.end_date

        # Ish kunlari ro'yxati
        work_days = []
        d = start
        while d <= end:
            if d.weekday() < 5:
                work_days.append(d)
            d += timedelta(days=1)

        if not work_days:
            return {'dates': [], 'ideal': [], 'actual': []}

        # Ideal line: teng taqsimot
        ideal = []
        daily_burn = total_sp / len(work_days) if work_days else 0
        for i in range(len(work_days)):
            ideal.append(round(total_sp - daily_burn * (i + 1), 1))

        # Actual: har bir kun oxirida qancha SP qolgan
        # Birinchi CLOSED transition sanalari bo'yicha
        closed_by_day: Dict[str, float] = {}
        for task in self.tasks:
            for tr in task.transitions:
                if _upper(tr.to_status) in STATUS_DONE:
                    day = tr.timestamp.strftime('%Y-%m-%d')
                    closed_by_day[day] = closed_by_day.get(day, 0) + task.story_points
                    break

        actual = []
        remaining = total_sp
        now = datetime.now()
        for wd in work_days:
            if wd > now:
                break
            day_str = wd.strftime('%Y-%m-%d')
            remaining -= closed_by_day.get(day_str, 0)
            actual.append(round(remaining, 1))

        dates_str = [wd.strftime('%m-%d') for wd in work_days]

        return {
            'dates': dates_str,
            'ideal': ideal,
            'actual': actual,
        }

    # ═════════════════════════════════════════════════════════════════════
    # 2. DEVELOPER PERFORMANCE
    # ═════════════════════════════════════════════════════════════════════

    def get_developer_stats(self) -> List[Dict[str, Any]]:
        """Har bir developer uchun SP, velocity, kechikish"""
        devs: Dict[str, List[TaskData]] = {}
        for t in self.tasks:
            if t.assignee != 'Unassigned':
                devs.setdefault(t.assignee, []).append(t)

        results = []
        for name, tasks in sorted(devs.items()):
            cap = self.dev_capacities.get(name)
            velocity_per_day = cap.velocity_per_day if cap else 2.0

            assigned_sp = sum(t.story_points for t in tasks)
            completed_sp = sum(t.story_points for t in tasks if _upper(t.status) in STATUS_DONE)
            in_progress_sp = sum(t.story_points for t in tasks if _upper(t.status) in STATUS_IN_PROGRESS)
            remaining_sp = assigned_sp - completed_sp
            returned_count = sum(
                1 for t in tasks
                for tr in t.transitions
                if _upper(tr.to_status) in STATUS_RETURN
            )
            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if _upper(t.status) in STATUS_DONE)

            # Task darajasida kechikish
            task_details = []
            total_delay_days = 0
            total_delay_sp = 0

            for t in tasks:
                expected_days = (t.story_points / velocity_per_day) if velocity_per_day > 0 else 0
                actual_days = self._task_cycle_days(t)

                if actual_days is not None:
                    delay_days = actual_days - expected_days
                    delay_sp = delay_days * velocity_per_day
                    total_delay_days += max(delay_days, 0)
                    total_delay_sp += max(delay_sp, 0)
                else:
                    delay_days = None
                    delay_sp = None

                task_details.append({
                    'key': t.key,
                    'summary': t.summary,
                    'status': t.status,
                    'story_points': t.story_points,
                    'expected_days': round(expected_days, 2),
                    'actual_days': round(actual_days, 2) if actual_days else None,
                    'delay_days': round(delay_days, 2) if delay_days is not None else None,
                    'delay_sp': round(delay_sp, 2) if delay_sp is not None else None,
                })

            # First pass rate
            first_pass = sum(
                1 for t in tasks
                if _upper(t.status) in STATUS_DONE
                and not any(_upper(tr.to_status) in STATUS_RETURN for tr in t.transitions)
            )
            fpr = round(first_pass / completed_tasks * 100, 1) if completed_tasks > 0 else 0

            results.append({
                'name': name,
                'velocity_per_day': velocity_per_day,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'assigned_sp': assigned_sp,
                'completed_sp': completed_sp,
                'in_progress_sp': in_progress_sp,
                'remaining_sp': remaining_sp,
                'returned_count': returned_count,
                'first_pass_rate': fpr,
                'total_delay_days': round(total_delay_days, 2),
                'total_delay_sp': round(total_delay_sp, 2),
                'task_details': task_details,
            })

        return results

    def _task_cycle_days(self, task: TaskData) -> Optional[float]:
        """Task boshlangan vaqtdan CLOSED gacha ish kunlari (IN PROGRESS → CLOSED)"""
        start = None
        end = None
        for tr in task.transitions:
            if start is None and _upper(tr.to_status) in STATUS_IN_PROGRESS:
                start = tr.timestamp
            if _upper(tr.to_status) in STATUS_DONE:
                end = tr.timestamp

        if start and end:
            return _work_days_between(start, end)
        return None

    # ═════════════════════════════════════════════════════════════════════
    # 3. TASK PIPELINE
    # ═════════════════════════════════════════════════════════════════════

    def get_pipeline_data(self) -> Dict[str, Any]:
        """Kanban board uchun tasklar (status bo'yicha guruhlangan)"""
        pipeline: Dict[str, List[Dict]] = {}
        for s in STATUS_PIPELINE + STATUS_EXCEPTION:
            pipeline[s] = []

        durations = self.compute_status_durations()
        # Har bir task ning hozirgi statusdagi vaqti
        current_status_hours: Dict[str, float] = {}
        for d in durations:
            # Oxirgi entry shu task uchun
            current_status_hours[d.task_key] = d.hours

        for task in self.tasks:
            group = _status_group(task.status)
            hrs = current_status_hours.get(task.key, 0)

            card = {
                'key': task.key,
                'summary': task.summary,
                'assignee': task.assignee,
                'story_points': task.story_points,
                'type': task.issue_type,
                'days_in_status': round(hrs / WORK_HOURS_PER_DAY, 1),
                'hours_in_status': round(hrs, 1),
                'is_stuck': hrs > 3 * WORK_HOURS_PER_DAY,  # 3+ ish kun = stuck
            }

            if group in pipeline:
                pipeline[group].append(card)
            else:
                pipeline.setdefault(group, []).append(card)

        return pipeline

    # ═════════════════════════════════════════════════════════════════════
    # 4. BOTTLENECK ANALYZER
    # ═════════════════════════════════════════════════════════════════════

    def get_bottleneck_data(self) -> Dict[str, Any]:
        """Bottleneck tahlili: status vaqtlari, heatmap, alertlar"""
        durations = self.compute_status_durations()

        # Status bo'yicha o'rtacha vaqt
        status_times: Dict[str, List[float]] = {}
        for d in durations:
            g = _status_group(d.status)
            status_times.setdefault(g, []).append(d.hours)

        avg_status_time = {}
        for status, hours_list in status_times.items():
            avg_h = sum(hours_list) / len(hours_list)
            avg_status_time[status] = {
                'avg_hours': round(avg_h, 1),
                'avg_days': round(avg_h / WORK_HOURS_PER_DAY, 2),
                'count': len(hours_list),
                'total_hours': round(sum(hours_list), 1),
                'bottleneck_score': round(len(hours_list) * avg_h, 1),
            }

        # Developer × Status heatmap
        heatmap: Dict[str, Dict[str, float]] = {}
        for d in durations:
            g = _status_group(d.status)
            heatmap.setdefault(d.assignee, {})
            heatmap[d.assignee].setdefault(g, [])
            heatmap[d.assignee][g].append(d.hours)

        heatmap_avg = {}
        for dev, statuses in heatmap.items():
            heatmap_avg[dev] = {}
            for status, hours_list in statuses.items():
                heatmap_avg[dev][status] = round(
                    sum(hours_list) / len(hours_list) / WORK_HOURS_PER_DAY, 2
                )

        # Alertlar
        alerts = []
        pipeline = self.get_pipeline_data()
        for status, cards in pipeline.items():
            for card in cards:
                days = card.get('days_in_status', 0)
                if _upper(status) in STATUS_MERGED and days > 2:
                    alerts.append({
                        'task': card['key'],
                        'status': status,
                        'days': days,
                        'assignee': card['assignee'],
                        'type': 'deploy_wait',
                        'message': f"MERGED statusda {days:.1f} kun — deploy kutmoqda",
                    })
                elif _upper(status) in STATUS_CODE_REVIEW and days > 1:
                    alerts.append({
                        'task': card['key'],
                        'status': status,
                        'days': days,
                        'assignee': card['assignee'],
                        'type': 'review_wait',
                        'message': f"PULL REQUEST da {days:.1f} kun — code review kechikmoqda",
                    })
                elif days > 3:
                    alerts.append({
                        'task': card['key'],
                        'status': status,
                        'days': days,
                        'assignee': card['assignee'],
                        'type': 'stuck',
                        'message': f"{status} da {days:.1f} kun — tiqilib qolgan",
                    })

        # Cycle time (IN PROGRESS → CLOSED)
        cycle_times = []
        for t in self.tasks:
            days = self._task_cycle_days(t)
            if days is not None:
                cycle_times.append(days)

        avg_cycle = round(sum(cycle_times) / len(cycle_times), 2) if cycle_times else 0

        return {
            'avg_status_time': avg_status_time,
            'heatmap': heatmap_avg,
            'alerts': alerts,
            'avg_cycle_time_days': avg_cycle,
            'cycle_times': cycle_times,
        }

    # ═════════════════════════════════════════════════════════════════════
    # 5. QA & TESTING
    # ═════════════════════════════════════════════════════════════════════

    def get_qa_stats(self) -> Dict[str, Any]:
        """QA va testing statistikasi"""
        total_tested = 0
        closed_clean = 0  # Birinchi marta CLOSED
        returned = 0
        need_clarification = 0
        rejected = 0

        qa_queue = []  # Ready to Test + TESTING dagi tasklar
        qa_times = []  # Ready to Test → CLOSED vaqtlar

        for task in self.tasks:
            was_returned = False
            was_clarified = False
            ready_test_time = None
            closed_time = None

            for tr in task.transitions:
                s = _upper(tr.to_status)
                if s in STATUS_RETURN:
                    was_returned = True
                    returned += 1
                if 'CLARIFICATION' in s:
                    was_clarified = True
                    need_clarification += 1
                if s in STATUS_REJECTED:
                    rejected += 1
                if s in STATUS_READY_TEST and ready_test_time is None:
                    ready_test_time = tr.timestamp
                if s in STATUS_DONE:
                    closed_time = tr.timestamp

            if _upper(task.status) in STATUS_DONE:
                total_tested += 1
                if not was_returned and not was_clarified:
                    closed_clean += 1

            if _upper(task.status) in (STATUS_READY_TEST | STATUS_TESTING):
                qa_queue.append({
                    'key': task.key,
                    'summary': task.summary,
                    'assignee': task.assignee,
                    'story_points': task.story_points,
                    'status': task.status,
                })

            if ready_test_time and closed_time:
                qa_hours = (closed_time - ready_test_time).total_seconds() / 3600
                qa_times.append(qa_hours / WORK_HOURS_PER_DAY)

        fpr = round(closed_clean / total_tested * 100, 1) if total_tested > 0 else 0
        avg_qa_time = round(sum(qa_times) / len(qa_times), 2) if qa_times else 0

        # Defect by developer (qaytarilgan task soni)
        defect_by_dev: Dict[str, int] = {}
        for task in self.tasks:
            for tr in task.transitions:
                if _upper(tr.to_status) in STATUS_RETURN:
                    defect_by_dev[task.assignee] = defect_by_dev.get(task.assignee, 0) + 1

        return {
            'total_tested': total_tested,
            'closed_clean': closed_clean,
            'returned': returned,
            'need_clarification': need_clarification,
            'rejected': rejected,
            'first_pass_rate': fpr,
            'avg_qa_time_days': avg_qa_time,
            'qa_queue': qa_queue,
            'defect_by_dev': defect_by_dev,
        }

    # ═════════════════════════════════════════════════════════════════════
    # 6. SPRINT COMPARISON
    # ═════════════════════════════════════════════════════════════════════

    def get_sprint_summary_for_comparison(self) -> Dict[str, Any]:
        """Sprint comparison uchun xulosa (bitta sprint uchun)"""
        overview = self.get_sprint_overview()
        qa = self.get_qa_stats()
        bn = self.get_bottleneck_data()

        dev_stats = self.get_developer_stats()
        velocities = [d['completed_sp'] / max(d['total_tasks'], 1) for d in dev_stats]

        return {
            'sprint_name': self.sprint.name if self.sprint else '',
            'total_sp': overview.get('total_sp', 0),
            'completed_sp': overview.get('completed_sp', 0),
            'completion_pct': overview.get('progress_pct', 0),
            'team_velocity': overview.get('team_velocity', 0),
            'first_pass_rate': qa.get('first_pass_rate', 0),
            'avg_cycle_time': bn.get('avg_cycle_time_days', 0),
            'return_count': qa.get('returned', 0),
            'total_tasks': overview.get('total_tasks', 0),
            'developers_count': overview.get('developers_count', 0),
        }
