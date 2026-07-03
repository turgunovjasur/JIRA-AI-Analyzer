# Eval harness — multi-agent checker golden testlari

Prompt yoki model o'zgarishi mijoz JIRA commentigacha yetib boradigan natija
sifatini **jimgina** buzmasligi uchun offline, deterministik regression to'plami.

## Nima tekshiriladi

Har bir golden case REAL pipeline kodi orqali replay qilinadi:

```
gemini_responses.json (yozib olingan javoblar)
  → AgentRunnerMixin._run_agent1 / _run_agent1b_merge / _run_agent2 / _run_agent3
  → parse_gemini_json (markaziy JSON gateway)
  → validate_agent1_json / validate_agent2_json / validate_agent3_json
  → build_quality_artifact (deterministik verdict/matrix)
  → calculate_compliance_score_from_agent3 + build_final_analysis_text
  → expected.json bilan solishtirish
```

Fake qilinadigan narsa faqat ikkita:
- **Gemini chaqiruvi** — `FakeGemini` yozib olingan javobni qaytaradi (tarmoq yo'q);
- **run-state persistence** — `_start_agent/_finish_agent/_event/...` no-op (DB yo'q).

Qolgan hamma narsa production kodi: JSON parse/repair, kontrakt validatsiya,
merge/reconcile, skip/technical/extra logika, score va final matn.

## Ishga tushirish

```bash
.venv/bin/python eval/run_eval.py                 # hamma case, exit 1 = FAIL
.venv/bin/python eval/run_eval.py --case case_01_fail_verdict

# pytest orqali (DB kerak emas, no_db marker):
.venv/bin/python -m pytest tests/test_eval_golden.py -q
```

## Case tuzilmasi

```
eval/golden/case_NN_nomi/
├── tz.md                  # JIRA description (TZ) — agent1 inputi
├── pr_diff.txt            # PR diff — agent2 code context (8000 belgidan KICHIK bo'lsin,
│                          #   aks holda explicit-cache yo'li ochiladi)
├── meta.json              # ixtiyoriy: task_key, summary, dev_comments,
│                          #   agent2_extra_scan_enabled, is_recheck, return_reason
├── gemini_responses.json  # agent qadamlari bo'yicha yozib olingan javoblar
└── expected.json          # kutilgan yakuniy natija
```

`gemini_responses.json` kalitlari:

| Kalit | Qadam |
|---|---|
| `agent1` | Scope builder (requirement inventory) |
| `agent1b` | Merge specialist (faqat >=2 requirement bo'lsa chaqiriladi) |
| `agent2.REQ-N` | Har bir effective requirement uchun single verify chaqiruvi |
| `agent2.extra_scan` | Extra-scope scan (meta'da o'chirilmagan bo'lsa) |
| `agent3` | Arbiter (summary/risks/recommendation/skipped) |

Qiymat JSON obyekt bo'lsa stringga aylantirib beriladi; string bo'lsa AYNAN
shu raw matn beriladi (masalan markdown fence bilan — parse/repair yo'lini
tekshirish uchun, `case_01` dagi `agent1` shunday). Format kontrakti:
`docs/MULTI_AGENT_JSON_CONTRACT.md`.

Qat'iy qoidalar:
- run davomida ISHLATILMAGAN kalit qolsa case FAIL bo'ladi (eskirgan golden fayl);
- kerakli kalit YO'Q bo'lsa pipeline yiqiladi va case FAIL bo'ladi.

`expected.json` maydonlari: `verdict`, `run_state`, `compliance_score`
(`null` = manual review), `completed/failed/skipped/technical` ro'yxatlari,
`extra_code_risk`, `requirement_statuses` (REQ id → status) va ixtiyoriy
`analysis_text_contains` (final analiz matnida bo'lishi shart bo'lgan bo'laklar).

## Mavjud caselar

| Case | Nimani qotiradi |
|---|---|
| `case_01_fail_verdict` | Agent1B merge (4→3), fenced-JSON cleanup, 1 failed → verdict `fail`, score 67 |
| `case_02_all_skipped_none_score` | Dev izohi bilan HAMMA talab skip → score `None` (N/A, manual review) |
| `case_03_skip_extra_manual_review` | Recheck-kontekst (dev izohi) bilan qisman skip + medium extra risk → score 100 lekin `manual_review` |

## Yangi case qo'shish

1. `eval/golden/case_NN_qisqa_nom/` papka oching, yuqoridagi fayllarni yozing.
2. TZni o'zbekcha, 3–5 talabli, realistik qiling; diffni kichik tuting.
3. `gemini_responses.json` ni kontraktga mos yozing (validate_* funksiyalari
   qabul qiladigan shakl — kontrakt hujjatiga qarang).
4. `expected.json` da avval taxminingizni yozing, keyin
   `.venv/bin/python eval/run_eval.py --case case_NN_...` chiqargan
   "actual (to'liq)" blokini ko'rib to'g'rilang — lekin actual'ni KO'R-KO'RONA
   ko'chirmang: har maydon haqiqatan kutilgan xulosami, tekshirib chiqing.

## Real Gemini javoblarini yozib olish (`--record` g'oyasi)

Hozircha implement qilinmagan (`--record` flag xato bilan chiqadi). G'oya:

1. `EvalExecutor` dagi fake seamlar o'rniga real `GeminiHelper` ishlatiladi;
2. har `analyze()` chaqiruvi (agent kaliti bilan) natijasi
   `gemini_responses.json` ga yoziladi (agent2 uchun `agent2.REQ-N` kalitida);
3. run tugagach `expected.json` skeleti actual natijadan generatsiya qilinadi
   va odam qo'lda tasdiqlaydi.

Qo'lda yozib olish esa bugun ham mumkin: real run snapshotidagi agent
artifactlari (`checker_agent_runs.artifact_json` → `raw_model_excerpt`,
`calls[].attempts[]`) dan javoblarni ko'chirib olish.

## Siyosat (majburiy)

- **Har qanday prompt matni o'zgarishi** tegishli modul(lar)dagi
  `PROMPT_VERSION` ni bump qilishi SHART (format: `YYYY.MM.DD-N`).
  Modullar: `services/checkers/tzpr_agents/agent{1,1b,2,3}.py`,
  `services/generators/testcase_agents/agent2_testcase.py`,
  `agent3_testcase_auditor.py`. Markaziy ro'yxat: `core/prompt_registry.py`.
- O'zgarishdan keyin `eval/run_eval.py` va `tests/test_eval_golden.py`
  yashil bo'lishi SHART. Golden natija o'zgargan bo'lsa — bu ongli qaror
  bo'lishi va expected.json diff sifatida reviewda ko'rinishi kerak.
- Versiyalar har run yaratilishida DB ga yoziladi:
  `checker_runs.request_payload_json` / `analysis_runs.request_payload_json`
  ichida `prompt_versions` kaliti — natija regressiyasini qaysi prompt
  versiyasi berganini keyin ham aniqlash mumkin.
