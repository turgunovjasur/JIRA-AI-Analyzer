export type UserRole = "super_admin" | "company_admin" | "user";

export type CompanyModules = Record<string, boolean>;

export type AuthPayload = {
  auth_source?: string | null;
  company_code?: string | null;
  company_id?: number | null;
  company_name?: string | null;
  expires_at?: string | null;
  last_activity_at?: string | null;
  logged_in: boolean;
  role?: UserRole | null;
  session_nonce?: string | null;
  session_started_at?: string | null;
  user_id?: number | null;
  user_name?: string | null;
};

export type LoginResponse = {
  success: boolean;
  error_message: string;
  auth: AuthPayload | null;
  company_modules: CompanyModules | null;
  session_token?: string | null;
  expires_at?: string | null;
};

export type SessionResponse = {
  success: boolean;
  auth: AuthPayload;
  companyModules: CompanyModules;
  expiresAt?: string | null;
};

export type BackendSessionResponse = {
  success: boolean;
  auth: AuthPayload;
  company_modules: CompanyModules;
  expires_at?: string | null;
};

export type BackendHealth = {
  service?: string;
  status?: string;
  version?: string;
  timestamp?: string;
  endpoints?: Record<string, string>;
  services?: Record<string, string>;
  settings?: Record<string, unknown>;
  queue?: Record<string, unknown>;
};

export type MonitoringSourceInfo = {
  backend?: string;
  db_exists?: boolean;
  db_size_kb?: number | null;
  source_label?: string;
};

export type MonitoringOverallStatsRow = {
  total_tasks?: number | null;
  completed?: number | null;
  avg_compliance?: number | null;
  total_returns?: number | null;
  progressing?: number | null;
  returned?: number | null;
  error?: number | null;
  blocked?: number | null;
  skipped?: number | null;
};

export type MonitoringTaskStatusRow = {
  task_status?: string | null;
  count?: number | null;
};

export type MonitoringServiceStatusRow = {
  service1_status?: string | null;
  service2_status?: string | null;
  count?: number | null;
};

export type MonitoringRecentTaskRow = {
  task_id?: string | null;
  task_status?: string | null;
  service1_status?: string | null;
  service2_status?: string | null;
  compliance_score?: number | null;
  return_count?: number | null;
  skip_detected?: boolean | null;
  last_processed_at?: string | null;
  updated_at?: string | null;
};

export type MonitoringErrorRow = {
  task_id?: string | null;
  updated_at?: string | null;
  task_status?: string | null;
  error_message?: string | null;
  service1_error?: string | null;
  service2_error?: string | null;
};

export type MonitoringBlockedTaskRow = {
  task_id?: string | null;
  service1_status?: string | null;
  service2_status?: string | null;
  blocked_retry_at?: string | null;
  blocked_at?: string | null;
  block_reason?: string | null;
};

export type MonitoringSnapshot = MonitoringSourceInfo & {
  overall_stats: MonitoringOverallStatsRow[];
  task_status_counts: MonitoringTaskStatusRow[];
  service_status_counts: MonitoringServiceStatusRow[];
  recent_tasks: MonitoringRecentTaskRow[];
  errors_log: MonitoringErrorRow[];
  blocked_tasks: MonitoringBlockedTaskRow[];
};

export type TZPRFileChange = {
  filename?: string | null;
  status?: string | null;
  additions?: number | null;
  deletions?: number | null;
  patch?: string | null;
  smart_context?: string | null;
  blob_url?: string | null;
};

export type TZPRPullRequestDetail = {
  number?: number | null;
  title?: string | null;
  url?: string | null;
  state?: string | null;
  source?: string | null;
  merged?: boolean | null;
  additions?: number | null;
  deletions?: number | null;
  files?: TZPRFileChange[];
};

export type TZPRPullRequestSelectionItem = {
  number?: number | null;
  title?: string | null;
  url?: string | null;
  state?: string | null;
  merged?: boolean | null;
  additions?: number | null;
  deletions?: number | null;
  files_count?: number | null;
  reason?: string | null;
};

