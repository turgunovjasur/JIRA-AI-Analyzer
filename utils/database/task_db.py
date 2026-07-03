"""
Task Processing Database Helper

PostgreSQL orqali task va servis-bosqich holatlarini boshqarish.
Webhook oqimida dublikat comment va qayta ishlashni oldini olish uchun.

Author: JASUR TURGUNOV
Date: 2026-02-09
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.logger import get_logger
from utils.database.job_queue_repository import (
    claim_next_job as repo_claim_next_job,
)
from utils.database.job_queue_repository import (
    enqueue_job as repo_enqueue_job,
)
from utils.database.job_queue_repository import (
    fetch_queue_snapshot as repo_fetch_queue_snapshot,
)
from utils.database.job_queue_repository import (
    mark_job_done as repo_mark_job_done,
)
from utils.database.job_queue_repository import (
    mark_job_failed as repo_mark_job_failed,
)
from utils.database.job_queue_repository import (
    mark_job_retry as repo_mark_job_retry,
)
from utils.database.job_queue_repository import (
    requeue_stale_running_jobs as repo_requeue_stale_running_jobs,
)
from utils.database.runtime import connect_processing_db
from utils.database.task_repository import (
    delete_task_record,
    fetch_task_by_id,
    insert_status_history,
    upsert_task_record,
)
from utils.database.task_repository import (
    fetch_blocked_tasks_ready_for_retry as repo_fetch_blocked_tasks_ready_for_retry,
)
from utils.database.task_repository import (
    fetch_status_history_for_report as repo_fetch_status_history_for_report,
)
from utils.database.task_repository import (
    fetch_stuck_tasks as repo_fetch_stuck_tasks,
)

log = get_logger("database")

# Settings import (lazy loading to avoid circular imports)
_settings_cache = None

def _get_db_settings():
    """Get DB settings from app_settings (cached)"""
    global _settings_cache
    if _settings_cache is None:
        try:
            from config.app_settings import get_app_settings
            _settings_cache = get_app_settings(force_reload=False).queue
        except Exception as e:
            log.warning(f"Settings load failed, using defaults: {e}")
            class DefaultSettings:
                db_connection_timeout = 30.0
            _settings_cache = DefaultSettings()
    return _settings_cache


def init_db() -> None:
    """PostgreSQL schemani versiyalangan migratsiya orqali tayyorlash.

    Runtime jadvallar (job_queue/checker/analysis) endi har ulanishda emas, shu
    yerda — startup'da bir marta ensure qilinadi (P2: hot-path DDL olib tashlandi).
    """
    try:
        from utils.database.migrations import run_migrations
        run_migrations()
        log.info("DB initialized (postgres runtime)")

    except Exception as e:
        log.warning(f"DB initialization error: {e}")
        raise

def get_task(task_id: str, company_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Berilgan task_id bo'yicha task ma'lumotlarini PostgreSQLdan o'qish."""
    try:
        settings = _get_db_settings()
        return fetch_task_by_id(connect_processing_db, task_id, settings.db_connection_timeout, company_id=company_id)

    except Exception as e:
        log.warning(f"[{task_id}] get_task error: {e}")
        return None


def upsert_task(task_id: str, fields: Dict[str, Any], company_id: Optional[int] = None) -> None:
    """
    Task ma'lumotlarini yangilash (UPDATE) yoki yangi yaratish (INSERT).

    Funksiya avval task mavjudligini tekshiradi: agar bor bo'lsa UPDATE,
    bo'lmasa INSERT bajaradi. ``updated_at`` maydoni har safar avtomatik
    yangilanadi.

    Args:
        task_id: JIRA task identifikatori (masalan: DEV-1234)
        fields: Yangilanishi kerak bo'lgan maydonlar lug'ati.
            Masalan: ``{'task_status': 'progressing', 'service1_status': 'pending'}``

    Raises:
        Exception: Kutilmagan DB xatolari.

    Note:
        ``fields`` lug'atidagi ``updated_at`` kaliti bu funksiya tomonidan
        avtomatik o'rnatiladi — tashqaridan berilgan qiymat ustiga yoziladi.
    """
    try:
        settings = _get_db_settings()
        upsert_task_record(
            connect_processing_db,
            task_id,
            fields,
            settings.db_connection_timeout,
            company_id=company_id,
        )

    except Exception as e:
        log.warning(f"[{task_id}] upsert_task error: {e}")
        raise


