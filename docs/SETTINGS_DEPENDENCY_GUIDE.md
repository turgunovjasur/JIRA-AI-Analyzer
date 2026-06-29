# Settings Dependency Guide

Ushbu hujjat `Settings` bo'limidagi sozlamalarni `Tab -> Modul -> Setting` ko'rinishida hujjatlashtiradi.
Har bir setting uchun roli ko'rsatiladi:

- `ONA`: child setting(lar)ni boshqaradi
- `BOLA`: parentga bog'liq setting
- `MUSTAQIL`: parent-child bog'liqligi yo'q
- `SOFT`: UI hide/show uchun qulay, lekin backendda qisman mustaqil ishlashi mumkin

## 1) AI & Integrations tab

### Integrations

- `jira_server` -> `MUSTAQIL`
- `jira_email` -> `MUSTAQIL`
- `jira_project_keys` -> `MUSTAQIL`
- `jira_token` -> `MUSTAQIL`
- `github_org` -> `MUSTAQIL`
- `github_token` -> `MUSTAQIL`
- `figma_token` -> `MUSTAQIL`
- `gemini_api_key_1` -> `MUSTAQIL`
- `gemini_api_key_2` -> `MUSTAQIL`

## 2) Modullar tab

### Checker

- `checker.read_comments_enabled` -> `ONA`
- `checker.max_comments_to_read` -> `BOLA` (parent: `checker.read_comments_enabled`)
- `checker.default_use_smart_patch` -> `MUSTAQIL`
- `checker.visible_sections` -> `MUSTAQIL`
- `checker.ai_data_section_order` -> `MUSTAQIL`

### Testcase

- `testcase.read_comments_enabled` -> `ONA`
- `testcase.max_comments_to_read` -> `BOLA` (parent: `testcase.read_comments_enabled`)
- `testcase.default_test_types` -> `MUSTAQIL`
- `testcase.testcases_per_requirement` -> `MUSTAQIL`
- `testcase.ai_data_section_order` -> `MUSTAQIL`
- `testcase.agent1_primary_model` -> `MUSTAQIL`
- `testcase.agent1_fallback_model` -> `MUSTAQIL`
- `testcase.agent2_primary_model` -> `MUSTAQIL`
- `testcase.agent2_fallback_model` -> `MUSTAQIL`
- `testcase.agent3_primary_model` -> `MUSTAQIL`
- `testcase.agent3_fallback_model` -> `MUSTAQIL`

## 3) Webhook tab

### Webhook TZ-PR

- `webhook_tz_pr.auto_return_enabled` -> `ONA`
- `webhook_tz_pr.return_threshold` -> `BOLA` (parent: `webhook_tz_pr.auto_return_enabled`)
- `webhook_tz_pr.return_notification_text` -> `BOLA(SOFT)` (parent: `webhook_tz_pr.auto_return_enabled`)

- `webhook_tz_pr.skip_code` -> `ONA`
- `webhook_tz_pr.max_skip_check_comments` -> `BOLA` (parent: `webhook_tz_pr.skip_code`)
- `webhook_tz_pr.skip_comment_text` -> `BOLA(SOFT)` (parent: `webhook_tz_pr.skip_code`)

- `webhook_tz_pr.trigger_status` -> `ONA`
- `webhook_tz_pr.trigger_status_aliases` -> `BOLA` (parent: `webhook_tz_pr.trigger_status`)

- `webhook_tz_pr.read_comments_enabled` -> `ONA`
- `webhook_tz_pr.max_comments_to_read` -> `BOLA` (parent: `webhook_tz_pr.read_comments_enabled`)

- `webhook_tz_pr.return_status` -> `MUSTAQIL (MUHIM ISTISNO)`
- `webhook_tz_pr.min_tz_description_chars` -> `MUSTAQIL`
- `webhook_tz_pr.allowed_issue_types` -> `MUSTAQIL`
- `webhook_tz_pr.excluded_assignees` -> `MUSTAQIL`
- `webhook_tz_pr.dev_comments_max` -> `MUSTAQIL`
- `webhook_tz_pr.pr_max_files` -> `MUSTAQIL`
- `webhook_tz_pr.ai_data_section_order` -> `MUSTAQIL`
- `webhook_tz_pr.visible_sections` -> `MUSTAQIL`
- `webhook_tz_pr.show_contradictory_comments` -> `MUSTAQIL`
- `webhook_tz_pr.default_use_smart_patch` -> `MUSTAQIL`
- `webhook_tz_pr.ai_max_output_tokens` -> `MUSTAQIL`
- `webhook_tz_pr.use_adf_format` -> `MUSTAQIL`
- `webhook_tz_pr.show_statistics` -> `MUSTAQIL`
- `webhook_tz_pr.show_compliance_score` -> `MUSTAQIL`
- `webhook_tz_pr.tz_pr_footer_text` -> `MUSTAQIL`
- `webhook_tz_pr.recheck_comment_text` -> `MUSTAQIL`