export type TZPRPullRequestSelection = {
  found_count?: number | null;
  fetched_count?: number | null;
  merged_count?: number | null;
  skipped_count?: number | null;
  analyzed_count?: number | null;
  merged?: TZPRPullRequestSelectionItem[];
  skipped?: TZPRPullRequestSelectionItem[];
};

export type TZPRFigmaSummary = {
  file_key?: string | null;
  name?: string | null;
  url?: string | null;
  summary?: string | null;
};

export type TZPRFigmaData = {
  count?: number | null;
  summaries?: TZPRFigmaSummary[];
};

export type TZPRAnalysisSection = {
  key: string;
  title: string;
  lines?: string[];
  items?: string[];
  item_count?: number | null;
  empty?: boolean;
};

export type TZPRAnalysisOverview = {
  verdict?: "pass" | "fail" | "manual_review" | "blocked" | string;
  verdict_label?: string | null;
  verdict_reason?: string | null;
  summary_lines?: string[];
  section_counts?: Record<string, number>;
  missing_figma_access?: boolean;
  requested_sections?: string[];
};

export type TZPRTaskInfo = {
  key?: string | null;
  summary?: string | null;
  issue_type?: string | null;
  status?: string | null;
  assignee?: string | null;
  reporter?: string | null;
  priority?: string | null;
  story_points?: number | null;
  created_at?: string | null;
  resolved_at?: string | null;
  labels?: string[];
  components?: string[];
};

export type TZPRRunInfo = {
  source?: "manual" | "webhook" | string;
  requested_output_profile?: string | null;
  comments_enabled?: boolean;
  max_comments_to_read?: number | null;
  smart_patch_enabled?: boolean;
  ai_data_section_order?: string[];
  files_analyzed?: number | null;
  total_files_changed?: number | null;
  prompt_size_chars?: number | null;
  ai_retry_count?: number | null;
  ai_model?: string | null;
  ai_primary_model?: string | null;
  ai_fallback_model?: string | null;
  ai_used_fallback?: boolean;
};

export type TZPRQARecommendation = {
  action?: "pass" | "manual_review" | "return" | "blocked" | string;
  label?: string | null;
  reason?: string | null;
};

export type TZPRCommentSignal = {
  author?: string | null;
  created?: string | null;
  preview?: string | null;
  full_text?: string | null;
  category?: "scope_change" | "deferred_scope" | "dev_objection" | string;
};

export type TZPRCommentIntelligence = {
  summary?: string | null;
  has_scope_changes?: boolean;
  change_count?: number | null;
  total_comments?: number | null;
  filtered_out_ai_comments?: number | null;
  has_dev_objections?: boolean;
  objection_count?: number | null;
  deferred_scope_detected?: boolean;
  scope_note?: string | null;
  important_comments?: TZPRCommentSignal[];
  deferred_scope_comments?: TZPRCommentSignal[];
  dev_objections?: TZPRCommentSignal[];
};

export type TZPRWorkflowInfo = {
  available?: boolean;
  source?: "manual" | "webhook" | string;
  task_status?: string | null;
  service1_status?: string | null;
  service2_status?: string | null;
  compliance_score?: number | null;
  return_reason?: string | null;
  blocked_at?: string | null;
  blocked_retry_at?: string | null;
  updated_at?: string | null;
  return_threshold?: number | null;
  auto_return_enabled?: boolean;
  is_recheck?: boolean;
  note?: string | null;
};

export type TZPREvidenceItem = {
  source?: "analysis" | "tz" | "comment" | "pr" | "code" | "figma" | string;
  label?: string | null;
  detail?: string | null;
  url?: string | null;
};

export type TZPRCodeReference = {
  filename?: string | null;
  blob_url?: string | null;
  pr_number?: number | null;
  pr_url?: string | null;
  change_type?: string | null;
  additions?: number | null;
  deletions?: number | null;
  line_start?: number | null;
  line_end?: number | null;
  patch_preview?: string | null;
};

