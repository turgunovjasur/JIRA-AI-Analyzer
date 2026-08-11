# JIRA Dynamic PR Providers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** JIRA OAuth GitHub providerlari ostidagi PR'larni webhook, UI va worker uchun dinamik topish.

**Architecture:** JIRA development summary provider turlarining source of truth'i bo'ladi. Har provider detail endpoint orqali tekshiriladi; GitHub PR URLlari birlashtirilib dedupe qilinadi, summary ishlamasa eski provider fallback saqlanadi.

**Tech Stack:** Python 3.11, requests, pytest.

## Global Constraints

- Ish bevosita `main` worktree'da bajariladi.
- Production deploydan oldin PostgreSQL backup olinadi.
- `rsync --delete` va Docker volume o'chirish taqiqlanadi.
- Avtomatik testlar foydalanuvchi alohida so'ramagani uchun ishga tushirilmaydi.

---

### Task 1: Dynamic JIRA PR provider discovery

**Files:**
- Modify: `utils/jira/jira_client.py:450`
- Test: `tests/test_jira_client.py`

**Interfaces:**
- Consumes: JIRA `/rest/dev-status/1.0/issue/summary` va `/issue/detail` javoblari.
- Produces: `extract_pr_urls_dev_status(issue_key, issue_id) -> list[dict]` mavjud kontraktini saqlaydi.

- [ ] **Step 1: Regression test yozish**

OAuth provider summary'dan topilib detail chaqirilishi va bir xil URL dedupe
qilinishini fake HTTP javoblari bilan tekshiruvchi testlar qo'shiladi.

- [ ] **Step 2: Minimal implementatsiya**

Summary'dan `pullrequest.byInstanceType` kalitlarini olish, bo'sh/xato holatda
`GitHub` fallback qilish, barcha detail bloklarini yurish va URL dedupe qo'shiladi.

- [ ] **Step 3: Statik verifikatsiya**

`git diff --check` va Python compile orqali patch sintaksisi tekshiriladi.
Pytest repo qoidasi bo'yicha alohida ruxsatsiz ishga tushirilmaydi.

- [ ] **Step 4: Release**

Main commit/push, production DB backup, exclude ro'yxatli rsync, Docker rebuild,
health va DEV-8843 live provider probe bajariladi.