def mark_progressing(task_id: str, jira_status: str, update_time: Optional[datetime] = None, company_id: Optional[int] = None) -> None:
    """
    Task holatini ``'progressing'`` ga o'zgartirish — qayta ishlash boshlanganda chaqiriladi.

    Holat o'tishi (state transition):
        ``none`` / ``completed`` / ``error`` / ``blocked`` / ``returned``
            → ``progressing``

    Bu holat webhook handler da dublikat ishlov berishni oldini olish uchun
    ishlatiladi: agar task allaqachon ``progressing`` bo'lsa, keyingi webhook
    eventi e'tiborga olinmaydi (queue lock mexanizmi).

    Saqlanadigan ma'lumotlar:
        - ``task_status`` = ``'progressing'``
        - ``last_jira_status``: JIRA dagi joriy status nomi (masalan: ``Ready to Test``)
        - ``task_update_time``: JIRA webhook eventidagi o'zgarish vaqti
        - ``last_processed_at``: hozirgi vaqt (qayta ishlash boshlangan moment)

    Args:
        task_id: JIRA task identifikatori (masalan: DEV-1234)
        jira_status: JIRA status nomi (masalan: ``'Ready to Test'``)
        update_time: JIRA webhook eventidagi vaqt damgasi.
            Agar berilmasa — hozirgi vaqt (``datetime.now()``) ishlatiladi.
    """
    if update_time is None:
        update_time = datetime.now()

    fields = {
        'task_status': 'progressing',
        'last_jira_status': jira_status,
        'task_update_time': update_time.isoformat(),
        'last_processed_at': datetime.now().isoformat()
    }
    if company_id is not None:
        fields['company_id'] = company_id

    upsert_task(task_id, fields, company_id=company_id)


def mark_completed(task_id: str, company_id: Optional[int] = None):
    """
    Task holatini 'completed' ga o'zgartirish
    """
    upsert_task(task_id, {
        'task_status': 'completed',
        'last_processed_at': datetime.now().isoformat()
    }, company_id=company_id)


def mark_returned(task_id: str, company_id: Optional[int] = None) -> None:
    """
    Task holatini ``'returned'`` ga o'zgartirish — task TZ/PR muammo sababli qaytarilganda.

    Holat o'tishi (state transition):
        ``progressing`` → ``returned``

    Nima uchun service2_status ``'pending'`` qoladi (``'error'`` emas):
        Task ``returned`` bo'lganda Service1 allaqachon ishlagan va past moslik
        bali (compliance_score) tufayli Service2 ishga tushmagan. Bu holat
        ``'error'`` emas — bu kutilgan biznes-mantiq. Shu sababli:

        - ``service1_status`` = ``'done'`` (Service1 bajarilgan, natija past)
        - ``service2_status`` = ``'pending'`` (Service2 hali ishlamagan, xato emas)
        - ``service2_error`` = None (xato xabari tozalanadi)

        Agar ``service2_status`` = ``'error'`` qilinsa, monitoring dashboardda
        noto'g'ri xato ko'rsatiladi va re-check logikasi buziladi.

    Args:
        task_id: JIRA task identifikatori (masalan: DEV-1234)
    """
    upsert_task(task_id, {
        'task_status': 'returned',
        'service1_status': 'done',  # Service1 done bo'lishi kerak (score past bo'lganda ham)
        'service2_status': 'pending',  # Service2 pending (error emas)
        'service2_error': None,
        'last_processed_at': datetime.now().isoformat()
    }, company_id=company_id)


def mark_returned_pr_not_merged(task_id: str, company_id: Optional[int] = None) -> None:
    """
    PR merged emas sababli task qaytarilganda DB holatini belgilash.

    Holat o'tishi (state transition):
        ``progressing`` → ``returned``

    mark_returned() dan farqi:
        - ``service1_status`` = ``'pending'`` (done emas!) — task qaytib kelganda
          Service1 qaytadan ishlashi kerak, chunki PR merge qilingan bo'ladi.
        - ``compliance_score`` = None — oldingi bali tozalanadi.
        - ``service1_error`` = None — xato holati tozalanadi.

    Qayta kelganda nima bo'ladi:
        Task yana trigger statusga o'tganda (developer PR merge qilib, taskni
        qayta jo'natganda) service1_status='pending' bo'lgani uchun
        check_tz_pr_and_comment() qaytadan to'liq ishlaydi.

    Args:
        task_id: JIRA task identifikatori (masalan: DEV-1234)
    """
    upsert_task(task_id, {
        'task_status': 'returned',
        'service1_status': 'pending',   # Qayta kelganda re-check uchun
        'service2_status': 'pending',
        'service1_error': None,         # Eski xato tozalanadi
        'service2_error': None,
        'compliance_score': None,       # Eski ball tozalanadi
        'last_processed_at': datetime.now().isoformat()
    }, company_id=company_id)


