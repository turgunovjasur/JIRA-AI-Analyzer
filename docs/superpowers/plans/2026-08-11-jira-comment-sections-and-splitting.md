# JIRA Comment Sections and Splitting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Webhook S1 JIRA comment bo'limlarini kompaniya sozlamasidan boshqarish va uzun S1/S2 commentlarni mazmun yo'qotmasdan umumiy publisher orqali bir nechta JIRA commentga bo'lib yozish.

**Architecture:** S1 va S2 formatterlari servisga xos to'liq ADF/simple natijani yaratadi. Yangi `jira_comment_publisher` moduli tayyor hujjatni o'lchaydi, valid ADF yoki plain-text qismlarga ajratadi, hint va raqamlangan qismlarni `JiraCommentWriter` orqali yuboradi; writer esa JIRA response turini yo'qotmaydigan natija qaytaradi. Webhook S1 alohida `jira_comment_sections` settingini formatterga uzatadi, S2 esa sozlamasiz barcha testcase kontentini publisherga beradi.

**Tech Stack:** Python 3.11, FastAPI/Pydantic, requests/python-jira, ADF JSON, Next.js 16 App Router, TypeScript/React.

## Global Constraints

- Ish faqat `dev1` branchda bajariladi.
- Manual Checker UI natijasi o'zgarmaydi; `jira_comment_sections` faqat webhook S1 JIRA publication qatlamiga ta'sir qiladi.
- S1 default bo'limlari: `statistics`, `ai_pipeline`, `summary`, `completed`, `failed`, `skipped`, `issues` — yettalasi ham yoqilgan.
- S2 uchun bo'lim settingi bo'lmaydi; testcase kontenti doim to'liq saqlanadi.
- Uzun S1/S2 mazmuni qisqartirilmaydi; hint va `1/N` dan `N/N` gacha qismlarga bo'linadi.
- `[AI_S1]` va `[AI_S2]` markerlari o'zgarmaydi.
- ADF va simple fallback ikkala yo'lda ham bo'lish ishlaydi.
- S1/S2 barcha kerakli commentlar yozilgandagina `done` bo'ladi.
- Webhook, UI va worker bir xil multi-agent engine ishlatishda davom etadi; o'zgarish publication qatlamida.
- Test buyruqlari faqat foydalanuvchi alohida ruxsat bergandan keyin ishga tushiriladi.
- `PROGRESS_LOG.md` yangilanmaydi.

---

### Task 1: JIRA writer natija kontrakti va umumiy splitter/publisher

**Files:**
- Create: `utils/jira/jira_comment_publisher.py`
- Modify: `utils/jira/jira_comment_writer.py`
- Test: `tests/test_jira_comment_publisher.py`

**Interfaces:**
- Produces: `JiraCommentWriteResult(success: bool, status_code: int | None, response_text: str, error: str)`.
- Produces: `JiraCommentPublishResult(success: bool, part_count: int, split: bool, error: str)`.
- Produces: `JiraCommentPublisher.publish_adf(task_key: str, document: dict, *, marker: str, service_name: str, simple_fallback: Callable[[], str] | None = None) -> JiraCommentPublishResult`.
- Produces: `JiraCommentPublisher.publish_text(task_key: str, text: str, *, marker: str, service_name: str) -> JiraCommentPublishResult`.
- Consumes: existing `JiraCommentWriter` credentials/session and ADF documents from both formatters.

- [ ] **Step 1: Write focused failing tests for response classification**

Add tests that construct `JiraCommentWriter` with `__new__`, inject a fake session,
and verify success and content-limit details are preserved:

```python
def test_adf_result_preserves_content_limit_response():
    writer = JiraCommentWriter.__new__(JiraCommentWriter)
    writer.server = "https://jira.example.com"
    writer._session = FakeSession(
        FakeResponse(400, '{"errorMessages":["CONTENT_LIMIT_EXCEEDED"]}')
    )

    result = writer.add_comment_adf_result("DEV-1", _doc(_paragraph("x")))

    assert result.success is False
    assert result.status_code == 400
    assert result.content_limit_exceeded is True
```

- [ ] **Step 2: With test permission, run the writer contract test and confirm RED**

Run: `./.venv/bin/pytest -q tests/test_jira_comment_publisher.py::test_adf_result_preserves_content_limit_response`

Expected: FAIL because `add_comment_adf_result` and `JiraCommentWriteResult` do not exist.

