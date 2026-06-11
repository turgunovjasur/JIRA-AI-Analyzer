# Reja: Multi-agent checker token optimizatsiyasi + per-agent model selection

## Context (nima uchun)

Hozir TZ-PR multi-agent checker bitta taskni tekshirganda Gemini'da ~$1–2 turadi.
Sabab arxitekturaviy: **Agent2 (Verifier) har bir requirement uchun alohida
Gemini call qiladi va har safar to'liq kod diff'ini qaytadan yuboradi.** Agent1 12 ta
requirement chiqarsa → 13+ ta call, har birida bir xil kod. Caching umuman yo'q,
3 agent ham `gemini-2.5-pro` ishlatadi (Agent1/Agent3 kod tahlil qilmaydi — Pro ortiqcha).

Maqsad: token sarfini ~10× kamaytirish (tahlil sifatini pasaytirmasdan) va super
admin → kompaniya ierarxiyasini saqlagan holda har agent uchun alohida model
tanlash imkonini qo'shish.

**User qarorlari:** bosqichma-bosqich; har agent uchun primary+fallback model;
Agent2'ga to'liq kod kontenti qoladi (Smart Patch saqlanadi), caching bilan arzonlashtiriladi.

---

## Yondashuv: 2 faza

- **FAZA 1** — sifatga xavfsiz, tez foyda: implicit caching (prompt qayta tartiblash)
  + per-agent model selection (settings + super admin default + kompaniya override + UI).
  Default tier: Agent1=flash, Agent2=pro, Agent3=flash.
- **FAZA 2** — chuqurroq: explicit context caching, requirement batching, diff tozalash,
  parallel rate-limit/freeze tuzatish.

Faza 1 yakunida narx ~$1.5 → ~$0.3 kutiladi; Faza 2 bilan ~$0.10–0.15.

---

## FAZA 1

### 1A. Agent2 promptini qayta tartiblash → implicit caching

`gemini-2.5` modellarida implicit caching avtomatik yoqilgan: ketma-ket so'rovlarda
**bir xil bo'lgan boshlang'ich prefiks** ~75% chegirma bilan keladi. Hozir
`build_single_prompt` da o'zgaruvchan `REQUIREMENT` blok promptning **o'rtasida**,
katta `CODE CHANGES` esa undan **keyin** — shuning uchun kod cache'lanmaydi.

**O'zgarish — `services/checkers/tzpr_agents/agent2.py`:**
- `build_single_prompt()` (95–149-qatorlar): tartibni o'zgartirish — avval barcha
  o'zgarmas qism (statik ko'rsatmalar + `PR SUMMARY` + `CODE CHANGES`), eng oxirida
  o'zgaruvchan qism (`REQUIREMENT` JSON + `id` ko'rsatilgan output namunasi).
  Natijada barcha per-requirement call'larda prefiks bayt-bayt bir xil → kod 2-chi
  call'dan boshlab cache'dan keladi.
- `build_extra_scan_prompt()` (42–92-qatorlar): xuddi shunday — kod blokini boshiga.
- `code_changes[:180000]` truncation o'zgarmaydi.

Bu faqat string tartibini o'zgartiradi — mantiq, schema, parsing tegmaydi.

### 1B. Per-agent model selection (super admin default → kompaniya override)

#### Backend — settings dataclass
**`config/app_settings.py` → `TZPRCheckerSettings` (119-qator):**
- 6 ta yangi maydon (default `""` = "meros qilib ol"):
  `agent1_primary_model`, `agent1_fallback_model`, `agent2_primary_model`,
  `agent2_fallback_model`, `agent3_primary_model`, `agent3_fallback_model`.
- Har biriga mos `*_help` matn (mavjud help-pattern bo'yicha).
- `__post_init__` da qattiq validatsiya QILINMAYDI (yangi Gemini modellari kod
  o'zgartirmasdan ishlasin; curated ro'yxat faqat UI dropdownda).

#### Backend — super admin global default
**`config/app_settings.py`:**
- Yangi `_apply_global_checker_overrides(settings)` funksiyasi — `_apply_global_queue_overrides`
  (765-qator) namunasida. `global_settings` jadvalidan `checker_agent1_primary_model`,
  `checker_agent1_fallback_model`, ... 6 ta kalitni o'qiydi va `dc_replace` bilan
  **ham `settings.tz_pr_checker`, ham `settings.webhook_tz_pr`** ga qo'llaydi.
- `get_app_settings()` (809-qator) `return` zanjiriga qo'shiladi:
  `_apply_global_checker_overrides(_apply_global_queue_overrides(settings))`.
- Kompaniya/user merge (`get_app_settings_for_company` 847, `get_app_settings_for_user`
  903) avtomatik global ustiga yoziladi — `_merge()` da bo'sh string'li model
  qiymatini o'tkazib yuborish kerak (bo'sh = meros, override emas).