### Webhook Testcase (Auto-comment)

- `webhook_testcase.auto_comment_enabled` -> `ONA`
- `webhook_testcase.auto_comment_trigger_status` -> `BOLA` (parent: `webhook_testcase.auto_comment_enabled`)
- `webhook_testcase.auto_comment_trigger_aliases` -> `BOLA` (parent: `webhook_testcase.auto_comment_enabled`)
- `webhook_testcase.default_test_types` -> `BOLA` (parent: `webhook_testcase.auto_comment_enabled`)
- `webhook_testcase.testcases_per_requirement` -> `BOLA` (parent: `webhook_testcase.auto_comment_enabled`)
- `webhook_testcase.ai_data_section_order` -> `BOLA` (parent: `webhook_testcase.auto_comment_enabled`)
- `webhook_testcase.read_comments_enabled` -> `BOLA-ONA` (parent: `webhook_testcase.auto_comment_enabled`)
- `webhook_testcase.max_comments_to_read` -> `BOLA` (parent: `webhook_testcase.read_comments_enabled`)
- `webhook_testcase.ai_max_output_tokens` -> `BOLA` (parent: `webhook_testcase.auto_comment_enabled`)
- `webhook_testcase.use_adf_format` -> `BOLA` (parent: `webhook_testcase.auto_comment_enabled`)
- `webhook_testcase.testcase_footer_text` -> `BOLA` (parent: `webhook_testcase.auto_comment_enabled`)

## 4) Tizim tab

### Queue/System

- `queue.queue_enabled` -> `ONA(SOFT)`
- `queue.task_wait_timeout` -> `BOLA(SOFT)` (parent: `queue.queue_enabled`)
- `queue.gemini_min_interval` -> `BOLA(SOFT)` (parent: `queue.queue_enabled`)

- `queue.blocked_retry_delay` -> `MUSTAQIL`
- `queue.blocked_check_interval` -> `MUSTAQIL`
- `queue.key_freeze_duration` -> `MUSTAQIL`
- `queue.ai_max_retries` -> `MUSTAQIL`
- `queue.ai_max_input_tokens` -> `MUSTAQIL`
- `queue.chars_per_token` -> `MUSTAQIL`
- `queue.db_busy_timeout` -> `MUSTAQIL`
- `queue.db_connection_timeout` -> `MUSTAQIL`
- `queue.http_timeout` -> `MUSTAQIL`
- `queue.executor_timeout` -> `MUSTAQIL`

---

## UI Hide/Show qoidalari (yakuniy)

- `checker.read_comments_enabled = false` -> hide `checker.max_comments_to_read`
- `testcase.read_comments_enabled = false` -> hide `testcase.max_comments_to_read`

- `webhook_tz_pr.auto_return_enabled = false` ->
  - hide `webhook_tz_pr.return_threshold`
  - hide `webhook_tz_pr.return_notification_text`

- `webhook_tz_pr.skip_code` bo'sh ->
  - hide `webhook_tz_pr.max_skip_check_comments`
  - hide `webhook_tz_pr.skip_comment_text`

- `webhook_tz_pr.trigger_status` bo'sh -> hide `webhook_tz_pr.trigger_status_aliases`
- `webhook_tz_pr.read_comments_enabled = false` -> hide `webhook_tz_pr.max_comments_to_read`

- `webhook_testcase.auto_comment_enabled = false` ->
  - hide `webhook_testcase.auto_comment_trigger_status`
  - hide `webhook_testcase.auto_comment_trigger_aliases`
  - hide `webhook_testcase.default_test_types`
  - hide `webhook_testcase.testcases_per_requirement`
  - hide `webhook_testcase.ai_data_section_order`
  - hide `webhook_testcase.read_comments_enabled`
  - hide `webhook_testcase.max_comments_to_read`
  - hide `webhook_testcase.ai_max_output_tokens`
  - hide `webhook_testcase.use_adf_format`
  - hide `webhook_testcase.testcase_footer_text`

- `webhook_testcase.read_comments_enabled = false` -> hide `webhook_testcase.max_comments_to_read`

- `queue.queue_enabled = false` (SOFT) ->
  - hide `queue.task_wait_timeout`
  - hide `queue.gemini_min_interval`

## Muhim istisnolar (doim ko'rinsin)

- `webhook_tz_pr.return_status` doim ko'rinsin.
  Sabab: `auto_return_enabled=false` bo'lsa ham `pr_not_found/pr_not_merged/tz_too_short` oqimida return status ishlatiladi.