export type TZPRFigmaReference = {
  name?: string | null;
  file_key?: string | null;
  url?: string | null;
  node_id?: string | null;
  summary?: string | null;
};

export type TZPRRequirementMatrixItem = {
  id: string;
  status?: "completed" | "failed" | string;
  status_label?: string | null;
  requirement?: string | null;
  requirement_source?: string | null;
  evidence?: TZPREvidenceItem[];
  code_files?: string[];
  code_refs?: TZPRCodeReference[];
  figma_relation?: string | null;
  figma_sources?: TZPRFigmaReference[];
  notes?: string | null;
};

export type TZPRExecutionMode = "multi_agent";
export type TZPRRunState =
  | "queued"
  | "running"
  | "completed"
  | "manual_review"
  | "blocked"
  | "failed"
  | string;
export type TZPRAgentState =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "blocked"
  | "skipped"
  | string;

export type TZPRRequirementInventoryItem = {
  id?: string;
  text?: string | null;
  source?: "tz" | "comment" | "figma" | "mixed" | string;
  notes?: string | null;
  merged_from?: string[] | null;
};

export type TZPRUntrustedCommentSignal = {
  author?: string | null;
  excerpt?: string | null;
  reason?: string | null;
};

export type TZPRAgent1SourceStats = {
  tz_candidates?: number | null;
  trusted_comment_candidates?: number | null;
  untrusted_signals?: number | null;
  figma_text_candidates?: number | null;
  figma_comment_candidates?: number | null;
  discarded_count?: number | null;
  prompt_comment_count?: number | null;
};

export type TZPRAgent1InputCandidatePreview = {
  tz?: string[];
  trusted_comments?: string[];
  figma_text?: string[];
  figma_comments?: string[];
  untrusted_comments?: string[];
};

export type TZPRAgent1Artifact = {
  summary?: string | null;
  requirements?: TZPRRequirementInventoryItem[];
  untrusted_comment_signals?: TZPRUntrustedCommentSignal[];
  parse_mode?: "model_json" | "recovered_json" | "heuristic_fallback" | string;
  source_stats?: TZPRAgent1SourceStats | null;
  sanitized_input_metadata?: Record<string, unknown> | null;
  discarded_examples?: string[];
  raw_model_excerpt?: string | null;
  input_candidate_preview?: TZPRAgent1InputCandidatePreview | null;
};

export type TZPRRequirementVerificationItem = {
  id?: string;
  evidence?: string | null;
  status?: "completed" | "failed" | string;
  files?: string[];
  figma_relation?: string | null;
  notes?: string | null;
};

export type TZPRExtraCodeChange = {
  text?: string | null;
  risk?: "low" | "medium" | "high" | string;
  files?: string[];
};

export type TZPRArbiterDecisionItem = {
  id?: string;
  text?: string | null;
  source?: string | null;
  status?: "completed" | "failed" | string;
  evidence?: string | null;
  status_label?: string | null;
  files?: string[];
  figma_relation?: string | null;
  note?: string | null;
  reason?: string | null;
};

export type TZPRAgentRunSnapshot = {
  id?: number | null;
  run_id?: string | null;
  agent_key: string;
  agent_label?: string | null;
  agent_order?: number | null;
  state?: TZPRAgentState;
  primary_model?: string | null;
  actual_model?: string | null;
  fallback_model?: string | null;
  used_fallback?: boolean;
  attempts?: number | null;
  input_summary?: string | null;
  output_summary?: string | null;
  error_text?: string | null;
  warnings?: string[];
  artifact?: Record<string, unknown> | null;
  created_at?: string | null;
  updated_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
};

export type TZPRRunEvent = {
  id?: number | null;
  run_id?: string | null;
  agent_key?: string | null;
  level?: "info" | "warning" | "error" | string;
  event_type?: string | null;
  message?: string | null;
  meta?: Record<string, unknown> | null;
  created_at?: string | null;
};