def mark_error(task_id: str, error_message: str, company_id: Optional[int] = None):
    """
    Task holatini 'error' ga o'zgartirish

    Args:
        task_id: JIRA task key
        error_message: Xato xabari
    """
    upsert_task(task_id, {
        'task_status': 'error',
        'error_message': error_message,
        'last_processed_at': datetime.now().isoformat()
    }, company_id=company_id)


def increment_return_count(task_id: str, company_id: Optional[int] = None):
    """
    Return count ni 1 ga oshirish
    """
    task = get_task(task_id, company_id=company_id)
    if task:
        new_count = (task.get('return_count') or 0) + 1
        upsert_task(task_id, {'return_count': new_count}, company_id=company_id)
    else:
        upsert_task(task_id, {'return_count': 1}, company_id=company_id)


def set_return_reason(task_id: str, reason: str, company_id: Optional[int] = None) -> None:
    """
    Task qaytarilish sababini DB ga saqlash.

    WARN_LOW_SCORE, WARN_MIN_TZ, WARN_NO_PR, WARN_PR_NOT_MERGED,
    WARN_AI_TIMEOUT, ERR_UNKNOWN kodlaridan biri.

    Navbatdagi signal kelganda servis bu codeni o'qib,
    qanday harakat qilishini belgilaydi.
    """
    upsert_task(task_id, {'return_reason': reason}, company_id=company_id)


def set_skip_detected(task_id: str, company_id: Optional[int] = None):
    """
    Skip detected flag ni True ga o'rnatish
    """
    upsert_task(task_id, {
        'skip_detected': True,
        'task_status': 'completed',  # yoki 'skipped'
        'last_processed_at': datetime.now().isoformat()
    }, company_id=company_id)


def set_service1_done(task_id: str, compliance_score: Optional[int] = None, company_id: Optional[int] = None):
    """
    Service1 (TZ-PR) holatini 'done' ga o'zgartirish

    Args:
        task_id: JIRA task key
        compliance_score: Moslik bali (ixtiyoriy)
    """
    fields = {
        'service1_status': 'done',
        'service1_done_at': datetime.now().isoformat(),
        'service1_error': None
    }
    if compliance_score is not None:
        fields['compliance_score'] = compliance_score

    upsert_task(task_id, fields, company_id=company_id)


def set_service1_error(
    task_id: str,
    error_msg: str,
    keep_service2_pending: bool = False,
    company_id: Optional[int] = None,
) -> None:
    """
    Service1 (TZ-PR checker) holatini ``'error'`` ga o'zgartirish.

    Holat o'tishi (state transition):
        ``service1_status``: ``'pending'`` / ``'progressing'`` → ``'error'``
        ``task_status``: → ``'error'``

    keep_service2_pending parametri nima uchun kerak:
        Ba'zi hollarda Service1 xatosi Service2 ni to'xtatmasligi kerak.
        Masalan, GitHub PR topilmasa Service1 xato bo'ladi, lekin Service2
        TZ-only rejimda ishlashi mumkin. Bunday holda:

        - ``keep_service2_pending=True`` — Service2 ``'pending'`` qoladi,
          Service2 keyingi bosqichda TZ ma'lumoti bilan ishlaydi.

        - ``keep_service2_pending=False`` (default) — Service1 xatosi
          Service2 ni ham bloklaydi: ``service2_status`` = ``'error'``,
          ``service2_error`` = ``'Blocked by Service1 failure'``.

    Args:
        task_id: JIRA task identifikatori (masalan: DEV-1234)
        error_msg: Xato xabari (log va DB ga yoziladi)
        keep_service2_pending: True bo'lsa Service2 ``'pending'`` holatida qoladi
            va keyingi bosqichda TZ-only rejimda ishlashga ruxsat beriladi.
            False bo'lsa (default) Service2 ham ``'error'`` ga o'tadi.
    """
    fields = {
        'service1_status': 'error',
        'service1_error': error_msg,
        'task_status': 'error',
        'last_processed_at': datetime.now().isoformat()
    }
    if keep_service2_pending:
        # Service2 ni pending ga o'rnatish (oldingi error holatini tozalash)
        fields['service2_status'] = 'pending'
        fields['service2_error'] = None
    else:
        fields['service2_status'] = 'error'
        fields['service2_error'] = 'Blocked by Service1 failure'

    upsert_task(task_id, fields, company_id=company_id)


def set_service2_done(task_id: str, company_id: Optional[int] = None):
    """
    Service2 (Testcase) holatini 'done' ga o'zgartirish
    """
    upsert_task(task_id, {
        'service2_status': 'done',
        'service2_done_at': datetime.now().isoformat(),
        'service2_error': None,
        'task_status': 'completed',
        'last_processed_at': datetime.now().isoformat()
    }, company_id=company_id)


