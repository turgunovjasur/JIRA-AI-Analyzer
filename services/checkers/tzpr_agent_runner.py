from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from time import perf_counter
from typing import Any

from core.logger import get_logger
from services.checkers.tzpr_constants import PRO_MODEL_NAME
from services.checkers.tzpr_agents import agent1 as agent1_contract
from services.checkers.tzpr_agents import agent1b as agent1b_contract
from services.checkers.tzpr_agents import agent2 as agent2_contract
from services.checkers.tzpr_agents import agent3 as agent3_contract
from utils.ai.gemini_json import parse_gemini_json as _parse_gemini_json
from services.checkers.tzpr_helpers import summarize as _summarize
from services.checkers.tzpr_preflight import (
    agent1_rules_from_effective_settings as _agent1_rules_from_effective_settings,
    build_agent1_sanitized_input as _build_agent1_sanitized_input,
)
from utils.ai.gemini_helper import GeminiHelper

log = get_logger("checker.multi_agent")


def _iter_attempts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for item in items or []:
        nested = item.get("attempts") if isinstance(item, dict) else None
        if isinstance(nested, list):
            attempts.extend(attempt for attempt in nested if isinstance(attempt, dict))
        elif isinstance(item, dict):
            attempts.append(item)
    return attempts


def _count_attempt_flag(items: list[dict[str, Any]], flag: str) -> int:
    return sum(1 for item in _iter_attempts(items) if bool(item.get(flag)))


def _count_attempt_error(items: list[dict[str, Any]], marker: str) -> int:
    return sum(
        1
        for item in _iter_attempts(items)
        if marker in str(item.get("error") or "")
    )


def _count_attempt_warning(items: list[dict[str, Any]], warning: str) -> int:
    return sum(
        1
        for item in _iter_attempts(items)
        if warning in [str(value) for value in list(item.get("warnings") or [])]
    )


def _sum_attempt_int(items: list[dict[str, Any]], key: str) -> int:
    total = 0
    for item in _iter_attempts(items):
        try:
            total += int(item.get(key) or 0)
        except (TypeError, ValueError):
            continue
    return total


def _token_metrics(usage: dict[str, Any] | None) -> dict[str, int]:
    source = usage or {}
    metrics: dict[str, int] = {}
    for key in (
        "cached_content_token_count",
        "prompt_token_count",
        "candidates_token_count",
        "total_token_count",
    ):
        try:
            metrics[key] = int(source.get(key) or 0)
        except (AttributeError, TypeError, ValueError):
            metrics[key] = 0
    return metrics