export type TZPRArbiterSummary = {
  summary?: string | null;
  verdict?: "pass" | "fail" | "manual_review" | "blocked" | string;
  verdict_label?: string | null;
  verdict_reason?: string | null;
  quality_status?: string | null;
  total_requirements?: number | null;
  completed_count?: number | null;
  failed_count?: number | null;
  completed?: string[];
  failed?: string[];
  missing?: string[];
  invalid?: string[];
  extra?: TZPRExtraCodeChange[];
  requirements?: TZPRArbiterDecisionItem[];
  extra_code_risk?: string | null;
};

export type TZPREffectiveSettings = {
  visible_sections?: string[];
  read_comments_enabled?: boolean;
  max_comments_to_read?: number | null;
  default_use_smart_patch?: boolean;
  effective_use_smart_patch?: boolean;
  agent2_verification_mode?: "batch" | "per_requirement" | string;
  agent2_parallelism?: number | null;
  ai_data_section_order?: string[];
  show_contradictory_comments?: boolean;
  requested_output_profile?: string | null;
};

export type AnalysisStatusBanner = {
  level?: "error" | "warning" | "info" | string;
  code?: string | null;
  title?: string | null;
  message?: string | null;
  meta?: Record<string, string | number | boolean | null | undefined>;
  actions?: string[];
};

export type TZPRAnalysisResult = {
  success: boolean;
  task_key: string;
  task_summary?: string | null;
  tz_content?: string | null;
  pr_count?: number | null;
  files_changed?: number | null;
  total_additions?: number | null;
  total_deletions?: number | null;
  pr_details?: TZPRPullRequestDetail[];
  pr_selection?: TZPRPullRequestSelection | null;
  ai_analysis?: string | null;
  compliance_score?: number | null;
  error_message?: string | null;
  warnings?: string[];
  ai_retry_count?: number | null;
  files_analyzed?: number | null;
  total_prompt_size?: number | null;
  figma_data?: TZPRFigmaData | null;
  comment_analysis?: Record<string, unknown> | null;
  dev_objections?: Array<Record<string, unknown>>;
  analysis_sections?: TZPRAnalysisSection[];
  analysis_overview?: TZPRAnalysisOverview | null;
  task_info?: TZPRTaskInfo | null;
  run_info?: TZPRRunInfo | null;
  qa_recommendation?: TZPRQARecommendation | null;
  comment_intelligence?: TZPRCommentIntelligence | null;
  workflow_info?: TZPRWorkflowInfo | null;
  requirement_matrix?: TZPRRequirementMatrixItem[];
  effective_settings?: TZPREffectiveSettings | null;
  status_banner?: AnalysisStatusBanner | null;
  execution_mode?: TZPRExecutionMode | string;
  run_id?: string | null;
  run_state?: TZPRRunState | null;
  agent_runs?: TZPRAgentRunSnapshot[];
  run_events?: TZPRRunEvent[];
  requirement_inventory?: TZPRRequirementInventoryItem[];
  verifications?: TZPRRequirementVerificationItem[];
  arbiter_summary?: TZPRArbiterSummary | null;
};

export type TZPRCreateRunRequest = {
  task_key: string;
  max_files?: number | null;
  output_profile?: string | null;
  show_full_diff?: boolean;
  use_smart_patch?: boolean | null;
};

export type TZPRRunSnapshot = {
  run_id: string;
  task_key: string;
  company_id?: number | null;
  user_id?: number | null;
  source?: "manual" | "webhook" | string;
  execution_mode?: TZPRExecutionMode | string;
  run_state?: TZPRRunState;
  active_phase?: string | null;
  status_message?: string | null;
  requested_output_profile?: string | null;
  request_payload?: Record<string, unknown> | null;
  final_result?: TZPRAnalysisResult | null;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  agent_runs?: TZPRAgentRunSnapshot[];
  run_events?: TZPRRunEvent[];
};

export type GeneratedTestCase = {
  id: string;
  title: string;
  description: string;
  preconditions: string;
  steps: string[];
  expected_result: string;
  test_type: string;
  priority: string;
  severity: string;
  tags?: string[];
  requirement_ids?: string[];
};

