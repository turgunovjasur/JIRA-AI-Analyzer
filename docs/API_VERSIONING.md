# API Versioning va Error Envelope

## Versioning: `/api/v1` alias

Barcha mavjud `/api/*` endpointlar qo'shimcha ravishda `/api/v1/*` ostida ham
ishlaydi (alias). Ikkalasi AYNAN bir xil handler'ga boradi:

```
/api/monitoring/snapshot      ==  /api/v1/monitoring/snapshot
/api/auth/login               ==  /api/v1/auth/login
/api/tzpr/runs                ==  /api/v1/tzpr/runs
...
```

Qoidalar:

- **Joriy yo'llar = v1 alias.** Eski (versiyasiz) yo'llar o'zgarmaydi va
  qo'llab-quvvatlanadi — hech narsa sinmaydi.
- **Breaking change** kerak bo'lsa, yangi endpoint `/api/v2/...` ostida
  ochiladi; `/api/...` va `/api/v1/...` eski xatti-harakatni saqlaydi.
- **Webhook endpointlar** (`/webhook/jira`, `/webhook/jira/{company_code}`)
  versiyalanmaydi — JIRA konfiguratsiyasi barqaror qolishi uchun.
- `/health`, `/metrics`, `/manual/*` kabi ildiz endpointlar ham versiyasiz.

Texnik joy: `services/webhook/jira_webhook_handler.py` → `_mount_api_v1_aliases()`
(modul oxirida, barcha route'lar ro'yxatdan o'tgach chaqiriladi). Alias route'lar
OpenAPI schema'da ko'rsatilmaydi (`include_in_schema=False`) — hujjat sifatida
versiyasiz yo'llar qoladi.

## Yagona xato konverti (error envelope)

### Hozirgi holat (additive, backward compatible)

`HTTPException` va request-validatsiya xatolari uchun global handler quyidagi
konvertni qaytaradi:

```json
{
  "detail": "...",                      // AVVALGIDEK — string yoki obyekt
  "error": {
    "code": "not_found",                // barqaror mashina-o'qiydigan kod
    "message": "Task not found"         // inson uchun xabar
  }
}
```

- `detail` maydoni FastAPI default'i bilan AYNAN mos qoladi — frontend BFF
  (`frontend/src/lib/backend.ts` → `unwrapBackendErrorPayload`) shuni o'qiydi.
- `error` obyekt yangi, qo'shimcha maydon. Yangi klientlar shundan foydalansin.
- Validatsiya xatolari (422): `detail` — FastAPI'ning odatiy xatolar ro'yxati,
  `error.code = "validation_error"`.
- `error.code` qiymatlari status'dan olinadi: `bad_request`, `unauthorized`,
  `forbidden`, `not_found`, `conflict`, `validation_error`, `rate_limited`,
  `internal_error`, `bad_gateway`, `service_unavailable`
  (boshqa 4xx → `http_error`, boshqa 5xx → `internal_error`).

### Preflight payload (o'zgarmagan istisno)

`POST /api/tzpr/runs` va `POST /api/testcase/runs` preflight muvaffaqiyatsiz
bo'lsa 400 bilan `core/module_start_preflight.py::to_error_payload()` shaklini
TO'G'RIDAN-TO'G'RI (detail'siz) qaytaradi:

```json
{
  "success": false,
  "module_key": "...",
  "task_key": "...",
  "run_state": "error",
  "active_phase": "preflight",
  "error": "…xabar (string!)",
  "error_message": "…xabar",
  "status_banner": { "level", "code", "title", "message", "meta", "actions" },
  "preflight_checks": [ ... ],
  "gemini_quota": { ... }              // ixtiyoriy
}
```

Bu shakl ataylab o'zgartirilmagan (frontend unga bog'langan). DIQQAT: bu yerda
`error` — string, global konvertda esa `error` — obyekt.

### Maqsad (v2 uchun)

`/api/v2` da barcha xato javoblari yagona superset konvertga o'tadi:

```json
{
  "detail": <eski shakl, o'tish davri uchun>,
  "error": { "code": "...", "message": "..." },
  "meta": { ...modulga xos qo'shimcha ma'lumot (masalan preflight_checks)... }
}
```

Ya'ni preflight kabi modulga xos payload'lar ham `error` obyekt + `meta` ichiga
ko'chiriladi; `error` maydonining string varianti bekor qilinadi.

## Monitoring pagination (additive)

`GET /api/monitoring/snapshot` endi `limit` (default 200, max 1000) va
`offset` (default 0) query parametrlarini qabul qiladi — `recent_tasks`
ro'yxatiga SQL darajasida qo'llanadi (`blocked_tasks` ham `limit` bilan
cheklanadi). Javobga qo'shimcha maydonlar qo'shildi:

```json
{ "total": 1234, "limit": 200, "offset": 0, ... }
```

`total` — filtr bo'yicha `recent_tasks`ning umumiy soni. Eski maydonlar
o'zgarmagan; ilgari cheksiz ro'yxat endi default 200 ta bilan cheklanadi.
