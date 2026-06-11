from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TZPRAnalysisSection:
    """Frontend uchun strukturalashtirilgan AI bo'limi."""

    key: str
    title: str
    lines: List[str] = field(default_factory=list)
    items: List[str] = field(default_factory=list)
    item_count: int = 0
    empty: bool = False


@dataclass
class TZPRAnalysisOverview:
    """Frontend checker header/summary uchun qisqa overview."""

    verdict: str = "unknown"
    verdict_label: str = "Unknown"
    verdict_reason: str = ""
    summary_lines: List[str] = field(default_factory=list)
    section_counts: Dict[str, int] = field(default_factory=dict)
    missing_figma_access: bool = False
    requested_sections: List[str] = field(default_factory=list)


@dataclass
class TZPRTaskInfo:
    """QA header/identity panel uchun task metadata."""

    key: str = ""
    summary: str = ""
    issue_type: str = ""
    status: str = ""
    assignee: str = ""
    reporter: str = ""
    priority: str = ""
    story_points: Optional[float] = None
    created_at: str = ""
    resolved_at: str = ""
    labels: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)


@dataclass
class TZPRRunInfo:
    """Checker run texnik parametrlari va signal summary."""

    source: str = "manual"
    requested_output_profile: str = "ui"
    comments_enabled: bool = True
    max_comments_to_read: int = 0
    smart_patch_enabled: bool = True
    ai_data_section_order: List[str] = field(default_factory=list)
    files_analyzed: int = 0
    total_files_changed: int = 0
    prompt_size_chars: int = 0
    ai_retry_count: int = 0
    ai_model: str = ""
    ai_primary_model: str = ""
    ai_fallback_model: str = ""
    ai_used_fallback: bool = False


@dataclass
class TZPRQARecommendation:
    """QA uchun keyingi action recommendation."""

    action: str = "manual_review"
    label: str = "Manual review kerak"
    reason: str = ""


@dataclass
class TZPRCommentSignal:
    """QA comment intelligence ichidagi bitta signal."""

    author: str = ""
    created: str = ""
    preview: str = ""
    full_text: str = ""
    category: str = ""


@dataclass
class TZPRCommentIntelligence:
    """Comment, scope va dev objection signal summary."""

    summary: str = ""
    has_scope_changes: bool = False
    change_count: int = 0
    total_comments: int = 0
    filtered_out_ai_comments: int = 0
    has_dev_objections: bool = False
    objection_count: int = 0
    deferred_scope_detected: bool = False
    scope_note: str = ""
    important_comments: List[TZPRCommentSignal] = field(default_factory=list)
    deferred_scope_comments: List[TZPRCommentSignal] = field(default_factory=list)
    dev_objections: List[TZPRCommentSignal] = field(default_factory=list)


@dataclass
class TZPRWorkflowInfo:
    """Checker workflow/process diagnostika summary."""

    available: bool = False
    source: str = "manual"
    task_status: str = ""
    service1_status: str = ""
    service2_status: str = ""
    compliance_score: Optional[int] = None
    return_reason: str = ""
    blocked_at: str = ""
    blocked_retry_at: str = ""
    updated_at: str = ""
    return_threshold: int = 0
    auto_return_enabled: bool = False
    is_recheck: bool = False
    note: str = ""


@dataclass
class TZPREvidenceItem:
    """Requirement audit ichidagi bitta evidence signali."""

    source: str = ""
    label: str = ""
    detail: str = ""
    url: str = ""


@dataclass
class TZPRCodeReference:
    """Requirement bilan bog'langan kod havolasi."""

    filename: str = ""
    blob_url: str = ""
    pr_number: Optional[int] = None
    pr_url: str = ""
    change_type: str = ""
    additions: Optional[int] = None
    deletions: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    patch_preview: str = ""


@dataclass
class TZPRFigmaReference:
    """Requirement bilan bog'langan Figma source havolasi."""

    name: str = ""
    file_key: str = ""
    url: str = ""
    node_id: str = ""
    summary: str = ""


@dataclass
class TZPRRequirementMatrixItem:
    """QA requirement-level audit qatori."""

    id: str = ""
    status: str = ""
    status_label: str = ""
    requirement: str = ""
    requirement_source: str = ""
    evidence: List[TZPREvidenceItem] = field(default_factory=list)
    code_files: List[str] = field(default_factory=list)
    code_refs: List[TZPRCodeReference] = field(default_factory=list)
    figma_relation: str = ""
    figma_sources: List[TZPRFigmaReference] = field(default_factory=list)
    notes: str = ""


@dataclass
class TZPRAnalysisResult:
    """Tahlil natijasi."""

    task_key: str
    task_summary: str = ""
    tz_content: str = ""
    pr_count: int = 0
    files_changed: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    pr_details: List[Dict] = field(default_factory=list)
    pr_selection: Dict[str, Any] = field(default_factory=dict)
    ai_analysis: str = ""
    compliance_score: Optional[int] = None
    success: bool = True
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)
    status_banner: Optional[Dict] = None
    ai_retry_count: int = 0
    files_analyzed: int = 0
    total_prompt_size: int = 0
    figma_data: Optional[Dict] = None
    comment_analysis: Optional[Dict] = None
    dev_objections: List[Dict] = field(default_factory=list)
    analysis_sections: List[TZPRAnalysisSection] = field(default_factory=list)
    analysis_overview: Optional[TZPRAnalysisOverview] = None
    task_info: Optional[TZPRTaskInfo] = None
    run_info: Optional[TZPRRunInfo] = None
    qa_recommendation: Optional[TZPRQARecommendation] = None
    comment_intelligence: Optional[TZPRCommentIntelligence] = None
    workflow_info: Optional[TZPRWorkflowInfo] = None
    requirement_matrix: List[TZPRRequirementMatrixItem] = field(default_factory=list)
    effective_settings: Dict[str, Any] = field(default_factory=dict)
    execution_mode: str = "multi_agent"
    run_id: str = ""
    run_state: str = ""
    agent_runs: List[Dict[str, Any]] = field(default_factory=list)
    run_events: List[Dict[str, Any]] = field(default_factory=list)
    requirement_inventory: List[Dict[str, Any]] = field(default_factory=list)
    verifications: List[Dict[str, Any]] = field(default_factory=list)
    arbiter_summary: Dict[str, Any] = field(default_factory=dict)