export type TestcaseScenario = {
  scenario_title: string;
  screen_or_flow?: string;
  requirement_ids?: string[];
  test_cases?: GeneratedTestCase[];
};

export type TestcaseAuditFinding = {
  type: string;
  requirement_ids?: string[];
  requirement_id?: string;
  reason: string;
};

export type TestcaseRequirement = {
  id: string;
  text: string;
  source: string;
};

export type TestcaseRequirementCoverage = {
  total_requirements?: number;
  covered_count?: number;
  uncovered_ids?: string[];
};

export type TestCaseGenerationResult = {
  success: boolean;
  task_key: string;
  task_summary?: string | null;
  test_cases?: GeneratedTestCase[];
  tz_content?: string | null;
  task_full_details?: Record<string, unknown>;
  task_overview?: string | null;
  comment_changes_detected?: boolean;
  comment_summary?: string | null;
  comment_details?: string[];
  total_test_cases?: number | null;
  by_type?: Record<string, number>;
  by_priority?: Record<string, number>;
  error_message?: string | null;
  warnings?: string[];
  custom_context_used?: boolean;
  status_banner?: AnalysisStatusBanner | null;
  ai_model?: string | null;
  requirements?: TestcaseRequirement[];
  requirement_coverage?: TestcaseRequirementCoverage;
  test_scenarios?: TestcaseScenario[];
  audit_findings?: TestcaseAuditFinding[];
};

export type TestcaseCreateRunRequest = {
  task_key: string;
  test_types?: string[];
  custom_context?: string;
  output_profile?: string | null;
};

export type TestcaseRunSnapshot = {
  run_id: string;
  task_key: string;
  company_id?: number | null;
  user_id?: number | null;
  source?: "manual" | "webhook" | string;
  execution_mode?: string;
  run_state?: TZPRRunState;
  active_phase?: string | null;
  status_message?: string | null;
  requested_output_profile?: string | null;
  request_payload?: Record<string, unknown> | null;
  final_result?: TestCaseGenerationResult | null;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  agent_runs?: TZPRAgentRunSnapshot[];
  run_events?: TZPRRunEvent[];
};

export type SettingsIntegrationStatus = {
  figma: boolean;
  gemini: boolean;
  github: boolean;
  jira: boolean;
};

export type SharedSettingsView = {
  success: boolean;
  mode: "company" | "platform" | "user";
  editable: boolean;
  role?: UserRole | null;
  company_name?: string | null;
  fields: {
    jira_server?: string;
    jira_email?: string;
    jira_project_keys?: string;
    github_org?: string;
    figma_token_mask?: string;
    figma_tokens?: Array<{ name: string; mask: string }>;
    jira_token_mask?: string;
    github_token_mask?: string;
    gemini_api_key_1_mask?: string;
    gemini_api_key_2_mask?: string;
    figma_token_present: boolean;
    jira_token_present: boolean;
    github_token_present: boolean;
    gemini_api_key_1_present: boolean;
    gemini_api_key_2_present: boolean;
  };
  integration_status: SettingsIntegrationStatus;
};

export type SharedSettingsSaveRequest = {
  jira_server?: string;
  jira_email?: string;
  jira_project_keys?: string;
  github_org?: string;
  figma_token?: string;
  figma_tokens?: Array<{ name: string; token?: string; keep?: boolean; idx?: number }>;
  jira_token?: string;
  github_token?: string;
  gemini_api_key_1?: string;
  gemini_api_key_2?: string;
};

export type CheckerModuleSettings = {
  agent1_fallback_model?: string;
  agent1_primary_model?: string;
  agent2_fallback_model?: string;
  agent2_primary_model?: string;
  agent3_fallback_model?: string;
  agent3_primary_model?: string;
  agent2_batch_size?: number;
  agent2_extra_scan_enabled?: boolean;
  checker_execution_mode?: TZPRExecutionMode;
  visible_sections: string[];
  ai_data_section_order: string[];
  read_comments_enabled: boolean;
  max_comments_to_read: number;
  trusted_scope_comment_authors?: string;
  dev_comment_source?: string;
};