#### Backend — model resolutsiya wiring
**`utils/ai/gemini_helper.py`:**
- `__init__` ga ixtiyoriy `fallback_model_name` parametri. `_get_fallback_model()`
  (156-qator) avval shu qiymatni, bo'lmasa env'ni qaytaradi. Shunda fallback ham
  per-agent bo'ladi.

**`services/checkers/tzpr_constants.py`:**
- `resolve_agent_models(checker_settings)` helper: har agent uchun
  `(primary, fallback)` qaytaradi — settings maydoni bo'sh bo'lsa `PRO_MODEL_NAME` /
  `FALLBACK_MODEL_NAME` ga tushadi. `AGENT_SEQUENCE` shu helper bilan dinamiklashtiriladi.

**`services/checkers/tzpr_orchestrator.py`:**
- `_pro_model()` (268-qator) → `_model_for_agent(agent_key)` ga aylantiriladi:
  `self.service._get_settings()` dan agent modelini oladi, mos `GeminiHelper`
  (primary + fallback) qaytaradi. Agentlar bir xil emas — har agent o'z helper'i.

**`services/checkers/tzpr_agent_runner.py`:**
- `_run_agent1` → agent1 modeli; `_run_agent3` → agent3 modeli.
- `_call_agent2_single_raw_isolated` (621) va `_call_agent2_extra_scan_raw` (636)
  → agent2 modeli (primary+fallback `GeminiHelper` ga uzatiladi).

#### Backend — API
- **`services/api/settings_api.py`** — checker (webhook/user) settings read/save
  endpointlariga 6 yangi maydonni qo'shish (kompaniya admin override uchun).
- **`services/api/internal_rpc_api.py`** + **`utils/auth/auth_db.py`** — super admin
  AI-defaults RPC'ga 6 ta `checker_agent*_model` global kalitini qo'shish
  (`set_global_setting` / `get_global_setting` orqali).

#### Frontend (Next.js)
- **`frontend/src/components/super-admin-panel.tsx`** — "AI Sozlamalar" tab'iga
  3 agent × (primary, fallback) dropdown bo'limi. `AiDefaultsForm` ga `agent_models`.
- **`frontend/src/app/api/super-admin/ai-defaults/route.ts`** — yangi maydonlarni qabul qilish.
- **`frontend/src/components/settings-panel.tsx`** — webhook/checker tab'iga kompaniya
  admin uchun per-agent override bo'limi (bo'sh qoldirilsa super admin defaulti meros).
- **`frontend/src/lib/types.ts`** — `GlobalAiDefaults` va checker settings view tiplari.
- `modelOptions()` ro'yxatini yagona joyda saqlash (masalan `gemini-2.5-pro`,
  `gemini-2.5-flash`, `gemini-2.0-flash`).

#### Default tier (super admin global default qiymatlari)
Agent1=`gemini-2.5-flash`, Agent2=`gemini-2.5-pro`, Agent3=`gemini-2.5-flash`,
fallback hammasi `gemini-2.5-flash`. Bu Flash-tiering optimizatsiyasini sozlama
orqali beradi (kodda hardcode emas).

---

## FAZA 2

### 2A. Explicit context caching
- **`utils/ai/gemini_helper.py`** — `create_cache(content, ttl)` (`client.caches.create`)
  va `analyze(..., cached_content=<name>)` qo'llab-quvvatlash
  (`GenerateContentConfig(cached_content=...)`).
- **`services/checkers/tzpr_agent_runner.py`** — `_run_agent2` da kod blokidan bir
  marta cache yaratiladi, barcha per-requirement va extra-scan call'lar shu cache'ga
  murojaat qiladi; oxirida qisqa TTL bilan o'zi tugaydi yoki o'chiriladi.

### 2B. Requirement batching
- **`services/checkers/tzpr_agents/agent2.py`** — `build_batch_prompt(requirements_batch, ...)`
  + array response schema + `validate_agent2_batch_json`.
- **`services/checkers/tzpr_agent_runner.py`** — `_run_agent2_per_requirement` requirement'larni
  ~6 talik batch'ga bo'ladi (call soni N → N/6), parallellik batch darajasida.
- **`config/app_settings.py`** — `agent2_batch_size` sozlamasi (default 6).

### 2C. Diff tozalash
- **`services/checkers/tz_pr_checker.py` → `_build_code_changes_section` (1292)** —
  `package-lock.json`, generated/vendored/`.min.*`/build artefaktlarni AI'ga
  yuborishdan oldin filtrlash (yangi `excluded_file_patterns` sozlamasi).

