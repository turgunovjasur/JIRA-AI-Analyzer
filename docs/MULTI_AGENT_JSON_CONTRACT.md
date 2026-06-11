# Multi-Agent JSON Contract

Status: current runtime contract

This document defines the compact JSON exchange format between the Checker and Agent1, Agent2, and Agent3.

## Gemini JSON Gateway

Every Gemini response passes through the same local JSON gateway before any agent-specific validation:

```text
raw Gemini response
-> parse_gemini_json(raw)
-> validate_agent1_json / validate_agent2_json / validate_agent3_json
```

`parse_gemini_json(raw)` only parses and repairs JSON syntax. It may strip markdown fences, extract a JSON object from surrounding text, remove common trailing commas, and balance a truncated quote/brace tail. It does not create requirements, statuses, evidence, verdicts, or any domain meaning.

Gateway metadata includes `ok`, `raw_length`, `used_cleanup`, `used_repair`, `repair_type`, `error`, and `warnings`.

## Checker Input

```json
{
  "task_key": "DEV-8358",
  "output_profile": "ui",
  "show_full_diff": true,
  "use_smart_patch": null,
  "max_files": null,
  "execution_mode": "multi_agent"
}
```

## Checker To Agent1

```json
{
  "tz": "Jira description / TZ matni",
  "comments": [
    "Trusted comment matni"
  ],
  "figma": [
    "Figma text/comment matni"
  ]
}
```

Rules:

- `tz` is always present.
- `comments` is always present and may be empty.
- `figma` is always present and may be empty.
- Checker applies settings and filtering before sending `comments` and `figma`.

## Agent1 To Checker

```json
{
  "requirements": [
    {
      "id": "REQ-1",
      "text": "Default 'N' qaytishi kerak.",
      "source": "tz"
    },
    {
      "id": "REQ-2",
      "text": "Setting UI'ga chiqmasligi kerak.",
      "source": "tz"
    }
  ]
}
```

Rules:

- `id` must be stable within the response: `REQ-1`, `REQ-2`, ...
- `text` is the atomic requirement.
- `source` values: `tz`, `comment`, `figma`, `mixed`.
- Backend validates and may renumber duplicate or missing ids.
- `validate_agent1_json` rejects missing/empty requirement inventory, skips invalid empty-text items, normalizes source, deduplicates requirements, and always returns stable `REQ-N` ids.

## Checker To Agent2

Checker calls Agent2 once per effective requirement. After requirement verification is complete, Checker makes one separate extra-scope scan call.

```json
{
  "requirements": [
    {
      "id": "REQ-1",
      "text": "Default 'N' qaytishi kerak.",
      "source": "tz"
    }
  ],
  "code": "FILE: path/to/file\nSTATUS: modified\nPATCH:\n@@ ...\n+..."
}
```

Rules:

- `requirements` comes from Agent1 output after backend normalization.
- `code` is a string containing file-by-file PR diff/code changes.

## Agent2 To Checker

```json
{
  "id": "REQ-1",
  "status": "completed",
  "evidence": "Kodda Mph_Pref.Expeditor_Room_Sync qiymat yo'q bo'lsa Nvl(..., 'N') orqali 'N' qaytarishi topildi."
}
```

Rules:

- `id` must match an Agent1 requirement id.
- `status` values: `completed`, `failed`.
- If `status = completed`, `evidence` must describe the concrete code evidence found.
- If `status = failed`, `evidence` must describe what is missing or which evidence was not found.
- `extra` is not returned in this call; extra scope uses its own call below.

Checker note:

- Checker retries an empty or invalid Agent2 JSON response for that requirement.
- Per-requirement calls may run in parallel, limited by effective setting `agent2_parallelism` (default `5`).
- After all per-requirement checks, checker performs one extra-scope Agent2 call that returns only `extra`.
- `validate_agent2_json` requires a single object whose `id` exactly matches the expected requirement id, `status` is `completed` or `failed`, and `evidence` is non-empty.
- If retry also fails, checker records the requirement in internal top-level `technical_failures`.
- The Agent2 verification item format still stays unchanged: `id`, `status`, `evidence`.
- Backend final matrix treats `technical_failures` as `manual_review`, not as real business failure.

Extra-scope call output:

```json
{
  "extra": [
    {
      "text": "TZ talablarida yo'q Room_Robots fallback logikasi qo'shilgan.",
      "risk": "medium"
    }
  ]
}
```

## Checker To Agent3

```json
{
  "requirements": [
    {
      "id": "REQ-1",
      "text": "Default 'N' qaytishi kerak.",
      "source": "tz"
    }
  ],
  "verifications": [
    {
      "id": "REQ-1",
      "status": "completed",
      "evidence": "Kodda default 'N' qaytarilishi implement qilingan."
    }
  ],
  "extra": [
    {
      "text": "TZda yo'q Mdeal_Headers draft returns logikasi qo'shilgan.",
      "risk": "medium"
    }
  ]
}
```

## Agent3 To Checker

```json
{
  "summary": "REQ-1 bajarilgan. Talablardan tashqari Mdeal_Headers draft returns logikasi qo'shilgan; risk medium, manual review kerak.",
  "risks": [
    "Extra code risk medium."
  ],
  "recommendation": "Manual review kerak."
}
```

Rules:

- Agent3 returns only `summary`, `risks`, and `recommendation`.
- Agent3 must mention `extra` items in the summary when they exist.
- Agent3 does not return verdict, score, completed, failed, missing, or invalid lists.
- `validate_agent3_json` requires non-empty `summary` and `recommendation`; missing `risks` is normalized to `[]`.
- Checker/backend computes verdict, score, status lists, missing verifications, invalid verifications, and requirement matrix deterministically.

## Checker Final Output

Checker/backend computes and returns the final result. Example:

```json
{
  "task_key": "DEV-8358",
  "verdict": "manual_review",
  "compliance_score": 100,
  "summary": "REQ-1 bajarilgan. Talablardan tashqari Mdeal_Headers draft returns logikasi qo'shilgan; risk medium, manual review kerak.",
  "completed": ["REQ-1"],
  "failed": [],
  "technical": [],
  "missing": [],
  "invalid": [],
  "verifications": [
    {
      "id": "REQ-1",
      "status": "completed",
      "evidence": "Kodda default 'N' qaytarilishi implement qilingan."
    }
  ],
  "extra": [
    {
      "text": "TZda yo'q Mdeal_Headers draft returns logikasi qo'shilgan.",
      "risk": "medium"
    }
  ],
  "requirements": [
    {
      "id": "REQ-1",
      "text": "Default 'N' qaytishi kerak.",
      "source": "tz",
      "status": "completed",
      "evidence": "Kodda default 'N' qaytarilishi implement qilingan."
    }
  ]
}
```

Backend guardrails:

- Agent1: validate `requirements`, fill or renumber ids, reject empty text, normalize `source`.
- Agent2: require one verification per requirement id, retry empty/invalid per-requirement JSON before recording technical failure, reject unknown ids, normalize invalid status to failed or mark invalid.
- Agent2: require non-empty `evidence`; normalize malformed `extra` items.
- Agent3: treat `summary` as human-readable text only, not as the source of verdict.
- Checker: compute verdict and score deterministically from normalized requirements, verifications, technical failures, and extra items.