export type TestcaseModuleSettings = {
  agent1_fallback_model?: string;
  agent1_primary_model?: string;
  agent2_fallback_model?: string;
  agent2_primary_model?: string;
  agent3_fallback_model?: string;
  agent3_primary_model?: string;
  default_test_types: string[];
  testcases_per_requirement: number;
  ai_data_section_order: string[];
  read_comments_enabled: boolean;
  max_comments_to_read: number;
};

export type ModuleSettingsAllowed = {
  checker_visible_sections: string[];
  checker_ai_data_order: string[];
  testcase_ai_data_order: string[];
  testcase_types: string[];
};

export type ModuleSettingsView = {
  success: boolean;
  data: {
    checker: CheckerModuleSettings;
    testcase: TestcaseModuleSettings;
    allowed: ModuleSettingsAllowed;
  };
};

export type ModuleSettingsSaveRequest = {
  checker: CheckerModuleSettings;
  testcase: TestcaseModuleSettings;
};

export type WebhookSettingsView = {
  success: boolean;
  data: {
    auto_return_enabled: boolean;
    checker_delay_seconds: number;
    excluded_assignees: string;
    min_tz_description_chars: number;
    return_threshold: number;
    return_status: string;
    use_adf_format: boolean;
    tz_pr_footer_text: string;
    recheck_comment_text: string;
    return_notification_text: string;
    read_comments_enabled: boolean;
    max_comments_to_read: number;
    show_contradictory_comments: boolean;
    visible_sections: string[];
    ai_data_section_order: string[];
    allowed_issue_types: string;
    skip_code: string;
    skip_comment_text: string;
    max_skip_check_comments: number;
    trigger_status: string;
    trigger_status_aliases: string;
    trigger_statuses: string[];
    testcase_auto_comment_enabled: boolean;
    testcase_auto_comment_trigger_status: string;
    testcase_auto_comment_trigger_aliases: string;
    testcase_default_test_types: string[];
    testcase_testcases_per_requirement: number;
    testcase_ai_data_section_order: string[];
    testcase_read_comments_enabled: boolean;
    testcase_max_comments_to_read: number;
    testcase_agent1_primary_model?: string;
    testcase_agent1_fallback_model?: string;
    testcase_agent2_primary_model?: string;
    testcase_agent2_fallback_model?: string;
    testcase_agent3_primary_model?: string;
    testcase_agent3_fallback_model?: string;
    testcase_ai_max_output_tokens: number;
    testcase_use_adf_format: boolean;
    testcase_footer_text: string;
  };
};

export type WebhookSettingsSaveRequest = {
  auto_return_enabled: boolean;
  checker_delay_seconds?: number;
  excluded_assignees: string;
  min_tz_description_chars: number;
  return_threshold: number;
  return_status: string;
  use_adf_format: boolean;
  tz_pr_footer_text: string;
  recheck_comment_text: string;
  return_notification_text: string;
  read_comments_enabled: boolean;
  max_comments_to_read: number;
  show_contradictory_comments: boolean;
  visible_sections: string[];
  ai_data_section_order: string[];
  allowed_issue_types: string;
  skip_code: string;
  skip_comment_text: string;
  max_skip_check_comments: number;
  trigger_status: string;
  trigger_status_aliases?: string;
  trigger_statuses?: string[];
  testcase_auto_comment_enabled: boolean;
  testcase_auto_comment_trigger_status: string;
  testcase_auto_comment_trigger_aliases: string;
  testcase_default_test_types: string[];
  testcase_testcases_per_requirement: number;
  testcase_ai_data_section_order: string[];
  testcase_read_comments_enabled: boolean;
  testcase_max_comments_to_read: number;
  testcase_agent1_primary_model?: string;
  testcase_agent1_fallback_model?: string;
  testcase_agent2_primary_model?: string;
  testcase_agent2_fallback_model?: string;
  testcase_agent3_primary_model?: string;
  testcase_agent3_fallback_model?: string;
  testcase_ai_max_output_tokens: number;
  testcase_use_adf_format: boolean;
  testcase_footer_text: string;
};