- [ ] **Step 3: Add the detailed writer result without breaking bool callers**

Implement in `jira_comment_writer.py`:

```python
@dataclass(frozen=True)
class JiraCommentWriteResult:
    success: bool
    status_code: int | None = None
    response_text: str = ""
    error: str = ""

    @property
    def content_limit_exceeded(self) -> bool:
        value = f"{self.response_text} {self.error}".upper()
        return "CONTENT_LIMIT_EXCEEDED" in value or "32767" in value


def add_comment_adf_result(self, task_key: str, adf_document: Dict) -> JiraCommentWriteResult:
    response = self.session.post(
        f"{self.server}/rest/api/3/issue/{task_key}/comment",
        json={"body": adf_document},
    )
    if response.status_code == 201:
        return JiraCommentWriteResult(True, response.status_code, response.text)
    log.log_error(task_key, "ADF comment", f"Failed: {response.status_code} - {response.text}")
    return JiraCommentWriteResult(False, response.status_code, response.text)


def add_comment_adf(self, task_key: str, adf_document: Dict) -> bool:
    return self.add_comment_adf_result(task_key, adf_document).success
```

Exception yo'lida `JiraCommentWriteResult(False, error=str(exc))` qaytaring.
Mavjud `add_comment()` bool interfeysini backward compatibility uchun saqlang.

- [ ] **Step 4: Write failing pure splitter tests**

Tests must cover top-level nodes, one oversized expand, one oversized text node,
Unicode and exact content preservation:

```python
def test_split_adf_preserves_all_original_text():
    source = _doc(
        _paragraph("[AI_S1]"),
        _heading("Checker — 33%"),
        _expand("REQ-1", "Ўзбекча matn " * 400),
        _expand("REQ-2", "Ikkinchi talab " * 400),
    )

    parts = split_adf_document(
        source,
        max_chars=1200,
        marker="[AI_S1]",
        task_key="DEV-8843",
    )

    assert len(parts) > 1
    assert _original_business_text(parts) == _original_business_text([source])
    assert all(adf_text_length(part) <= 1200 for part in parts)
```

Plain text uchun ham newline/gap/hard-slice fallbackdan keyin
`"".join(raw_chunks) == source_text` invariantini tekshiring.

- [ ] **Step 5: With test permission, run splitter tests and confirm RED**

Run: `./.venv/bin/pytest -q tests/test_jira_comment_publisher.py -k "split"`

Expected: FAIL because the splitter module does not exist.

- [ ] **Step 6: Implement lossless ADF and text split primitives**

Create `jira_comment_publisher.py` with focused pure helpers:

```python
JIRA_COMMENT_TARGET_CHARS = 30_000
JIRA_COMMENT_RETRY_TARGET_CHARS = 15_000


def adf_text_length(value: Any) -> int:
    if isinstance(value, dict):
        return len(str(value.get("text") or "")) + sum(adf_text_length(v) for k, v in value.items() if k != "text")
    if isinstance(value, list):
        return sum(adf_text_length(item) for item in value)
    return 0
```

`split_text_lossless(text: str, max_chars: int) -> list[str]` newline, keyin gap
va space chegarasini tanlasin; delimiter bir chunk ichida qolishi sabab
`"".join(chunks) == text` doim bajarilsin.

`split_adf_document(document: dict, *, max_chars: int, marker: str,
task_key: str) -> list[dict]` top-level node'larni partition qilsin. Oversized
container ayni type/attrs bilan child chunklarga clone qilinsin; oversized text
node `split_text_lossless` orqali bo'linsin.

Har part valid `{"version": 1, "type": "doc", "content": [node]}` shaklida
bo'lsin; real `content`da bir yoki undan ko'p valid node bo'lishi mumkin.
Publisher qo'shadigan marker/task/part metadata splitter budgetiga oldindan
kiritilsin.

- [ ] **Step 7: Write failing publication flow tests**

Use a fake writer and verify three paths:

```python
def test_publish_long_adf_writes_hint_then_numbered_parts():
    writer = FakeWriter()
    publisher = JiraCommentPublisher(writer, target_chars=500)

    result = publisher.publish_adf(
        "DEV-8843",
        _large_doc(),
        marker="[AI_S1]",
        service_name="Servis-1",
    )

    assert result.success is True
    assert result.split is True
    assert result.part_count >= 2
    assert "bo'lib yuboriladi" in _text(writer.adf_documents[0])
    assert "Qism: 1/" in _text(writer.adf_documents[1])
```