### 2D. Parallel rate-limit / key-freeze tuzatish
- `_call_agent2_single_raw_isolated` har call'da yangi `GeminiHelper` yaratadi →
  `last_request_time=0` → rate-limit ishlamaydi, parallel worker'lar bir vaqtda
  Gemini'ga uriladi (429 → key freeze xavfi). Va freeze holati worker'lar orasida
  ulashilmaydi.
- Yechim: Agent2 parallel worker'lar uchun **ulashilgan rate-limiter + freeze state**
  (umumiy lock/holat obyekti `GeminiHelper` ga uzatiladi).

---

## Kritik fayllar

| Fayl | Faza | O'zgarish |
|---|---|---|
| `services/checkers/tzpr_agents/agent2.py` | 1A, 2B | Prompt tartibi; batch prompt |
| `config/app_settings.py` | 1B, 2B, 2C | Per-agent model maydonlari; global override; batch/filter sozlamalari |
| `utils/ai/gemini_helper.py` | 1B, 2A, 2D | `fallback_model_name`; caching; ulashilgan rate-limit |
| `services/checkers/tzpr_constants.py` | 1B | `resolve_agent_models` helper |
| `services/checkers/tzpr_orchestrator.py` | 1B | `_model_for_agent` |
| `services/checkers/tzpr_agent_runner.py` | 1B, 2A, 2B, 2D | Per-agent model; caching; batching; rate-limit |
| `services/api/settings_api.py` | 1B | Checker settings API maydonlari |
| `services/api/internal_rpc_api.py`, `utils/auth/auth_db.py` | 1B | Super admin global model kalitlari |
| `services/checkers/tz_pr_checker.py` | 2C | `_build_code_changes_section` filtri |
| `frontend/src/components/super-admin-panel.tsx` | 1B | Per-agent model UI (default) |
| `frontend/src/components/settings-panel.tsx` | 1B | Per-agent model UI (kompaniya override) |
| `frontend/src/app/api/super-admin/ai-defaults/route.ts` | 1B | API route |
| `frontend/src/lib/types.ts` | 1B | Tip ta'riflari |

**Qayta ishlatiladigan mavjud mexanizmlar:** `_apply_global_queue_overrides`
(super admin override namunasi), `_merge()` + `dc_replace` (kompaniya/user override),
`*_help` field pattern, `get_global_setting`/`set_global_setting`, `AGENT_SEQUENCE`,
`BaseSelectField` (frontend dropdown).

---

## Tekshirish (verification)

1. **Mavjud testlar:** `pytest tests/test_full_system.py` — 106 test yashil qolishi shart.
2. **Settings ierarxiyasi:** super admin global model o'rnatadi → yangi kompaniya
   uni meros qiladi → kompaniya o'zgartiradi → faqat o'sha kompaniyaga ta'sir
   qilishini tekshirish (boshqa tenant tegmasligi — SaaS izolyatsiya).
3. **Multi-agent run:** `scripts/debug_tzpr_input_context.py` yoki real task webhook
   bilan checker run ishga tushirib, har agent log'ida to'g'ri model nomini ko'rish.
4. **Caching isboti:** `gemini_helper.py` da javob `usage_metadata.cached_content_token_count`
   ni log qilish — Agent2'ning 2-chi call'idan boshlab cached token > 0 bo'lishi kerak.
5. **Narx o'lchovi:** bitta o'rtacha task uchun jami input/output token log'larini
   optimizatsiyadan oldin/keyin solishtirib, ~3-5× (Faza 1) kamayganini tasdiqlash.
6. **Frontend:** dev server'da super admin va kompaniya admin sifatida kirib,
   per-agent dropdown'lar saqlanishi va meros mantig'i (bo'sh = inherit) ishlashini
   brauzerda tekshirish.

---

## E'tibor talab qiladigan joylar

- `tz_pr_checker` (UI/user) va `webhook_tz_pr` (kompaniya webhook) bir xil
  `TZPRCheckerSettings` dataclass — yangi maydonlar ikkalasiga ham tegishli.
- `_merge()` bo'sh string'li model qiymatini override deb qabul qilmasligi shart
  (bo'sh = meros). Kerak bo'lsa `_merge` ga bo'sh-string filtri qo'shiladi.
- Faza 2A explicit caching: parallel Agent2 worker'lar bitta cache nomini ulashishi
  kerak — cache bir marta yaratilib, worker'larga uzatiladi.
- Migratsiya talab qilinmaydi: `global_settings` (key/value) va `webhook_module_settings`
  (JSON) yangi kalitlarni sxema o'zgarishisiz qabul qiladi.