def set_service2_error(task_id: str, error_msg: str, company_id: Optional[int] = None):
    """
    Service2 (Testcase) holatini 'error' ga o'zgartirish

    Args:
        task_id: JIRA task key
        error_msg: Xato xabari
    """
    upsert_task(task_id, {
        'service2_status': 'error',
        'service2_error': error_msg,
        'task_status': 'error',
        'last_processed_at': datetime.now().isoformat()
    }, company_id=company_id)


def set_task_timeout_error(task_id: str, error_msg: str, company_id: Optional[int] = None):
    """
    Task queue timeout xatosi - barcha servislar error holatga

    Args:
        task_id: JIRA task key
        error_msg: Timeout xato xabari
    """
    upsert_task(task_id, {
        'task_status': 'error',
        'service1_status': 'error',
        'service2_status': 'error',
        'service1_error': error_msg,
        'service2_error': 'Blocked by timeout',
        'error_message': error_msg,
        'last_processed_at': datetime.now().isoformat()
    }, company_id=company_id)


def mark_blocked(task_id: str, reason: str, retry_minutes: int = 5, company_id: Optional[int] = None):
    """
    Task holatini 'blocked' ga o'zgartirish (AI timeout/429 limit)

    Args:
        task_id: JIRA task key
        reason: Bloklash sababi
        retry_minutes: Necha daqiqadan keyin qayta ishlash
    """
    now = datetime.now()
    retry_at = now + timedelta(minutes=retry_minutes)
    upsert_task(task_id, {
        'task_status': 'blocked',
        'error_message': reason,
        'blocked_at': now.isoformat(),
        'blocked_retry_at': retry_at.isoformat(),
        'block_reason': reason,
        'last_processed_at': now.isoformat()
    }, company_id=company_id)


def set_service1_blocked(task_id: str, reason: str, retry_minutes: int = 5, company_id: Optional[int] = None):
    """
    Service1 ni 'blocked' va task ni 'blocked' ga o'zgartirish
    Service2 'pending' qoladi

    Args:
        task_id: JIRA task key
        reason: Bloklash sababi
        retry_minutes: Necha daqiqadan keyin qayta ishlash
    """
    now = datetime.now()
    retry_at = now + timedelta(minutes=retry_minutes)
    upsert_task(task_id, {
        'service1_status': 'blocked',
        'service1_error': reason,
        'service2_status': 'pending',
        'task_status': 'blocked',
        'error_message': reason,
        'blocked_at': now.isoformat(),
        'blocked_retry_at': retry_at.isoformat(),
        'block_reason': reason,
        'last_processed_at': now.isoformat()
    }, company_id=company_id)


def set_service2_blocked(task_id: str, reason: str, retry_minutes: int = 5, company_id: Optional[int] = None):
    """
    Service2 ni 'blocked' va task ni 'blocked' ga o'zgartirish
    Service1 o'zgarmaydi (done yoki skip)

    Args:
        task_id: JIRA task key
        reason: Bloklash sababi
        retry_minutes: Necha daqiqadan keyin qayta ishlash
    """
    now = datetime.now()
    retry_at = now + timedelta(minutes=retry_minutes)
    upsert_task(task_id, {
        'service2_status': 'blocked',
        'service2_error': reason,
        'task_status': 'blocked',
        'error_message': reason,
        'blocked_at': now.isoformat(),
        'blocked_retry_at': retry_at.isoformat(),
        'block_reason': reason,
        'last_processed_at': now.isoformat()
    }, company_id=company_id)


def set_service1_skip(task_id: str, company_id: Optional[int] = None):
    """
    Service1 ni 'skip' ga o'zgartirish (AI_SKIP code topilganda)
    Score 100 qo'yiladi (threshold check o'tishi uchun)
    """
    upsert_task(task_id, {
        'service1_status': 'skip',
        'service1_done_at': datetime.now().isoformat(),
        'service1_error': None,
        'compliance_score': 100,
        'skip_detected': True
    }, company_id=company_id)