Also assert: a short document produces exactly one write/no hint; a first
`CONTENT_LIMIT_EXCEEDED` response triggers retry-target splitting; any failed
hint/part returns `success=False`; long simple text is split losslessly.

- [ ] **Step 8: Implement `JiraCommentPublisher`**

The publisher must:

```python
@dataclass(frozen=True)
class JiraCommentPublishResult:
    success: bool
    part_count: int = 0
    split: bool = False
    error: str = ""


class JiraCommentPublisher:
    def __init__(
        self,
        writer: JiraCommentWriter,
        target_chars: int = JIRA_COMMENT_TARGET_CHARS,
    ):
        self.writer = writer
        self.target_chars = target_chars
```

Classga interface blokida belgilangan `publish_adf()` va `publish_text()`
metodlarini qo'shing.

Single ADF write non-length errorida `simple_fallback()` bo'lsa text publisherga
o'ting. Length aniqlanganda hintni va barcha numbered partsni ADF sifatida
yozing. Har write natijasini tekshiring va task/service/part bilan log yozing.

- [ ] **Step 9: With test permission, run Task 1 tests and confirm GREEN**

Run: `./.venv/bin/pytest -q tests/test_jira_comment_publisher.py`

Expected: all tests PASS.

- [ ] **Step 10: Commit Task 1**

```bash
git add utils/jira/jira_comment_writer.py utils/jira/jira_comment_publisher.py tests/test_jira_comment_publisher.py
git commit -m "feat(jira): split oversized comments losslessly"
```

---

### Task 2: S1 webhook-only section setting and formatter support

**Files:**
- Modify: `config/app_settings.py`
- Modify: `services/api/settings_api.py`
- Modify: `utils/jira/jira_adf_formatter.py`
- Modify: `tests/test_settings_api_order_contract.py`
- Modify: `tests/test_tzpr_ui_contract.py`
- Modify: `docs/SETTINGS_DEPENDENCY_GUIDE.md`

**Interfaces:**
- Produces: `TZPRCheckerSettings.jira_comment_sections: list[str]`.
- Produces: `_parse_ordered_list(value, field_name, allowed, required_items=(), allow_empty=False) -> list[str]`; existing callers keep `allow_empty=False`.
- Produces: `JiraADFFormatter.build_comment_document(result: Any, new_status: str = "Ready to Test", footer_text: Optional[str] = None, is_recheck: bool = False, recheck_text: Optional[str] = None, visible_sections: Optional[list[str]] = None, dev_objections: Optional[list[dict]] = None, extra_scan_enabled: bool = True, jira_comment_sections: Optional[list[str]] = None) -> dict`.
- Produces: `JiraADFFormatter.build_simple_comment(result: Any, new_status: str = "Ready to Test", visible_sections: Optional[list[str]] = None, extra_scan_enabled: bool = True, jira_comment_sections: Optional[list[str]] = None) -> str`.
- Consumes: Task 1 publisher only indirectly in Task 3.

- [ ] **Step 1: Write failing setting default/validation/read-save tests**

Cover old JSON fallback, ordered-list filtering, an explicitly empty selection,
and all seven values:

```python
EXPECTED = [
    "statistics", "ai_pipeline", "summary", "completed",
    "failed", "skipped", "issues",
]


def test_jira_comment_sections_default_all_enabled():
    assert TZPRCheckerSettings().jira_comment_sections == EXPECTED


def test_jira_comment_sections_preserves_selected_order():
    settings = TZPRCheckerSettings(
        jira_comment_sections=["summary", "failed"],
    )
    assert settings.jira_comment_sections == ["summary", "failed"]


def test_jira_comment_sections_allows_empty_selection():
    settings = TZPRCheckerSettings(jira_comment_sections=[])
    assert settings.jira_comment_sections == []
```

API testida mavjud session/company fixture patterni orqali
`save_webhook_config()`ga `{"jira_comment_sections": ["summary", "failed"]}`
yuboring, keyin `read_webhook_config()` response'ida ayni ordered-listni assert
qiling.

- [ ] **Step 2: Write failing formatter toggle tests**

Build one result containing every block and assert each omitted key removes only
its mapped output. Separately assert old `visible_sections` still controls the
manual canonical requirement sections and does not substitute for the new
webhook setting.