def _chunk_items(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    chunk_size = max(1, int(size or 1))
    return [items[index:index + chunk_size] for index in range(0, len(items), chunk_size)]


def _is_agent2_model_unavailable_error(error: Any) -> bool:
    text = str(error or "").lower()
    if not text:
        return False
    return "model_unavailable" in text or "ham ishlamadi" in text


def _is_agent2_model_unavailable_result(result: dict[str, Any] | None) -> bool:
    if not isinstance(result, dict):
        return False
    call_records = result.get("call_records") or []
    if not any(str(item.get("state") or "") == "technical_failure" for item in call_records if isinstance(item, dict)):
        return False
    for item in call_records:
        if isinstance(item, dict) and str(item.get("failure_reason") or "") == "model_unavailable":
            return True
    for item in result.get("technical_failures") or []:
        if isinstance(item, dict) and (
            str(item.get("failure_reason") or "") == "model_unavailable"
            or _is_agent2_model_unavailable_error(item.get("error"))
        ):
            return True
    return False


class AgentRunnerMixin:
    def _run_agent1(self, context: dict[str, Any]) -> dict[str, Any]:
        agent_key = "agent1_scope_builder"
        self._start_agent(agent_key, "TZ, comment va Figma asosida requirement inventory ajratilmoqda")
        agent1_rules = _agent1_rules_from_effective_settings(context.get("effective_settings") or {})
        agent1_input = context.get("agent1_input") or _build_agent1_sanitized_input(
            task_details=context["task_details"],
            trusted_authors=[],
            figma_data=None,
            read_comments_enabled=False,
            max_comments_to_read=0,
            rules=agent1_rules,
        )
        prompt = agent1_contract.build_prompt(
            agent1_input=agent1_input,
        )

        raw = ""
        parse_mode = "not_parsed"
        parse_metadata: dict[str, Any] = {}
        warnings: list[str] = []
        agent1_contract_output: dict[str, Any] = {
            "requirements": [],
            "warnings": [],
        }
        try:
            raw = self._model_for_agent(agent_key).analyze(
                prompt,
                max_output_tokens=16384,
                generation_config_overrides={
                    "response_mime_type": "application/json",
                    "response_schema": agent1_contract.RESPONSE_SCHEMA,
                },
            )
            parse_result = _parse_gemini_json(raw)
            parse_metadata = {
                "ok": parse_result.ok,
                "raw_length": parse_result.raw_length,
                "used_cleanup": parse_result.used_cleanup,
                "used_repair": parse_result.used_repair,
                "repair_type": parse_result.repair_type,
                "error": parse_result.error,
                "warnings": parse_result.warnings,
            }
            if not parse_result.ok:
                raise ValueError(parse_result.error or "Agent1 JSON parse failed")
            if parse_result.used_cleanup or parse_result.used_repair:
                warnings.append("Agent1 JSON cleanup/repair ishlatildi.")
            validation = agent1_contract.validate_agent1_json(
                parse_result.data,
                task_summary=str(context["task_details"].get("summary") or "").strip(),
                description=str(context["task_details"].get("description") or ""),
                rules=agent1_rules,
            )
            warnings.extend(str(item).strip() for item in (validation.get("warnings") or []) if str(item).strip())
            if not validation.get("ok"):
                raise ValueError(str(validation.get("error") or "Requirement inventory invalid"))
            agent1_contract_output = validation["data"]
            requirements = list(validation.get("requirements") or [])
            parse_mode = "recovered_json" if (parse_result.used_cleanup or parse_result.used_repair) else "model_json"
            summary = str((parse_result.data or {}).get("summary") if isinstance(parse_result.data, dict) else "").strip()
        except Exception as exc:
            recovered = agent1_contract.recover_incomplete_response(raw)

            if recovered:
                agent1_contract_output = agent1_contract.normalize_contract_output(recovered)
                requirements = agent1_contract.refine_requirements(
                    requirements=agent1_contract_output["requirements"],
                    task_summary=str(context["task_details"].get("summary") or "").strip(),
                    description=str(context["task_details"].get("description") or ""),
                    rules=agent1_rules,
                )
                if requirements:
                    if parse_mode == "not_parsed":
                        parse_mode = "recovered_json"
                    if not any("JSON" in w for w in warnings):
                        warnings.append(f"Agent1 structured JSON parse yiqildi, qisman recover ishlatildi: {exc}")
                    warnings.extend(
                        str(item).strip()
                        for item in (recovered.get("warnings") or [])
                        if str(item).strip()
                    )
                    warnings = list(dict.fromkeys(warnings))
                    summary = (
                        str(recovered.get("summary") or "").strip()
                        or "AI raw outputdan requirementlar qisman recover qilindi."
                    )
                else:
                    recovered = None

            if not recovered:
                log.warning(f"[{self.task_key}] Agent1 fallback ishladi: {exc}")
                warnings.append(f"Agent1 output parse bo'lmadi: {exc}")
                requirements = []
                summary = ""

            if not requirements:
                self._finish_agent(
                    agent_key,
                    state="failed",
                    error_text="Requirement inventory qurilmadi",
                    output_summary="Agent1 requirement topa olmadi",
                    warnings=warnings,
                    artifact={"raw_excerpt": _summarize(raw if raw else "", 320)},
                )
                return {"success": False, "error": "Requirement inventory qurilmadi"}

        validated_requirements, validation_warnings = agent1_contract.validate_output(requirements)
        warnings.extend(agent1_contract.user_facing_validation_warnings(validation_warnings))
        raw_requirements = agent1_contract.public_requirement_items(validated_requirements)

        merged_requirements, merge_warnings = self._run_agent1b_merge(raw_requirements)
        warnings.extend(merge_warnings)

        agent1_contract_output["requirements"] = merged_requirements
        agent1_contract_output["warnings"] = list(dict.fromkeys([*agent1_contract_output.get("warnings", []), *warnings]))

        merged_count = sum(1 for item in merged_requirements if item.get("merged_from"))
        artifact = {
            "summary": summary,
            "requirements": merged_requirements,
            "raw_requirements": raw_requirements,
            "warnings": agent1_contract_output["warnings"],
            "parse_mode": parse_mode,
            "parse_metadata": parse_metadata,
            "raw_model_excerpt": _summarize(raw, 1200),
        }
        self._finish_agent(
            agent_key,
            state="completed",
            input_summary=(
                f"tz: {len(str(agent1_input.get('tz') or ''))} belgi. "
                f"comments: {len(agent1_input.get('comments') or [])} ta. "
                f"figma: {len(agent1_input.get('figma') or [])} ta."
            ),
            output_summary=(
                f"{len(raw_requirements)} ta requirement ajratildi, "
                f"{len(merged_requirements)} taga birlashtirildi ({merged_count} ta merge)."
            ),
            warnings=warnings,
            artifact=artifact,
        )
        return {
            "success": True,
            "summary": summary,
            "requirements": merged_requirements,
            "effective_requirements": list(merged_requirements),
            "raw_requirements": raw_requirements,
            "warnings": warnings,
            "parse_mode": parse_mode,
        }

    def _run_agent1b_merge(
        self,
        raw_requirements: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        if len(raw_requirements) < 2:
            return list(raw_requirements), []

        prompt = agent1b_contract.build_prompt(requirements=raw_requirements)
        try:
            raw = self._model_for_agent("agent1b_merger").analyze(
                prompt,
                max_output_tokens=8192,
                generation_config_overrides={
                    "response_mime_type": "application/json",
                    "response_schema": agent1b_contract.RESPONSE_SCHEMA,
                },
            )
            parse_result = _parse_gemini_json(raw)
            if not parse_result.ok:
                raise ValueError(parse_result.error or "Agent1B JSON parse failed")
            validation = agent1b_contract.validate_merged_json(parse_result.data)
            if not validation.get("ok"):
                raise ValueError(str(validation.get("error") or "Agent1B output invalid"))
            merged, warnings = agent1b_contract.reconcile_merged(
                raw_requirements=raw_requirements,
                merged_groups=validation["groups"],
            )
        except Exception as exc:
            log.warning(f"[{self.task_key}] Agent1B merge yiqildi, asl ro'yxat ishlatildi: {exc}")
            self._event(
                "warning",
                "agent1b_merge_failed",
                f"Agent1B merge ishlamadi, asl requirement ro'yxati saqlandi: {exc}",
                agent_key="agent1_scope_builder",
            )
            return list(raw_requirements), [f"Agent1B merge ishlamadi: {exc}"]

        merged_count = sum(1 for item in merged if item.get("merged_from"))
        self._event(
            "info",
            "agent1b_merge",
            f"Agent1B {len(raw_requirements)} ta requirementni {len(merged)} taga birlashtirdi ({merged_count} ta merge).",
            agent_key="agent1_scope_builder",
            meta={"raw_count": len(raw_requirements), "merged_count": len(merged), "merge_groups": merged_count},
        )
        return merged, warnings

    def _run_agent2(self, context: dict[str, Any], agent1: dict[str, Any]) -> dict[str, Any]:
        agent_key = "agent2_verifier"
        self._start_agent(agent_key, "Requirementlar kod va PR diff bo'yicha tekshirilmoqda")
        effective_requirements = list(agent1.get("effective_requirements") or [])
        if not effective_requirements:
            self._finish_agent(
                agent_key,
                state="blocked",
                error_text="Tekshiriladigan requirement yo'q",
                output_summary="Requirement inventory effective item bermadi",
                artifact={"verifications": []},
            )
            return {
                "success": False,
                "summary": "Effective requirement yo'q.",
                "verifications": [],
                "warnings": ["Verifier uchun effective requirement topilmadi."],
            }

        code_changes = self.service._build_code_changes_section(
            context["pr_info"],
            max_files=None,
            show_full_diff=True,
            use_smart_patch=context["effective_use_smart_patch"],
        )
        return self._run_agent2_per_requirement(
            agent_key=agent_key,
            context=context,
            effective_requirements=effective_requirements,
            code_changes=code_changes,
        )

    def _run_agent2_per_requirement(
        self,
        *,
        agent_key: str,
        context: dict[str, Any],
        effective_requirements: list[dict[str, Any]],
        code_changes: str,
    ) -> dict[str, Any]:
        verifications: list[dict[str, Any]] = []
        warnings: list[str] = []
        call_records: list[dict[str, Any]] = []
        technical_failures: list[dict[str, Any]] = []
        extra_items: list[dict[str, Any]] = []
        extra_scan: dict[str, Any] = {
            "state": "not_started",
            "attempt_count": 0,
            "attempts": [],
        }
        schema_validation_failures = 0
        model_call_count = 0
        retry_count = 0
        max_attempts = 2
        started_total = perf_counter()
        effective_settings = context.get("effective_settings") or {}
        try:
            parallelism = int(effective_settings.get("agent2_parallelism") or 5)
        except (TypeError, ValueError):
            parallelism = 5
        try:
            batch_size = int(effective_settings.get("agent2_batch_size") or 6)
        except (TypeError, ValueError):
            batch_size = 6
        batch_size = max(1, min(20, batch_size))
        parallelism = max(1, min(16, parallelism, max(len(effective_requirements), 1)))
        api_keys = list((self.service._get_creds() or {}).get("gemini_keys") or [])
        agent2_shared_state: dict[str, Any] = {}
        cache_name = ""
        fallback_cache_name = ""
        cache_enabled = False
        cache_error = ""
        prompt_code_changes = code_changes
        if len(code_changes or "") >= 8000:
            try:
                cache_content = agent2_contract.build_cached_code_context(
                    pr_info=context["pr_info"],
                    code_changes=code_changes,
                )
                primary_model, fallback_model = self._model_names_for_agent(agent_key)
                cache_helper = self._model_for_agent(agent_key)
                cache_name = cache_helper.create_cache(
                    cache_content,
                    ttl_seconds=600,
                    display_name=f"tzpr-agent2-{self.run_id[:24]}-{primary_model}",
                )
                if fallback_model and fallback_model != primary_model:
                    try:
                        fallback_cache_name = cache_helper.create_cache(
                            cache_content,
                            ttl_seconds=600,
                            display_name=f"tzpr-agent2-{self.run_id[:24]}-{fallback_model}",
                            model_name=fallback_model,
                        )
                    except Exception as exc:
                        fallback_cache_name = ""
                        warnings.append(
                            "Agent2 fallback cache yaratilmadi, Pro cache fallback'siz ishlaydi: "
                            f"{str(exc).strip() or exc.__class__.__name__}"
                        )
                cache_enabled = bool(cache_name)
                if cache_enabled:
                    prompt_code_changes = "(PR SUMMARY va CODE CHANGES explicit Gemini cache orqali berilgan.)"
                    agent2_shared_state["last_request_time"] = float(
                        getattr(cache_helper, "last_request_time", 0.0) or 0.0
                    )
                    agent2_shared_state["request_count"] = int(
                        getattr(cache_helper, "request_count", 0) or 0
                    )
            except Exception as exc:
                cache_error = str(exc).strip() or exc.__class__.__name__
                warnings.append(f"Agent2 explicit cache yaratilmadi, oddiy prompt ishlatildi: {cache_error}")

        batches = _chunk_items(effective_requirements, batch_size)
        worker_results: list[dict[str, Any] | None] = [None] * len(batches)
        model_unavailable_breaker_threshold = 2
        model_unavailable_consecutive_failures = 0
        model_unavailable_breaker_open = False
        model_unavailable_breaker_reason = ""
        model_unavailable_skipped_batch_count = 0
        model_unavailable_skipped_requirement_count = 0

        def _req_ids_for_batch(batch: list[dict[str, Any]]) -> list[str]:
            return [
                str(item.get("id") or "").strip()
                for item in batch
                if str(item.get("id") or "").strip()
            ]

        def _run_batch(batch: list[dict[str, Any]]) -> dict[str, Any]:
            return self._run_agent2_requirement_batch(
                requirements=batch,
                context=context,
                code_changes=prompt_code_changes,
                api_keys=api_keys,
                max_attempts=max_attempts,
                cached_content=cache_name,
                fallback_cached_content=fallback_cache_name,
                shared_state=agent2_shared_state,
            )

        def _record_breaker_state(index: int, result: dict[str, Any] | None) -> None:
            nonlocal model_unavailable_consecutive_failures
            nonlocal model_unavailable_breaker_open
            nonlocal model_unavailable_breaker_reason
            if _is_agent2_model_unavailable_result(result):
                model_unavailable_consecutive_failures += 1
                if (
                    model_unavailable_consecutive_failures >= model_unavailable_breaker_threshold
                    and not model_unavailable_breaker_open
                ):
                    model_unavailable_breaker_open = True
                    model_unavailable_breaker_reason = (
                        f"Agent2 ketma-ket {model_unavailable_consecutive_failures} ta batchda "
                        "Pro+Flash model_unavailable oldi."
                    )
                    warning = (
                        f"{model_unavailable_breaker_reason} "
                        "Hali yuborilmagan batchlar modelga yuborilmaydi."
                    )
                    warnings.append(warning)
                    log.warning(f"[{self.task_key}] {warning} Batch index: {index}")
                return
            model_unavailable_consecutive_failures = 0

        def _skip_not_submitted_batches(start_index: int) -> None:
            nonlocal model_unavailable_skipped_batch_count
            nonlocal model_unavailable_skipped_requirement_count
            reason = model_unavailable_breaker_reason or "Agent2 model_unavailable circuit breaker ochildi."
            for skip_index in range(start_index, len(batches)):
                if worker_results[skip_index] is not None:
                    continue
                req_ids = _req_ids_for_batch(batches[skip_index])
                worker_results[skip_index] = self._agent2_model_unavailable_skipped_batch(req_ids, reason)
                model_unavailable_skipped_batch_count += 1
                model_unavailable_skipped_requirement_count += len(req_ids)

        if parallelism <= 1 or len(batches) <= 1:
            for index, batch in enumerate(batches):
                if model_unavailable_breaker_open:
                    _skip_not_submitted_batches(index)
                    break
                worker_results[index] = _run_batch(batch)
                _record_breaker_state(index, worker_results[index])
        else:
            with ThreadPoolExecutor(max_workers=parallelism) as executor:
                futures = {}
                next_batch_index = 0
                while next_batch_index < len(batches) and len(futures) < parallelism:
                    futures[executor.submit(_run_batch, batches[next_batch_index])] = next_batch_index
                    next_batch_index += 1

                while futures:
                    done, _pending = wait(set(futures), return_when=FIRST_COMPLETED)
                    for future in sorted(done, key=lambda item: futures[item]):
                        index = futures.pop(future)
                        try:
                            worker_results[index] = future.result()
                        except Exception as exc:
                            batch = batches[index]
                            req_ids = _req_ids_for_batch(batch)
                            error = str(exc).strip() or exc.__class__.__name__
                            log.warning(f"[{self.task_key}] Agent2 parallel batch worker failed ({req_ids}): {error}")
                            worker_results[index] = self._agent2_batch_unexpected_failure(req_ids, error)
                        _record_breaker_state(index, worker_results[index])

                    if model_unavailable_breaker_open and next_batch_index < len(batches):
                        _skip_not_submitted_batches(next_batch_index)
                        next_batch_index = len(batches)

                    while (
                        not model_unavailable_breaker_open
                        and next_batch_index < len(batches)
                        and len(futures) < parallelism
                    ):
                        futures[executor.submit(_run_batch, batches[next_batch_index])] = next_batch_index
                        next_batch_index += 1

        for result in worker_results:
            if not result:
                continue
            verifications.extend(result.get("verifications") or [])
            call_records.extend(result.get("call_records") or [])
            warnings.extend(result.get("warnings") or [])
            technical_failures.extend(result.get("technical_failures") or [])
            schema_validation_failures += int(result.get("schema_validation_failures") or 0)
            model_call_count += int(result.get("model_call_count") or 0)
            retry_count += int(result.get("retry_count") or 0)

        extra_scan_enabled = bool(effective_settings.get("agent2_extra_scan_enabled", True))
        extra_attempts: list[dict[str, Any]] = []
        extra_started = perf_counter()
        extra_last_error = ""
        if not extra_scan_enabled:
            extra_scan = {
                "state": "disabled",
                "latency_ms": 0,
                "attempt_count": 0,
                "attempts": [],
                "extra_count": 0,
            }
        elif model_unavailable_breaker_open:
            extra_last_error = model_unavailable_breaker_reason or "Agent2 model_unavailable circuit breaker ochildi."
            extra_scan = {
                "state": "technical_failure",
                "failure_reason": "model_unavailable",
                "skipped_due_to_circuit_breaker": True,
                "latency_ms": int((perf_counter() - extra_started) * 1000),
                "attempt_count": 0,
                "attempts": [],
                "error": f"model_unavailable: {extra_last_error}",
                "extra_count": 0,
            }
            warnings.append("Agent2 extra scan model_unavailable circuit breaker sabab skip qilindi.")
        else:
            extra_prompt = agent2_contract.build_extra_scan_prompt(
                requirements=effective_requirements,
                pr_info=context["pr_info"],
                code_changes=prompt_code_changes,
                verifications=verifications,
            )
            for attempt in range(1, max_attempts + 1):
                raw = ""
                extra_usage_metrics: dict[str, int] = {}
                attempt_started = perf_counter()
                model_call_count += 1
                if attempt > 1:
                    retry_count += 1
                try:
                    raw, extra_model_used, extra_usage_metrics = self._call_agent2_extra_scan_raw(
                        extra_prompt,
                        api_keys=api_keys,
                        cached_content=cache_name,
                        fallback_cached_content=fallback_cache_name,
                        shared_state=agent2_shared_state,
                    )
                    parse_result = _parse_gemini_json(raw)
                    if not parse_result.ok or not isinstance(parse_result.data, dict):
                        raise ValueError(parse_result.error or "Agent2 extra JSON parse failed")
                    extra_parsed = parse_result.data
                    extra_items = agent2_contract.normalize_extra(extra_parsed.get("extra") or [])
                    extra_attempts.append(
                        {
                            "attempt": attempt,
                            "state": "completed",
                            "latency_ms": int((perf_counter() - attempt_started) * 1000),
                            "model": extra_model_used,
                            "raw_length": len(raw or ""),
                            "used_cleanup": parse_result.used_cleanup,
                            "used_repair": parse_result.used_repair,
                            "repair_type": parse_result.repair_type,
                            "warnings": parse_result.warnings,
                            "extra_count": len(extra_items),
                            **extra_usage_metrics,
                        }
                    )
                    extra_scan = {
                        "state": "completed",
                        "latency_ms": int((perf_counter() - extra_started) * 1000),
                        "attempt_count": len(extra_attempts),
                        "attempts": extra_attempts,
                        "extra_count": len(extra_items),
                    }
                    break
                except Exception as exc:
                    schema_validation_failures += 1
                    extra_last_error = str(exc).strip() or exc.__class__.__name__
                    extra_attempts.append(
                        {
                            "attempt": attempt,
                            "state": "parse_failed",
                            "latency_ms": int((perf_counter() - attempt_started) * 1000),
                            "model": self._model_names_for_agent("agent2_verifier")[0],
                            "error": _summarize(extra_last_error, 320),
                            "raw_length": len(raw or ""),
                            "raw_excerpt": _summarize(raw if raw else "", 600),
                            **_token_metrics(extra_usage_metrics),
                        }
                    )

        if extra_scan.get("state") not in {"completed", "disabled"} and not extra_scan.get("skipped_due_to_circuit_breaker"):
            warnings.append(f"Agent2 extra scan ishlamadi: {extra_last_error or 'empty/invalid response'}")
            extra_scan = {
                "state": "technical_failure",
                "latency_ms": int((perf_counter() - extra_started) * 1000),
                "attempt_count": len(extra_attempts),
                "attempts": extra_attempts,
                "error": _summarize(extra_last_error or "empty/invalid response", 500),
                "extra_count": 0,
            }

        if extra_items:
            extra_items, dropped_extra = agent2_contract.filter_extra_against_requirements(
                extra_items=extra_items,
                requirements=effective_requirements,
                verifications=verifications,
            )
            if dropped_extra:
                warnings.append(
                    f"Agent2 extra scan: {len(dropped_extra)} ta item requirement bilan ust-ma-ust tushgani uchun olib tashlandi."
                )

        coverage = agent2_contract.verification_coverage(
            requirements=effective_requirements,
            verifications=verifications,
        )
        metrics = {
            "mode": "batch" if batch_size > 1 else "per_requirement",
            "code_context_chars": len(code_changes or ""),
            "requirement_count": len(effective_requirements),
            "agent2_batch_size": batch_size,
            "batch_count": len(batches),
            "model_unavailable_breaker_open": model_unavailable_breaker_open,
            "model_unavailable_breaker_threshold": model_unavailable_breaker_threshold,
            "model_unavailable_breaker_reason": model_unavailable_breaker_reason,
            "model_unavailable_skipped_batch_count": model_unavailable_skipped_batch_count,
            "model_unavailable_skipped_requirement_count": model_unavailable_skipped_requirement_count,
            "explicit_cache_enabled": cache_enabled,
            "explicit_cache_error": cache_error,
            "cached_content_token_count": (
                _sum_attempt_int(call_records, "cached_content_token_count")
                + _sum_attempt_int(extra_attempts, "cached_content_token_count")
            ),
            "prompt_token_count": (
                _sum_attempt_int(call_records, "prompt_token_count")
                + _sum_attempt_int(extra_attempts, "prompt_token_count")
            ),
            "candidates_token_count": (
                _sum_attempt_int(call_records, "candidates_token_count")
                + _sum_attempt_int(extra_attempts, "candidates_token_count")
            ),
            "total_token_count": (
                _sum_attempt_int(call_records, "total_token_count")
                + _sum_attempt_int(extra_attempts, "total_token_count")
            ),
            "parallelism": parallelism,
            "requirement_verification_count": len(call_records),
            "agent2_call_count": model_call_count,
            "retry_count": retry_count,
            "schema_validation_failures": schema_validation_failures,
            "technical_failure_count": len(technical_failures),
            "repair_success_count": _count_attempt_flag(call_records, "used_repair") + _count_attempt_flag(extra_attempts, "used_repair"),
            "cleanup_success_count": _count_attempt_flag(call_records, "used_cleanup") + _count_attempt_flag(extra_attempts, "used_cleanup"),
            "empty_response_count": _count_attempt_error(call_records, "empty_response") + _count_attempt_error(extra_attempts, "empty_response"),
            "weak_evidence_count": _count_attempt_warning(call_records, "weak_evidence"),
            "extra_count": len(extra_items),
            "extra_scan_state": str(extra_scan.get("state") or ""),
            "missing_verification_count": len(coverage["missing"]),
            "total_latency_ms": int((perf_counter() - started_total) * 1000),
            "per_requirement_latency_ms": [
                int(item.get("latency_ms") or 0)
                for item in call_records
            ],
        }
        state = "failed" if coverage["missing"] or coverage["invalid"] or technical_failures else "completed"
        output_summary = (
            f"{len(verifications)} ta requirement {len(batches)} ta batch orqali tekshirildi."
            if not coverage["missing"]
            else f"{len(verifications)} ta requirement {len(batches)} ta batch orqali tekshirildi, {len(coverage['missing'])} ta yetishmayapti."
        )
        result = {
            "success": not bool(coverage["missing"] or coverage["invalid"] or technical_failures),
            "summary": "",
            "verifications": verifications,
            "extra": extra_items,
            "technical_failures": technical_failures,
            "warnings": warnings,
            "checker_coverage": coverage,
            "retry_count": retry_count,
            "verification_mode": "batch" if batch_size > 1 else "per_requirement",
            "metrics": metrics,
        }
        try:
            self._finish_agent(
                agent_key,
                state=state,
                input_summary=(
                    f"Verifierga {len(effective_requirements)} ta requirement yuborildi. "
                    f"Code context: {len(code_changes or '')} belgi. Batch size: {batch_size}. Parallelism: {parallelism}."
                ),
                output_summary=output_summary,
                warnings=warnings,
                artifact={
                    "summary": "",
                    "verifications": verifications,
                    "extra": extra_items,
                    "technical_failures": technical_failures,
                    "checker_coverage": coverage,
                    "retry_count": retry_count,
                    "verification_mode": "batch" if batch_size > 1 else "per_requirement",
                    "metrics": metrics,
                    "calls": call_records,
                    "extra_scan": extra_scan,
                    "explicit_cache": {
                        "enabled": cache_enabled,
                        "error": cache_error,
                        "cache_name_present": bool(cache_name),
                        "fallback_cache_name_present": bool(fallback_cache_name),
                        "delete_on_finish": bool(cache_name),
                        "ttl_seconds": 600 if cache_name else 0,
                    },
                },
            )
            return result
        finally:
            for cache_to_delete in dict.fromkeys([cache_name, fallback_cache_name]):
                if cache_to_delete:
                    self._model_for_agent(agent_key).delete_cache(cache_to_delete)

    def _run_agent2_requirement_batch(
        self,
        *,
        requirements: list[dict[str, Any]],
        context: dict[str, Any],
        code_changes: str,
        api_keys: list[str],
        max_attempts: int,
        cached_content: str = "",
        fallback_cached_content: str = "",
        shared_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        req_ids = [
            str(requirement.get("id") or "").strip()
            for requirement in requirements
            if str(requirement.get("id") or "").strip()
        ]
        if len(requirements) <= 1:
            single = self._run_agent2_single_requirement(
                requirement=requirements[0],
                context=context,
                code_changes=code_changes,
                api_keys=api_keys,
                max_attempts=max_attempts,
                cached_content=cached_content,
                fallback_cached_content=fallback_cached_content,
                shared_state=shared_state,
            )
            return {
                "verifications": [single["verification"]],
                "technical_failures": single.get("technical_failures") or [],
                "warnings": single.get("warnings") or [],
                "call_records": [single["call_record"]],
                "schema_validation_failures": int(single.get("schema_validation_failures") or 0),
                "model_call_count": int(single.get("model_call_count") or 0),
                "retry_count": int(single.get("retry_count") or 0),
            }

        started = perf_counter()
        prompt = agent2_contract.build_batch_prompt(
            requirements=requirements,
            pr_info=context["pr_info"],
            code_changes=code_changes,
        )
        attempt_records: list[dict[str, Any]] = []
        parsed_by_id: dict[str, dict[str, Any]] = {}
        missing_ids: list[str] = list(req_ids)
        warnings: list[str] = []
        last_error = ""
        model_used, _fallback_model = self._model_names_for_agent("agent2_verifier")

        for attempt in range(1, max_attempts + 1):
            raw = ""
            usage_metrics: dict[str, int] = {}
            attempt_started = perf_counter()
            try:
                raw, model_used, usage_metrics = self._call_agent2_batch_raw_isolated(
                    prompt,
                    api_keys,
                    cached_content=cached_content,
                    fallback_cached_content=fallback_cached_content,
                    shared_state=shared_state,
                )
                parse_result = _parse_gemini_json(raw)
                if not parse_result.ok:
                    raise ValueError(parse_result.error or "Agent2 batch JSON parse failed")
                validation = agent2_contract.validate_agent2_batch_json(
                    parse_result.data,
                    expected_ids=req_ids,
                )
                if not validation.get("ok"):
                    raise ValueError(str(validation.get("error") or "Agent2 batch JSON validation failed"))
                parsed_items = list(validation.get("verifications") or [])
                for item in parsed_items:
                    item_id = str(item.get("id") or "").strip()
                    if item_id and item_id not in parsed_by_id:
                        parsed_by_id[item_id] = item
                missing_ids = [item_id for item_id in req_ids if item_id not in parsed_by_id]
                warnings.extend(str(item) for item in [*parse_result.warnings, *list(validation.get("warnings") or [])])
                attempt_records.append(
                    {
                        "attempt": attempt,
                        "state": "completed" if not missing_ids else "partial",
                        "latency_ms": int((perf_counter() - attempt_started) * 1000),
                        "model": model_used,
                        "raw_length": len(raw or ""),
                        "used_cleanup": parse_result.used_cleanup,
                        "used_repair": parse_result.used_repair,
                        "repair_type": parse_result.repair_type,
                        "warnings": [*parse_result.warnings, *list(validation.get("warnings") or [])],
                        "requirement_count": len(req_ids),
                        "verification_count": len(parsed_items),
                        "merged_verification_count": len(parsed_by_id),
                        "missing_ids": missing_ids,
                        **usage_metrics,
                    }
                )
                if not missing_ids:
                    break
            except Exception as exc:
                last_error = str(exc).strip() or exc.__class__.__name__
                attempt_records.append(
                    {
                        "attempt": attempt,
                        "state": "parse_failed",
                        "latency_ms": int((perf_counter() - attempt_started) * 1000),
                        "model": model_used,
                        "error": _summarize(last_error, 320),
                        "raw_length": len(raw or ""),
                        "raw_excerpt": _summarize(raw if raw else "", 600),
                        "requirement_count": len(req_ids),
                        **_token_metrics(usage_metrics),
                    }
                )

        verifications = [parsed_by_id[item_id] for item_id in req_ids if item_id in parsed_by_id]
        technical_failures: list[dict[str, Any]] = []
        model_unavailable_failure = bool(attempt_records) and not parsed_by_id and all(
            str(item.get("state") or "") == "parse_failed"
            and _is_agent2_model_unavailable_error(item.get("error"))
            for item in attempt_records
        )
        failure_reason = "model_unavailable" if model_unavailable_failure else ""
        if missing_ids:
            log.warning(f"[{self.task_key}] Agent2 batch missing verifications ({missing_ids}): {last_error}")
            for req_id in missing_ids:
                verifications.append(
                    {
                        "id": req_id,
                        "status": "failed",
                        "evidence": (
                            "Agent2 batch javobida bu requirement uchun valid verification topilmadi; "
                            f"manual review kerak: {last_error or 'missing item'}"
                        ),
                    }
                )
                technical_failures.append(
                    {
                        "id": req_id,
                        "error": _summarize(last_error or "batch missing item", 500),
                        "failure_reason": failure_reason,
                        "attempts": attempt_records,
                    }
                )

        retry_count = max(0, len(attempt_records) - 1)
        schema_validation_failures = sum(
            1
            for item in attempt_records
            if str(item.get("state") or "") in {"parse_failed", "partial"}
        )
        state = "completed" if not missing_ids and parsed_by_id else "technical_failure"
        return {
            "verifications": verifications,
            "technical_failures": technical_failures,
            "warnings": warnings,
            "call_records": [
                {
                    "id": ",".join(req_ids),
                    "state": state,
                    "failure_reason": failure_reason,
                    "latency_ms": int((perf_counter() - started) * 1000),
                    "model": model_used,
                    "attempt_count": len(attempt_records),
                    "attempts": attempt_records,
                    "requirement_count": len(req_ids),
                    "verification_count": len(verifications),
                }
            ],
            "schema_validation_failures": schema_validation_failures,
            "model_call_count": len(attempt_records),
            "retry_count": retry_count,
        }

    def _run_agent2_single_requirement(
        self,
        *,
        requirement: dict[str, Any],
        context: dict[str, Any],
        code_changes: str,
        api_keys: list[str],
        max_attempts: int,
        cached_content: str = "",
        fallback_cached_content: str = "",
        shared_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        req_id = str(requirement.get("id") or "").strip()
        started = perf_counter()
        prompt = agent2_contract.build_single_prompt(
            requirement=requirement,
            pr_info=context["pr_info"],
            code_changes=code_changes,
        )
        attempt_records: list[dict[str, Any]] = []
        parsed: dict[str, Any] | None = None
        last_error = ""

        for attempt in range(1, max_attempts + 1):
            raw = ""
            usage_metrics: dict[str, int] = {}
            model_used, _fallback_model = self._model_names_for_agent("agent2_verifier")
            attempt_started = perf_counter()
            try:
                raw, model_used, usage_metrics = self._call_agent2_single_raw_isolated(
                    prompt,
                    api_keys,
                    cached_content=cached_content,
                    fallback_cached_content=fallback_cached_content,
                    shared_state=shared_state,
                )
                parse_result = _parse_gemini_json(raw)
                if not parse_result.ok:
                    raise ValueError(parse_result.error or "Agent2 JSON parse failed")
                validation = agent2_contract.validate_agent2_json(
                    parse_result.data,
                    expected_id=req_id,
                )
                if not validation.get("ok"):
                    raise ValueError(str(validation.get("error") or "Agent2 JSON validation failed"))
                parsed = validation["verification"]
                attempt_records.append(
                    {
                        "attempt": attempt,
                        "state": "completed",
                        "latency_ms": int((perf_counter() - attempt_started) * 1000),
                        "model": model_used,
                        "raw_length": len(raw or ""),
                        "used_cleanup": parse_result.used_cleanup,
                        "used_repair": parse_result.used_repair,
                        "repair_type": parse_result.repair_type,
                        "warnings": [*parse_result.warnings, *list(validation.get("warnings") or [])],
                        **usage_metrics,
                    }
                )
                break
            except Exception as exc:
                last_error = str(exc).strip() or exc.__class__.__name__
                attempt_records.append(
                    {
                        "attempt": attempt,
                        "state": "parse_failed",
                        "latency_ms": int((perf_counter() - attempt_started) * 1000),
                        "model": model_used,
                        "error": _summarize(last_error, 320),
                        "raw_length": len(raw or ""),
                        "raw_excerpt": _summarize(raw if raw else "", 600),
                        **_token_metrics(usage_metrics),
                    }
                )

        model_used = str((attempt_records[-1] if attempt_records else {}).get("model") or PRO_MODEL_NAME)
        retry_count = max(0, len(attempt_records) - 1)
        schema_validation_failures = sum(
            1
            for item in attempt_records
            if str(item.get("state") or "") == "parse_failed"
        )
        model_unavailable_failure = bool(attempt_records) and all(
            str(item.get("state") or "") == "parse_failed"
            and _is_agent2_model_unavailable_error(item.get("error"))
            for item in attempt_records
        )
        failure_reason = "model_unavailable" if model_unavailable_failure else ""

        if parsed is None:
            evidence = (
                "Agent2 texnik xato sabab bu requirementni tekshira olmadi; "
                f"manual review kerak: {last_error or 'empty/invalid response'}"
            )
            log.warning(f"[{self.task_key}] Agent2 single verification technical failure ({req_id}): {last_error}")
            return {
                "verification": {
                    "id": req_id,
                    "status": "failed",
                    "evidence": evidence,
                },
                "technical_failures": [
                    {
                        "id": req_id,
                        "error": _summarize(last_error or "empty/invalid response", 500),
                        "failure_reason": failure_reason,
                        "attempts": attempt_records,
                    }
                ],
                "warnings": [f"Agent2 single verification technical failure ({req_id}): {last_error}"],
                "call_record": {
                    "id": req_id,
                    "state": "technical_failure",
                    "failure_reason": failure_reason,
                    "latency_ms": int((perf_counter() - started) * 1000),
                    "model": model_used,
                    "attempt_count": len(attempt_records),
                    "attempts": attempt_records,
                },
                "schema_validation_failures": schema_validation_failures,
                "model_call_count": len(attempt_records),
                "retry_count": retry_count,
            }

        try:
            verification, item_warnings = agent2_contract.normalize_single_verification(
                parsed,
                requirement=requirement,
            )
            if item_warnings:
                schema_validation_failures += 1
            return {
                "verification": verification,
                "technical_failures": [],
                "warnings": item_warnings,
                "call_record": {
                    "id": req_id,
                    "state": "completed",
                    "latency_ms": int((perf_counter() - started) * 1000),
                    "model": model_used,
                    "attempt_count": len(attempt_records),
                    "attempts": attempt_records,
                },
                "schema_validation_failures": schema_validation_failures,
                "model_call_count": len(attempt_records),
                "retry_count": retry_count,
            }
        except Exception as exc:
            error = str(exc).strip() or exc.__class__.__name__
            log.warning(f"[{self.task_key}] Agent2 single verification normalize fallback ({req_id}): {error}")
            return {
                "verification": {
                    "id": req_id,
                    "status": "failed",
                    "evidence": f"Agent2 bu requirementni tekshira olmadi: {error}",
                },
                "technical_failures": [],
                "warnings": [f"Agent2 single verification fallback ishlatildi ({req_id}): {error}"],
                "call_record": {
                    "id": req_id,
                    "state": "failed",
                    "latency_ms": int((perf_counter() - started) * 1000),
                    "model": model_used,
                    "attempt_count": len(attempt_records),
                    "attempts": attempt_records,
                },
                "schema_validation_failures": schema_validation_failures + 1,
                "model_call_count": len(attempt_records),
                "retry_count": retry_count,
            }

    def _agent2_single_unexpected_failure(self, req_id: str, error: str) -> dict[str, Any]:
        evidence = f"Agent2 parallel worker texnik xato sabab bu requirementni tekshira olmadi: {error}"
        return {
            "verification": {
                "id": req_id,
                "status": "failed",
                "evidence": evidence,
            },
            "technical_failures": [
                {
                    "id": req_id,
                    "error": _summarize(error, 500),
                    "attempts": [],
                }
            ],
            "warnings": [f"Agent2 parallel worker technical failure ({req_id}): {error}"],
            "call_record": {
                "id": req_id,
                "state": "technical_failure",
                "latency_ms": 0,
                "model": PRO_MODEL_NAME,
                "attempt_count": 0,
                "attempts": [],
            },
            "schema_validation_failures": 1,
            "model_call_count": 0,
            "retry_count": 0,
        }

    def _agent2_batch_unexpected_failure(self, req_ids: list[str], error: str) -> dict[str, Any]:
        ids = [str(item or "").strip() for item in req_ids if str(item or "").strip()]
        failure_reason = "model_unavailable" if _is_agent2_model_unavailable_error(error) else ""
        return {
            "verifications": [
                {
                    "id": req_id,
                    "status": "failed",
                    "evidence": f"Agent2 parallel batch worker texnik xato sabab bu requirementni tekshira olmadi: {error}",
                }
                for req_id in ids
            ],
            "technical_failures": [
                {
                    "id": req_id,
                    "error": _summarize(error, 500),
                    "failure_reason": failure_reason,
                    "attempts": [],
                }
                for req_id in ids
            ],
            "warnings": [f"Agent2 parallel batch worker technical failure ({', '.join(ids)}): {error}"],
            "call_records": [
                {
                    "id": ",".join(ids),
                    "state": "technical_failure",
                    "failure_reason": failure_reason,
                    "latency_ms": 0,
                    "model": self._model_names_for_agent("agent2_verifier")[0],
                    "attempt_count": 0,
                    "attempts": [],
                    "requirement_count": len(ids),
                    "verification_count": 0,
                }
            ],
            "schema_validation_failures": 1,
            "model_call_count": 0,
            "retry_count": 0,
        }

    def _agent2_model_unavailable_skipped_batch(self, req_ids: list[str], reason: str) -> dict[str, Any]:
        ids = [str(item or "").strip() for item in req_ids if str(item or "").strip()]
        error = f"model_unavailable: {reason}"
        return {
            "verifications": [
                {
                    "id": req_id,
                    "status": "failed",
                    "evidence": (
                        "Agent2 model_unavailable circuit breaker sabab bu requirement modelga yuborilmadi; "
                        "manual review kerak."
                    ),
                }
                for req_id in ids
            ],
            "technical_failures": [
                {
                    "id": req_id,
                    "error": error,
                    "failure_reason": "model_unavailable",
                    "attempts": [],
                }
                for req_id in ids
            ],
            "warnings": [
                f"Agent2 model_unavailable circuit breaker sabab batch skip qilindi ({', '.join(ids)})."
            ],
            "call_records": [
                {
                    "id": ",".join(ids),
                    "state": "technical_failure",
                    "failure_reason": "model_unavailable",
                    "skipped_due_to_circuit_breaker": True,
                    "latency_ms": 0,
                    "model": self._model_names_for_agent("agent2_verifier")[0],
                    "attempt_count": 0,
                    "attempts": [],
                    "requirement_count": len(ids),
                    "verification_count": 0,
                }
            ],
            "schema_validation_failures": 0,
            "model_call_count": 0,
            "retry_count": 0,
        }

    def _call_agent2_batch_raw_isolated(
        self,
        prompt: str,
        api_keys: list[str],
        cached_content: str = "",
        fallback_cached_content: str = "",
        shared_state: dict[str, Any] | None = None,
    ) -> tuple[str, str, dict[str, int]]:
        primary_model, fallback_model = self._model_names_for_agent("agent2_verifier")
        helper = GeminiHelper(
            api_keys=api_keys,
            model_name=primary_model,
            fallback_model_name=fallback_model,
            shared_state=shared_state,
        )
        raw = helper.analyze(
            prompt,
            max_output_tokens=8192,
            generation_config_overrides={
                "response_mime_type": "application/json",
                "response_schema": agent2_contract.BATCH_RESPONSE_SCHEMA,
            },
            cached_content=cached_content or None,
            fallback_cached_content=fallback_cached_content or None,
        )
        return raw, str(helper.last_model_used or primary_model), _token_metrics(helper.last_usage_metadata)

    def _call_agent2_single_raw_isolated(
        self,
        prompt: str,
        api_keys: list[str],
        cached_content: str = "",
        fallback_cached_content: str = "",
        shared_state: dict[str, Any] | None = None,
    ) -> tuple[str, str, dict[str, int]]:
        primary_model, fallback_model = self._model_names_for_agent("agent2_verifier")
        helper = GeminiHelper(
            api_keys=api_keys,
            model_name=primary_model,
            fallback_model_name=fallback_model,
            shared_state=shared_state,
        )
        raw = helper.analyze(
            prompt,
            max_output_tokens=2048,
            generation_config_overrides={
                "response_mime_type": "application/json",
                "response_schema": agent2_contract.SINGLE_RESPONSE_SCHEMA,
            },
            cached_content=cached_content or None,
            fallback_cached_content=fallback_cached_content or None,
        )
        return raw, str(helper.last_model_used or primary_model), _token_metrics(helper.last_usage_metadata)

    def _call_agent2_extra_scan_raw(
        self,
        prompt: str,
        api_keys: list[str],
        cached_content: str = "",
        fallback_cached_content: str = "",
        shared_state: dict[str, Any] | None = None,
    ) -> tuple[str, str, dict[str, int]]:
        primary_model, fallback_model = self._model_names_for_agent("agent2_verifier")
        helper = GeminiHelper(
            api_keys=api_keys,
            model_name=primary_model,
            fallback_model_name=fallback_model,
            shared_state=shared_state,
        )
        raw = helper.analyze(
            prompt,
            max_output_tokens=4096,
            generation_config_overrides={
                "response_mime_type": "application/json",
                "response_schema": agent2_contract.EXTRA_RESPONSE_SCHEMA,
            },
            cached_content=cached_content or None,
            fallback_cached_content=fallback_cached_content or None,
        )
        return raw, str(helper.last_model_used or primary_model), _token_metrics(helper.last_usage_metadata)

    def _run_agent3(
        self,
        context: dict[str, Any],
        agent1: dict[str, Any],
        agent2: dict[str, Any],
    ) -> dict[str, Any]:
        agent_key = "agent3_arbiter"
        self._start_agent(agent_key, "Agent1 va Agent2 natijalari arbitraj qilinmoqda")
        prompt = agent3_contract.build_prompt(
            requirements=agent1.get("requirements") or [],
            verifications=agent2.get("verifications") or [],
            extra=agent2.get("extra") or [],
            technical_failures=agent2.get("technical_failures") or [],
            dev_comments=context.get("agent3_dev_comments") or [],
        )

        fallback = agent3_contract.fallback_arbiter(
            requirements=agent1.get("requirements") or [],
            verifications=agent2.get("verifications") or [],
            extra=agent2.get("extra") or [],
            technical_failures=agent2.get("technical_failures") or [],
            agent2_success=bool(agent2.get("success")),
        )

        try:
            raw = self._model_for_agent(agent_key).analyze(
                prompt,
                max_output_tokens=4096,
                generation_config_overrides={
                    "response_mime_type": "application/json",
                    "response_schema": agent3_contract.RESPONSE_SCHEMA,
                },
            )
            parse_result = _parse_gemini_json(raw)
            if not parse_result.ok:
                raise ValueError(parse_result.error or "Agent3 JSON parse failed")
            validation = agent3_contract.validate_agent3_json(parse_result.data)
            if not validation.get("ok"):
                raise ValueError(str(validation.get("error") or "Agent3 JSON validation failed"))
            parsed = validation["data"]
            summary = str(parsed.get("summary") or "").strip() or fallback["summary"]
            quality = agent3_contract.build_quality_artifact(
                requirements=agent1.get("requirements") or [],
                verifications=agent2.get("verifications") or [],
                extra=agent2.get("extra") or [],
                technical_failures=agent2.get("technical_failures") or [],
                parsed=parsed,
                agent2_success=bool(agent2.get("success")),
            )
            final_requirements = quality["requirements"]
            run_state = quality["run_state"]
            verdict = quality["verdict"]
            verdict_label = quality["verdict_label"]
            verdict_reason = quality["verdict_reason"]
            warnings = [*parse_result.warnings, *list(validation.get("warnings") or [])]
        except Exception as exc:
            log.warning(f"[{self.task_key}] Agent3 fallback ishladi: {exc}")
            final_requirements = fallback["requirements"]
            run_state = fallback["run_state"]
            verdict = fallback["verdict"]
            verdict_label = fallback["verdict_label"]
            verdict_reason = fallback["verdict_reason"]
            warnings = [f"Agent3 fallback ishlatildi: {exc}", *fallback.get("warnings", [])]
            summary = fallback["summary"]
            quality = fallback

        self._finish_agent(
            agent_key,
            state="completed" if run_state == "completed" else "failed" if run_state == "blocked" else "completed",
            input_summary=(
                f"Arbiterga {len(agent1.get('requirements') or [])} ta inventory va "
                f"{len(agent2.get('verifications') or [])} ta verification yuborildi."
            ),
            output_summary=f"{len(final_requirements)} ta requirement bo'yicha checker final matrix hisoblandi.",
            warnings=warnings,
            artifact={
                "summary": summary,
                "run_state": run_state,
                "verdict": verdict,
                "verdict_label": verdict_label,
                "verdict_reason": verdict_reason,
                "quality_status": quality.get("quality_status", "ok"),
                "total_requirements": quality.get("total_requirements", 0),
                "completed_count": quality.get("completed_count", 0),
                "failed_count": quality.get("failed_count", 0),
                "technical_count": quality.get("technical_count", 0),
                "skipped_count": quality.get("skipped_count", 0),
                "completed": quality.get("completed", []),
                "failed": quality.get("failed", []),
                "technical": quality.get("technical", []),
                "skipped": quality.get("skipped", []),
                "skip_reasons": quality.get("skip_reasons", {}),
                "missing": quality.get("missing", []),
                "invalid": quality.get("invalid", []),
                "extra": quality.get("extra", []),
                "extra_code_risk": quality.get("extra_code_risk", "none"),
                "requirements": final_requirements,
            },
        )
        return {
            "success": True,
            "summary": summary,
            "run_state": run_state,
            "verdict": verdict,
            "verdict_label": verdict_label,
            "verdict_reason": verdict_reason,
            "quality_status": quality.get("quality_status", "ok"),
            "total_requirements": quality.get("total_requirements", 0),
            "completed_count": quality.get("completed_count", 0),
            "failed_count": quality.get("failed_count", 0),
            "technical_count": quality.get("technical_count", 0),
            "skipped_count": quality.get("skipped_count", 0),
            "completed": quality.get("completed", []),
            "failed": quality.get("failed", []),
            "technical": quality.get("technical", []),
            "skipped": quality.get("skipped", []),
            "skip_reasons": quality.get("skip_reasons", {}),
            "missing": quality.get("missing", []),
            "invalid": quality.get("invalid", []),
            "extra": quality.get("extra", []),
            "extra_code_risk": quality.get("extra_code_risk", "none"),
            "requirements": final_requirements,
            "warnings": warnings,
        }