def get_blocked_tasks_ready_for_retry() -> List[Dict[str, Any]]:
    """
    Qayta urinish vaqti kelgan ``'blocked'`` tasklarni tanlash.

    So'rov mantiq:
        ``WHERE task_status = 'blocked'
           AND blocked_retry_at IS NOT NULL
           AND blocked_retry_at <= :now``

        Ya'ni: hozirgi vaqt ``blocked_retry_at`` dan katta yoki teng bo'lgan
        barcha blocked tasklar qaytariladi. Bu retry scheduler tomonidan har
        N daqiqada chaqiriladi — ``blocked_retry_at`` qiymati kelajakda
        bo'lsa, o'sha task hali tayyor emas.

    Bloklash stsenariylari (bu funksiya ular uchun ishlatiladi):
        - AI 429 (Too Many Requests) — rate limit oshilganda
        - AI timeout — Gemini javob bermasa
        - ``mark_blocked()``, ``set_service1_blocked()``, ``set_service2_blocked()``
          orqali o'rnatilgan holatlar

    Tartiblash:
        ``blocked_retry_at ASC`` — eng eski (eng uzoq kutgan) task birinchi.

    Returns:
        List[Dict[str, Any]]: Har bir task to'liq maydonlari bilan lug'at sifatida.
            Bo'sh ro'yxat qaytadi agar tayyor task yo'q bo'lsa yoki xato yuz bersa.
    """
    try:
        return repo_fetch_blocked_tasks_ready_for_retry(connect_processing_db)

    except Exception as e:
        log.warning(f"get_blocked_tasks_ready_for_retry error: {e}")
        return []


def delete_task(task_id: str, company_id: Optional[int] = None) -> bool:
    """
    Taskni DB dan to'liq o'chirish (transaction-safe)

    Args:
        task_id: JIRA task key

    Returns:
        True agar o'chirilsa, False agar topilmasa
    """
    try:
        settings = _get_db_settings()
        deleted = delete_task_record(
            connect_processing_db,
            task_id,
            company_id,
            settings.db_connection_timeout,
        )
        if deleted:
            log.info(f"[{task_id}] DB-DELETE -> ok")
            return True
        else:
            log.warning(f"[{task_id}] DB-DELETE -> task not found, nothing to delete")
            return False

    except Exception as e:
        log.warning(f"[{task_id}] delete_task error: {e}")
        return False


def reset_service_statuses(task_id: str, company_id: Optional[int] = None) -> None:
    """
    Servis holatlarini noldan boshlash uchun qayta tiklash (re-check stsenariysida).

    Qachon chaqiriladi:
        Task ilgari ``'returned'`` yoki ``'error'`` holatida bo'lgan va
        endi qayta ``Ready to Test`` statusiga o'tganda (masalan: developer
        TZ ni to'ldirib, taskni qaytadan test uchun jo'natganda) bu funksiya
        chaqiriladi. Shunday qilib Service1 va Service2 yana yangi sikl
        sifatida boshidan boshlanadi.

    Reset qilinadigan maydonlar:
        - ``service1_status`` → ``'pending'``
        - ``service2_status`` → ``'pending'``
        - ``service1_error`` → None
        - ``service2_error`` → None
        - ``service1_done_at`` → None
        - ``service2_done_at`` → None
        - ``compliance_score`` → None

    O'zgarmaydigan maydonlar:
        - ``task_status``: chaqiruvchi funksiya tomonidan boshqariladi
        - ``return_count``: saqlab qolinadi (nechi marta qaytarilgani statistika uchun)
        - ``assignee``, ``task_type``, ``feature_name``: meta-ma'lumotlar saqlanadi

    Args:
        task_id: JIRA task identifikatori (masalan: DEV-1234)
    """
    upsert_task(task_id, {
        'service1_status': 'pending',
        'service2_status': 'pending',
        'service1_error': None,
        'service2_error': None,
        'service1_done_at': None,
        'service2_done_at': None,
        'compliance_score': None
    }, company_id=company_id)


def _extract_task_type(task_details: Dict) -> str:
    """
    Extract task type from JIRA issue type.

    Raw JIRA issue type nomini qaytaradi — allowed_issue_types sozlamasi bilan mos keladi.
    Masalan: 'DEV-BUG', 'DEV- PROD TASK', 'DEV-TECHTASK', 'DEV-CLIENT TASK'

    Agar issue type bo'sh bo'lsa 'other' qaytaradi.
    """
    issue_type = task_details.get('type', '') or ''
    cleaned = issue_type.strip()
    return cleaned if cleaned else 'other'