```python
doc = formatter.build_comment_document(
    result,
    jira_comment_sections=["summary", "failed"],
)
text = str(doc)
assert "Xulosa" in text
assert "Bajarilmagan" in text
assert "Statistika" not in text
assert "AI pipeline" not in text
assert "Bajarilgan" not in text
assert "Skip" not in text
assert "Extra Scan" not in text
```

- [ ] **Step 3: With test permission, run Task 2 tests and confirm RED**

Run: `./.venv/bin/pytest -q tests/test_settings_api_order_contract.py tests/test_tzpr_ui_contract.py -k "jira_comment_sections or webhook_comment"`

Expected: FAIL because the setting and formatter argument do not exist.

- [ ] **Step 4: Add the dataclass setting and centralized validation**

In `TZPRCheckerSettings` add:

```python
_JIRA_COMMENT_SECTIONS_ALLOWED = (
    "statistics", "ai_pipeline", "summary", "completed",
    "failed", "skipped", "issues",
)
jira_comment_sections: List[str] = field(
    default_factory=lambda: list(TZPRCheckerSettings._JIRA_COMMENT_SECTIONS_ALLOWED)
)
```

Normalize duplicates/unknown values in `__post_init__`. Unlike the existing
`visible_sections`, an explicitly empty list is valid: user barcha optional
bloklarni o'chirsa marker/title/footer qoladi. Missing JSON field uses all-on
default.

- [ ] **Step 5: Extend ordered-list parsing and wire backend settings read/save**

Add `allow_empty: bool = False` to `_parse_ordered_list`; only skip its current
`if not order` HTTP 400 when `allow_empty=True`. Thread the same optional flag
through nested `_wh_ordered_list`, leaving every existing call unchanged.

Add `_JIRA_COMMENT_SECTIONS_ALLOWED` in `settings_api.py`, return the field from
`/webhook/config/read`, and parse it in save via `_wh_ordered_list` with
`required_items=()`, `allow_empty=True` and all-on default:

```python
jira_comment_sections = _wh_ordered_list(
    "jira_comment_sections",
    _JIRA_COMMENT_SECTIONS_ALLOWED,
    required_items=(),
    default=list(_JIRA_COMMENT_SECTIONS_ALLOWED),
    allow_empty=True,
)
```

- [ ] **Step 6: Apply the seven formatter gates to ADF and simple output**

Normalize `jira_comment_sections` separately from existing requirement
`visible_sections`. Gate meta stats, pipeline, summary, and the four requirement
categories in both `build_comment_document()` and `build_simple_comment()`.
Keep marker/title/score/recheck/warnings/footer unconditional.

- [ ] **Step 7: Update dependency documentation**

Document `webhook_tz_pr.jira_comment_sections -> MUSTAQIL` and explicitly state
that it affects only webhook JIRA comments; checker `visible_sections` remains
the manual UI/final-report contract.

- [ ] **Step 8: With test permission, run Task 2 tests and confirm GREEN**

Run: `./.venv/bin/pytest -q tests/test_settings_api_order_contract.py tests/test_tzpr_ui_contract.py`

Expected: all tests PASS.

- [ ] **Step 9: Commit Task 2**

```bash
git add config/app_settings.py services/api/settings_api.py utils/jira/jira_adf_formatter.py tests/test_settings_api_order_contract.py tests/test_tzpr_ui_contract.py docs/SETTINGS_DEPENDENCY_GUIDE.md
git commit -m "feat(settings): configure webhook S1 comment sections"
```

---

### Task 3: Webhook S1 and S2 publication integration

**Files:**
- Modify: `services/webhook/error_handler.py`
- Modify: `services/webhook/service_runner.py`
- Modify: `services/webhook/testcase_webhook_handler.py`
- Modify: `tests/test_tzpr_stabilization.py`
- Modify: `tests/test_testcase_multi_agent.py`

**Interfaces:**
- Consumes: `JiraCommentPublisher` and `JiraCommentPublishResult` from Task 1.
- Consumes: `settings.jira_comment_sections` and formatter arguments from Task 2.
- Produces: `_write_success_comment(task_key, result, new_status, settings, comment_writer, adf_formatter, is_recheck=False, dev_objections=None) -> bool` where `True` means all S1 JIRA comments were written.
- Preserves: `_write_testcases_comment(task_key, result, use_adf=True, footer_text=None, pr_details=None, pr_count=0, files_changed=0, company_id=None) -> tuple[bool, str]` public return shape.

