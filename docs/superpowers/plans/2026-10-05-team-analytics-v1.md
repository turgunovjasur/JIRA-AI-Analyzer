# Team Analytics v1 Implementation Plan

**Goal:** Bitta status sozlamasi bilan task vaqtini hisoblash va kelajak analytics uchun Jira tarixini yig'ish.
**Architecture:** Append-only normalized Jira events + versioned company settings; pure replay engine; tenant-scoped API va Next.js dashboard.
**Tech Stack:** PostgreSQL, FastAPI, Next.js/React.
**Spec:** ../specs/2026-10-05-team-analytics-v1.md

## Constraints

- Foydalanuvchi kod yozishni boshlashni aniq so'radi; shu sessiyada bajariladi.
- Testlar yoziladi, lekin foydalanuvchi alohida so'ramaguncha ishga tushirilmaydi.
- PROGRESS_LOG.md va mavjud boshqa o'zgarishlarga tegilmaydi.

## Tasks

- [x] Migration: analytics event va settings tarix jadvallari, tenant/source deduplication va replay indekslari.
- [x] Pure engine: pause/resume, assignee almashish, late events, settings versiyasi, unknown initial time.
- [x] Repository va webhook: auth/subscription tekshiruvidan keyin, AI triggerlardan oldin analytics saqlash.
- [x] API: company-admin/super-admin tenant scope, fresh entitlement tekshiruvi, bitta settings field, paginated snapshot.
- [x] Frontend: addon catalog/toggle, navigation, dashboard va bitta status settings field.
- [x] Permission matrix va rollout notes; statik diff ko'rigi. Runtime test/build/migration bajarilmaydi.

## Review focus

Duplicate deliveries, out-of-order timestamps, first observation without historical start, changing assignee/settings while active, cross-tenant access. Regression tests these behaviors pin down; execution requires user request.

## Verification status

Python source AST sintaksis ko‘rigi va `git diff --check` bajarildi. Bu runtime test o‘rnini bosmaydi. Testlar yozildi, ishga tushirilmadi; frontend build va PostgreSQL integratsiya tekshiruvi qolmoqda.