def _extract_features_from_pr_files(pr_files: List[Dict]) -> tuple:
    """
    Extract feature names and tech stack from PR file paths.

    Fayl yo'llari strukturasi (debug DEV-6096 asosida):
      main/oracle/module/{MODULE}/...           → MODULE
      main/oracle/ui/{ORG}/{MODULE}/...         → MODULE
      main/oracle/uis/form/{ORG}/{MODULE}/...   → MODULE
      main/oracle/uis/{ORG}/{MODULE}/...        → MODULE
      main/page/form/{ORG}/{MODULE}/...         → MODULE
      main/app/{MODULE}/...                     → MODULE
      main/oracle/migr[5toX]/...               → skip (migration)
      main/oracle/setup/...                     → skip (setup)

    Misol:
      main/oracle/module/mkw/mkw_api.pck        → mkw, Oracle
      main/oracle/ui/anor/mkw/purchase/...      → mkw, Oracle
      main/oracle/uis/form/anor/mkw/purchase/.. → mkw, Oracle
      main/page/form/anor/mkw/purchase/...      → mkw, HTML

    Returns:
        tuple: (feature_names_csv, tech_stack_csv) or (None, None)
    """
    import re

    features = set()
    technologies = set()

    # Umumiy papkalar — feature sifatida hisoblanmaydi
    _SKIP_NAMES = {
        'form', 'ui', 'uis', 'app', 'src', 'main', 'oracle',
        'module', 'setup', 'migr', 'init', 'test', 'tests',
        'util', 'utils', 'common', 'shared', 'base', 'core',
        'config', 'resources', 'assets', 'static', 'templates',
        'page', 'pages', 'view', 'views', 'api', 'web',
    }

    # Skip pattern'lar — bu yo'llardan feature olinmaydi
    _SKIP_PATH_PATTERNS = [
        r'main/oracle/migr',       # migration fayllar
        r'main/oracle/setup',      # setup/init fayllar
    ]

    # Technology pattern'lar
    tech_patterns = {
        'Oracle': [r'\.sql$', r'\.pks$', r'\.pkb$', r'\.pck$', r'/oracle/'],
        'HTML':   [r'\.html?$'],
        'Java':   [r'\.java$'],
        'JavaScript': [r'\.jsx?$'],
        'TypeScript': [r'\.tsx?$'],
        'Python': [r'\.py$'],
    }

    # Feature extraction pattern'lar (tartib muhim — birinchi mos kelgani ishlatiladi)
    feature_patterns = [
        # main/oracle/module/{MODULE}/...
        r'main/oracle/module/([^/]+)/',
        # main/oracle/ui/{ORG}/{MODULE}/...
        r'main/oracle/ui/[^/]+/([^/]+)/',
        # main/oracle/uis/form/{ORG}/{MODULE}/...
        r'main/oracle/uis/form/[^/]+/([^/]+)/',
        # main/oracle/uis/{ORG}/{MODULE}/...
        r'main/oracle/uis/[^/]+/([^/]+)/',
        # main/page/form/{ORG}/{MODULE}/...
        r'main/page/form/[^/]+/([^/]+)/',
        # main/app/{MODULE}/...
        r'main/app/([^/]+)/',
        # src/{MODULE}/...
        r'src/([^/]+)/',
    ]

    for file_data in pr_files:
        filename = file_data.get('filename', '')

        # Technology aniqlash
        for tech, patterns in tech_patterns.items():
            for pattern in patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    technologies.add(tech)
                    break

        # Skip path tekshirish
        if any(re.search(p, filename) for p in _SKIP_PATH_PATTERNS):
            continue

        # Feature olish — birinchi mos kelgan pattern
        for pattern in feature_patterns:
            match = re.search(pattern, filename)
            if match:
                feature = match.group(1).lower()
                # Faqat harf va raqamlar
                feature = re.sub(r'[^a-z0-9_]', '', feature)
                # Umumiy papkalar va qisqa nomlarni o'tkazib yuborish
                if len(feature) > 2 and feature not in _SKIP_NAMES:
                    features.add(feature)
                break  # Birinchi mos kelgan pattern yetarli

    feature_csv = ', '.join(sorted(features)) if features else None
    tech_csv    = ', '.join(sorted(technologies)) if technologies else None

    return feature_csv, tech_csv


def update_task_metadata(
    task_id: str,
    task_details: Dict,
    pr_info: Optional[Dict] = None,
    company_id: Optional[int] = None,
):
    """
    Update task metadata: assignee, task_type, feature_name, technology_stack.

    Called from TZ-PR checker after PR fetch.
    """
    try:
        # Extract from JIRA
        assignee = task_details.get('assignee', 'Unassigned')
        task_type = _extract_task_type(task_details)

        # Extract from PR files
        feature_name = None
        technology_stack = None

        if pr_info and pr_info.get('all_files'):
            feature_name, technology_stack = _extract_features_from_pr_files(
                pr_info['all_files']
            )

        # Update DB
        upsert_task(task_id, {
            'assignee': assignee,
            'task_type': task_type,
            'feature_name': feature_name,
            'technology_stack': technology_stack
        }, company_id=company_id)

    except Exception as e:
        log.warning(f"[{task_id}] Metadata update error: {e}")