- [ ] **Step 1: Write failing S1 service completion guard test**

Update/add test so a failed publication cannot call `set_service1_done`:

```python
monkeypatch.setattr(
    error_handler_module,
    "_write_success_comment",
    AsyncMock(return_value=False),
)

asyncio.run(
    service_runner.check_tz_pr_and_comment(
        task_key="DEV-1",
        new_status="READY TO TEST",
        company_id=1,
    )
)

set_service1_done.assert_not_called()
```

Also assert a successful publication still saves score and continues existing
auto-return logic.

- [ ] **Step 2: Write failing S1/S2 publisher wiring tests**

For S1 assert publisher receives `[AI_S1]`, `Servis-1`, simple fallback factory,
and the exact company `jira_comment_sections`. For S2 assert it receives
`[AI_S2]`, `Servis-2`, full testcase ADF and no section setting.

- [ ] **Step 3: With test permission, run Task 3 focused tests and confirm RED**

Run: `./.venv/bin/pytest -q tests/test_tzpr_stabilization.py tests/test_testcase_multi_agent.py -k "publication or comment_write"`

Expected: FAIL because the webhook handlers still call the bool writer directly.

- [ ] **Step 4: Return publication success from S1 comment writer**

Change `_write_success_comment` to:

```python
async def _write_success_comment(
    task_key,
    result,
    new_status,
    settings,
    comment_writer,
    adf_formatter,
    is_recheck=False,
    dev_objections=None,
) -> bool:
    adf_doc = adf_formatter.build_comment_document(
        result,
        new_status,
        footer_text=settings.tz_pr_footer_text,
        is_recheck=is_recheck,
        recheck_text=settings.recheck_comment_text,
        dev_objections=dev_objections or [],
        extra_scan_enabled=extra_scan_enabled,
        jira_comment_sections=settings.jira_comment_sections,
    )
    publication = JiraCommentPublisher(comment_writer).publish_adf(
        task_key,
        adf_doc,
        marker="[AI_S1]",
        service_name="Servis-1",
        simple_fallback=lambda: adf_formatter.build_simple_comment(
            result,
            new_status,
            extra_scan_enabled=extra_scan_enabled,
            jira_comment_sections=settings.jira_comment_sections,
        ),
    )
    return publication.success
```

- [ ] **Step 5: Guard S1 DB completion**

In `check_tz_pr_and_comment`, if `_write_success_comment` returns `False`, call
`set_service1_error(task_key, "S1 JIRA comment to'liq yozilmadi",
company_id=company_id)`, log the publication failure and return before
`set_service1_done` and auto-return.

- [ ] **Step 6: Route S2 through the shared publisher**

Replace direct ADF/simple bool writes in `_write_testcases_comment` with one
publisher call:

```python
publication = JiraCommentPublisher(writer).publish_adf(
    task_key,
    adf_doc,
    marker="[AI_S2]",
    service_name="Servis-2",
    simple_fallback=lambda: formatter.build_simple_comment(
        task_key=task_key,
        test_cases=result.test_cases,
        test_scenarios=getattr(result, "test_scenarios", []),
        agent_runs=getattr(result, "agent_runs", []),
    ),
)
success = publication.success
```

Keep the existing `(success, message)` contract so `_run_testcase_generation`
only calls `set_service2_done` when every hint/part write succeeded.

- [ ] **Step 7: With test permission, run Task 3 tests and confirm GREEN**

Run: `./.venv/bin/pytest -q tests/test_tzpr_stabilization.py tests/test_testcase_multi_agent.py`

Expected: all tests PASS.

- [ ] **Step 8: Commit Task 3**

```bash
git add services/webhook/error_handler.py services/webhook/service_runner.py services/webhook/testcase_webhook_handler.py tests/test_tzpr_stabilization.py tests/test_testcase_multi_agent.py
git commit -m "feat(webhook): publish long S1 and S2 comments in parts"
```

---