export type SystemSettingsView = {
  success: boolean;
  data: {
    queue_enabled: boolean;
    task_wait_timeout: number;
    checker_testcase_delay: number;
    blocked_retry_delay: number;
    gemini_min_interval: number;
    blocked_check_interval: number;
    key_freeze_duration: number;
    ai_max_retries: number;
    ai_max_input_tokens: number;
    chars_per_token: number;
    db_busy_timeout: number;
    db_connection_timeout: number;
    http_timeout: number;
    executor_timeout: number;
  };
};

export type SystemSettingsSaveRequest = SystemSettingsView["data"];

export type CompanyAdminUser = {
  created_at?: string | null;
  id: number;
  is_active?: boolean | number | null;
  role?: UserRole | null;
  username: string;
};

export type CompanyAdminTeamOverview = {
  available_slots: number;
  company: {
    company_code?: string | null;
    company_name?: string | null;
    id: number;
    seat_limit?: number | null;
  };
  extra_user_count: number;
  success: boolean;
  total_accounts: number;
  users: CompanyAdminUser[];
};

export type CompanyAdminResetTokenPayload = {
  expires_at: string;
  token: string;
  user_id: number;
};

export type SecurityStatus = {
  can_encrypt?: boolean;
  encrypted_storage?: boolean;
  message: string;
  rotation_ready?: boolean;
  status: "danger" | "ok" | "warning" | string;
  using_fallback_key?: boolean;
};

export type BillingHealth = {
  message: string;
  severity: "danger" | "ok" | "warning";
};

export type CompanySubscription = {
  billing_end_date?: string | null;
  billing_mode?: string | null;
  billing_start_date?: string | null;
  last_payment_date?: string | null;
  last_payment_note?: string | null;
  next_payment_date?: string | null;
  plan_name?: string | null;
  subscription_status?: string | null;
};

export type SuperAdminCompany = {
  addon_modules: string[];
  billing_health: BillingHealth;
  company_code: string;
  company_name: string;
  created_at?: string | null;
  derived_modules: string[];
  extra_user_count: number;
  has_api_keys: boolean;
  id: number;
  included_modules: string[];
  is_active: boolean;
  modules: CompanyModules;
  seat_limit: number;
  subscription: CompanySubscription;
  total_accounts: number;
};

export type LoginAuditLog = {
  company_id?: number | null;
  created_at?: string | null;
  identifier?: string | null;
  reason?: string | null;
  role?: string | null;
  success?: boolean | number | null;
  user_id?: number | null;
};

export type GlobalAiDefaults = {
  agent1_fallback_model?: string | null;
  agent1_primary_model?: string | null;
  agent2_fallback_model?: string | null;
  agent2_primary_model?: string | null;
  agent3_fallback_model?: string | null;
  agent3_primary_model?: string | null;
  api_key_1_mask?: string | null;
  api_key_1_present: boolean;
  api_key_2_mask?: string | null;
  api_key_2_present: boolean;
  key_freeze_minutes?: number | null;
  testcase_agent1_fallback_model?: string | null;
  testcase_agent1_primary_model?: string | null;
  testcase_agent2_fallback_model?: string | null;
  testcase_agent2_primary_model?: string | null;
  testcase_agent3_fallback_model?: string | null;
  testcase_agent3_primary_model?: string | null;
};

export type SuperAdminOverviewMetrics = {
  active: number;
  billable: number;
  blocked: number;
  expiring_soon: number;
  past_due: number;
  total: number;
};

export type SuperAdminOverview = {
  auth_source?: string | null;
  current_admin: boolean;
  global_ai_defaults: GlobalAiDefaults;
  metrics: SuperAdminOverviewMetrics;
  recent_login_audit_logs: LoginAuditLog[];
  security_status: SecurityStatus;
  success: boolean;
  companies: SuperAdminCompany[];
};