def get_stuck_tasks(timeout_minutes: int = 30) -> List[Dict[str, Any]]:
    """
    ``'progressing'`` holatida qolib ketgan (stuck) tasklarni topish.

    Task "stuck" hisoblanganda:
        Task ``'progressing'`` holatiga o'tgandan keyin ``timeout_minutes``
        daqiqadan ortiq vaqt o'tsa va hali ham ``'progressing'`` bo'lsa —
        bu task server crash, network uzilishi yoki kutilmagan xato sababli
        to'xtab qolgan deb hisoblanadi.

    timeout_minutes parametri nima uchun kerak:
        - Turli muhitlarda (test, staging, prod) timeout farqli bo'lishi mumkin.
        - Kichik qiymat (masalan: 5 min) — test muhitida tez aniqlash uchun.
        - Katta qiymat (masalan: 60 min) — og'ir AI operatsiyalar uchun.
        - Default: 30 daqiqa — oddiy webhook operatsiyalar uchun yetarli.

    SQL so'rovi:
        ``WHERE task_status = 'progressing'
           AND updated_at < :cutoff_time``

        ``stuck_minutes`` PostgreSQL vaqt farqi orqali daqiqalarda hisoblanadi.

    Monitoring ishlatilishi:
        Bu funksiya monitoring dashboard va cleanup scheduler tomonidan
        periodiq chaqiriladi. Topilgan stuck tasklar ``mark_error()`` orqali
        xato holatiga o'tkazilishi yoki adminга xabar yuborilishi mumkin.

    Args:
        timeout_minutes: Qancha daqiqa o'tsa task stuck deb hisoblanadi.
            Default: 30 daqiqa.

    Returns:
        List[Dict[str, Any]]: Stuck tasklar ro'yxati. Har bir element:
            - ``task_id``: JIRA task identifikatori
            - ``task_status``: ``'progressing'``
            - ``service1_status``, ``service2_status``: servis holatlari
            - ``last_processed_at``, ``updated_at``: vaqt damgalari
            - ``stuck_minutes``: necha daqiqa stuck bo'lgani (hisoblangan)
    """
    try:
        return repo_fetch_stuck_tasks(connect_processing_db, timeout_minutes)

    except Exception as e:
        log.warning(f"get_stuck_tasks error: {e}")
        return []


def log_status_change(
    task_id: str,
    from_status: Optional[str],
    to_status: str,
    changed_at: datetime,
    assignee: Optional[str] = None,
    story_points: Optional[float] = None,
    issue_type: Optional[str] = None,
    company_id: Optional[int] = None,
) -> None:
    """
    JIRA task status o'zgarishini task_status_history jadvaliga yozish.

    Har bir webhook kelganda (status o'zgarsa) bu funksiya chaqiriladi.
    Sprint report uchun vaqt tahlili shu jadval asosida quriladi.

    Args:
        task_id: JIRA task identifikatori (masalan: DEV-1234)
        from_status: Oldingi JIRA status (birinchi tranzitsiyada None bo'lishi mumkin)
        to_status: Yangi JIRA status
        changed_at: Status o'zgargan aniq vaqt (webhook'dan olinadi)
        assignee: Task ijrochisi (JIRA displayName)
        story_points: Task story point qiymati (JIRA customfield_10016)
        issue_type: Task turi (masalan: DEV-PROD TASK)
    """
    try:
        settings = _get_db_settings()
        insert_status_history(
            connect_processing_db,
            task_id,
            from_status,
            to_status,
            changed_at.isoformat(),
            assignee,
            story_points,
            issue_type,
            company_id,
            settings.db_connection_timeout,
        )

    except Exception as e:
        log.warning(f"[{task_id}] log_status_change error: {e}")