### Task 4: Webhook S1 settings UI and BFF contract

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/backend.ts`
- Modify: `frontend/src/app/api/settings/webhook/route.ts`
- Modify: `frontend/src/components/settings-panel.tsx`

**Interfaces:**
- Consumes: backend `jira_comment_sections: string[]` from Task 2.
- Produces: `WebhookSettingsView.data.jira_comment_sections: string[]`.
- Produces: `WebhookSettingsSaveRequest.jira_comment_sections: string[]`.
- Produces: `WebhookFormState.jira_comment_sections: string[]`.

- [ ] **Step 1: Add TypeScript contract first**

Add the field to webhook view/save types, BFF payload and local form state. Use:

```ts
const JIRA_COMMENT_SECTIONS = [
  "statistics",
  "ai_pipeline",
  "summary",
  "completed",
  "failed",
  "skipped",
  "issues",
] as const;
```

GET fallback and empty form default must return all seven. POST must forward the
actual user-selected array; it must not overwrite it with the old five-item
`CHECKER_COMMENT_SECTIONS` constant.

- [ ] **Step 2: Render seven Webhook → Servis-1 toggles**

Add a `JIRA comment bo'limlari` inner card under the S1 webhook card. Labels:

```ts
const JIRA_COMMENT_SECTION_LABELS = {
  statistics: "Statistika",
  ai_pipeline: "AI pipeline",
  summary: "Xulosa",
  completed: "Bajarilgan",
  failed: "Bajarilmagan",
  skipped: "Skip qilingan",
  issues: "Qo'shimcha tekshiruv",
};
```

Each `ToggleRow` must preserve order and toggle only one key:

```tsx
onChange={(enabled) =>
  updateWebhookField(
    "jira_comment_sections",
    enabled
      ? JIRA_COMMENT_SECTIONS.filter((key) =>
          key === section || webhookForm.jira_comment_sections.includes(key),
        )
      : webhookForm.jira_comment_sections.filter((key) => key !== section),
  )
}
```

All toggles off is allowed; marker/title/footer still appear according to the
backend contract.

- [ ] **Step 3: With test permission, run frontend static checks**

Run from `frontend/`:

```bash
npm run typecheck
npm run lint
```

Expected: both commands exit 0.

- [ ] **Step 4: Commit Task 4**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/backend.ts frontend/src/app/api/settings/webhook/route.ts frontend/src/components/settings-panel.tsx
git commit -m "feat(frontend): configure S1 Jira comment sections"
```

---

### Task 5: Cross-path regression verification and final review

**Files:**
- Modify if contract coverage requires: `tests/test_full_system.py`
- Modify if copy/contract changed: `docs/superpowers/specs/2026-08-11-jira-comment-sections-and-splitting-design.md`

**Interfaces:**
- Verifies Tasks 1-4 as one webhook publication flow.
- Does not change checker/testcase multi-agent engine entry points.

- [ ] **Step 1: Add/adjust one integration-level regression test**

The test must prove:

```python
assert run_multi_agent_for_webhook_called_once
assert publisher_received_company_jira_sections
assert all_parts_written_before_set_service1_done
assert s2_publisher_has_no_section_filter
```

Use mocks; no real JIRA, GitHub, Gemini or production DB calls.

- [ ] **Step 2: With test permission, run the complete focused backend suite**

Run:

```bash
./.venv/bin/pytest -q \
  tests/test_jira_comment_publisher.py \
  tests/test_settings_api_order_contract.py \
  tests/test_tzpr_ui_contract.py \
  tests/test_tzpr_stabilization.py \
  tests/test_testcase_multi_agent.py
```

Expected: all tests PASS with no skip caused by missing DB; these tests should be
pure/no-db where applicable.

- [ ] **Step 3: With test permission, run repo-required quality gates**

Run from repository root:

```bash
python -m ruff check .
```

Run from `frontend/`:

```bash
npm run typecheck
npm run lint
```

Expected: all commands exit 0.

- [ ] **Step 4: Inspect the final diff and marker invariants**

Run:

```bash
git diff --check
git diff origin/dev1..HEAD -- \
  config/app_settings.py services/api/settings_api.py \
  utils/jira services/webhook frontend/src docs/SETTINGS_DEPENDENCY_GUIDE.md
rg -n "\[AI_S1\]|\[AI_S2\]" utils/jira services/webhook
```

Confirm no secret values, production credentials, DB DDL or engine fork was
introduced.

- [ ] **Step 5: Commit final integration adjustments if any**

```bash
git add tests/test_full_system.py docs/superpowers/specs/2026-08-11-jira-comment-sections-and-splitting-design.md
git commit -m "test: cover split Jira comment publication"
```

- [ ] **Step 6: Report completion without deploy**

Summarize commits, files, verification commands/results and explicitly state
that no production deploy occurred. Push/deploy only on a separate explicit
user instruction.