def get_status_history_for_report(days: int = 30, company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Sprint report uchun status o'zgarishlar tarixini o'qish.

    Har bir qator: task_id, from_status, to_status, changed_at, assignee,
    story_points, issue_type.

    Natija vaqt bo'yicha o'sib boruvchi tartibda — time-in-status hisoblash
    uchun kerakli ketma-ketlik saqlanadi.

    Args:
        days: Necha kunlik tarix (bugundan orqaga)

    Returns:
        List[Dict]: Tarix qatorlari ro'yxati
    """
    try:
        return repo_fetch_status_history_for_report(connect_processing_db, days, company_id=company_id)

    except Exception as e:
        log.warning(f"get_status_history_for_report error: {e}")
        return []


def enqueue_background_job(
    job_type: str,
    task_key: str,
    *,
    company_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
    dedupe_key: Optional[str] = None,
    scheduled_at: Optional[str] = None,
    max_attempts: int = 3,
) -> Dict[str, Any]:
    """Background worker uchun job navbatga qo'shish."""
    try:
        settings = _get_db_settings()
        conn = connect_processing_db(timeout=settings.db_connection_timeout, row_factory=True)
        job = repo_enqueue_job(
            conn,
            job_type=job_type,
            task_key=task_key,
            company_id=company_id,
            payload=payload,
            dedupe_key=dedupe_key,
            scheduled_at=scheduled_at,
            max_attempts=max_attempts,
        )
        conn.close()
        return job
    except Exception as e:
        log.warning(f"[{task_key}] enqueue_background_job error: {e}")
        return {}


def claim_next_background_job(worker_name: str) -> Optional[Dict[str, Any]]:
    """Worker uchun keyingi queued jobni claim qilish."""
    try:
        settings = _get_db_settings()
        conn = connect_processing_db(timeout=settings.db_connection_timeout, row_factory=True)
        job = repo_claim_next_job(conn, worker_name=worker_name)
        conn.close()
        return job or None
    except Exception as e:
        log.warning(f"[worker:{worker_name}] claim_next_background_job error: {e}")
        return None


def complete_background_job(job: Dict[str, Any]) -> bool:
    try:
        settings = _get_db_settings()
        conn = connect_processing_db(timeout=settings.db_connection_timeout, row_factory=True)
        repo_mark_job_done(conn, job)
        conn.close()
        return True
    except Exception as e:
        log.warning(f"[job:{job.get('id')}] complete_background_job error: {e}")
        return False


def retry_background_job(job: Dict[str, Any], error_message: str, delay_seconds: int) -> bool:
    try:
        settings = _get_db_settings()
        conn = connect_processing_db(timeout=settings.db_connection_timeout, row_factory=True)
        repo_mark_job_retry(conn, job, error_message, delay_seconds)
        conn.close()
        return True
    except Exception as e:
        log.warning(f"[job:{job.get('id')}] retry_background_job error: {e}")
        return False


def fail_background_job(job: Dict[str, Any], error_message: str) -> bool:
    try:
        settings = _get_db_settings()
        conn = connect_processing_db(timeout=settings.db_connection_timeout, row_factory=True)
        repo_mark_job_failed(conn, job, error_message)
        conn.close()
        return True
    except Exception as e:
        log.warning(f"[job:{job.get('id')}] fail_background_job error: {e}")
        return False


def requeue_stale_background_jobs(stale_seconds: int) -> Dict[str, int]:
    """Worker crash tufayli 'running'da qotib qolgan joblarni qayta navbatga/failed."""
    try:
        settings = _get_db_settings()
        conn = connect_processing_db(timeout=settings.db_connection_timeout, row_factory=True)
        result = repo_requeue_stale_running_jobs(conn, stale_seconds=stale_seconds)
        conn.close()
        return result
    except Exception as e:
        log.warning(f"requeue_stale_background_jobs error: {e}")
        return {"requeued": 0, "failed": 0}


def sweep_stuck_progressing_tasks(timeout_minutes: int = 60) -> int:
    """Terminal holatga o'tmay 'progressing'da qotib qolgan tasklarni 'error' qilish.

    So'nggi himoya chizig'i: worker/API run o'rtasida o'lsa yoki instrumentlanmagan
    oqim taskni 'progressing'da qoldirsa, keyingi webhook'lar SKIP bo'ladi (lockout).
    Bu ularni 'error' ga o'tkazadi — monitoring'da ko'rinadi va keyingi status
    o'zgarishida webhook handler reset qilib qayta ishlaydi.

    Job reaper (requeue_stale_background_jobs) crash'ni birinchi tiklaydi, shuning
    uchun bu timeout undan uzunroq bo'lishi kerak (default 60 daqiqa).

    Returns:
        int: 'error' ga o'tkazilgan tasklar soni.
    """
    swept = 0
    for task in get_stuck_tasks(timeout_minutes):
        task_id = str(task.get('task_id') or '').strip()
        if not task_id:
            continue
        company_id = task.get('company_id')
        stuck_minutes = task.get('stuck_minutes')
        mark_error(
            task_id,
            f"Stuck: {stuck_minutes} daqiqa 'progressing'da qoldi (avto-tiklash)",
            company_id=company_id,
        )
        swept += 1
    return swept


def get_background_queue_snapshot() -> Dict[str, Any]:
    try:
        settings = _get_db_settings()
        conn = connect_processing_db(timeout=settings.db_connection_timeout, row_factory=True)
        payload = repo_fetch_queue_snapshot(conn)
        conn.close()
        return payload
    except Exception as e:
        log.warning(f"get_background_queue_snapshot error: {e}")
        return {"queued": 0, "running": 0, "done": 0, "failed": 0}


# DB initialization on import
try:
    init_db()
except Exception as e:
    log.warning(f"DB initialization warning: {e}")
