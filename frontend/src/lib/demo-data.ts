// Demo rejim uchun mock data. Real backend/DB'ga aloqasi yo'q —
// faqat qa-assistant.uz mehmonlariga tizim qanday ishlashini ko'rsatish uchun.

export type DemoAgentState = "pending" | "running" | "completed";

export type DemoAgent = {
  key: string;
  label: string;
  running: string; // ishlab turgandagi bosqich matni
  done: string; // tugagach qisqa xulosa
  model: string; // masalan "Pro" / "Flash"
};

export type DemoEvent = {
  agent: string;
  message: string;
  level?: "info" | "error";
};

export type DemoRequirementStatus = "completed" | "failed" | "skipped";

export type DemoRequirement = {
  id: string;
  status: DemoRequirementStatus;
  requirement: string;
  evidence: string;
  source: string;
};

export const DEMO_TASK_KEY = "DEV-1284";
export const DEMO_TASK_SUMMARY = "Parolni tiklash: SMS orqali kod yuborish";

// ─────────────────────────── CHECKER (Servis-1) ───────────────────────────

export const DEMO_CHECKER_AGENTS: DemoAgent[] = [
  {
    key: "agent1_scope",
    label: "Scope Builder",
    running: "TZ talablarga ajratilmoqda…",
    done: "8 talab ajratildi",
    model: "Pro",
  },
  {
    key: "agent2_verifier",
    label: "Verifier",
    running: "Talablar PR kodida tekshirilmoqda…",
    done: "PR bo'yicha tekshirildi",
    model: "Pro",
  },
  {
    key: "agent3_arbiter",
    label: "Arbiter",
    running: "Yakuniy qaror chiqarilmoqda…",
    done: "Yakuniy qaror tayyor",
    model: "Pro",
  },
];

export const DEMO_CHECKER_EVENTS: DemoEvent[] = [
  { agent: "queue", message: "Run navbatga qo'yildi · execution_mode=multi_agent" },
  { agent: "context", message: "JIRA task, PR #482 va Figma ma'lumotlari yig'ildi" },
  { agent: "agent1_scope", message: "TZ 8 ta talabga ajratildi" },
  { agent: "agent2_verifier", message: "Talablar PR diff bilan solishtirilmoqda" },
  { agent: "agent2_verifier", message: "1 ta talab kodda topilmadi" },
  { agent: "agent3_arbiter", message: "Moslik bali hisoblandi: 88%" },
  { agent: "done", message: "Natija tayyor · JIRA'ga izoh yozildi" },
];

export const DEMO_CHECKER_RESULT = {
  taskKey: DEMO_TASK_KEY,
  taskSummary: DEMO_TASK_SUMMARY,
  complianceScore: 88,
  verdict: "O'tdi",
  completed: 7,
  failed: 1,
  aiRetry: 0,
  additions: 241,
  deletions: 18,
  filesChanged: 9,
  prLabel: "1/1",
  figma: true,
  figmaSignals: 3,
  summaryLines: [
    "TZ 8 ta talabga ajratildi; 7 tasi PR kodida to'liq bajarilgan.",
    "1 ta talab (bloklash vaqtini UI'da ko'rsatish) bajarilmagan — kichik.",
    "Moslik bali 88% — chegaradan (80%) yuqori, task keyingi bosqichga o'tkazildi.",
  ],
  requirements: [
    {
      id: "REQ-1",
      status: "completed",
      requirement: "Foydalanuvchi telefon raqamini kiritadi va SMS kod so'raladi",
      evidence: "sms_service.py — send_code() 6 xonali kod generatsiya qiladi va yuboradi.",
      source: "TZ",
    },
    {
      id: "REQ-2",
      status: "completed",
      requirement: "Kod 6 xonali bo'lishi kerak",
      evidence: "generate_code() random 6-digit; test_sms.py da tekshirilgan.",
      source: "TZ",
    },
    {
      id: "REQ-3",
      status: "completed",
      requirement: "Kod 60 soniya amal qiladi",
      evidence: "code_ttl=60, verify_code() da expiry tekshiruvi bor.",
      source: "TZ",
    },
    {
      id: "REQ-4",
      status: "completed",
      requirement: "3 marta xato kiritilsa 5 daqiqa bloklash",
      evidence: "attempt_counter + block_until logikasi auth_limits.py da.",
      source: "TZ",
    },
    {
      id: "REQ-5",
      status: "completed",
      requirement: "Muvaffaqiyatda yangi parol o'rnatish formasi",
      evidence: "ResetPasswordForm komponenti; PR diff'da mavjud.",
      source: "TZ",
    },
    {
      id: "REQ-6",
      status: "skipped",
      requirement: "Rate-limit (IP bo'yicha) — keyingi sprintda",
      evidence: "Dev izohi: ushbu talab keyingi sprintga ko'chirilgan.",
      source: "Comment",
    },
    {
      id: "REQ-7",
      status: "failed",
      requirement: "Bloklash vaqtini foydalanuvchiga UI'da ko'rsatish",
      evidence: "Backend'da block_until bor, lekin frontend'da countdown ko'rsatilmagan.",
      source: "TZ",
    },
  ] as DemoRequirement[],
  issues: [
    "SMS kod ba'zi holatlarda plaintext holda log'ga yozilmoqda (xavfsizlik).",
  ],
};

// ─────────────────────────── TESTCASE (Servis-2) ───────────────────────────

export const DEMO_TESTCASE_AGENTS: DemoAgent[] = [
  {
    key: "agent1_requirements",
    label: "Talablar",
    running: "Talablar ajratilmoqda…",
    done: "8 talab aniqlandi",
    model: "Pro",
  },
  {
    key: "agent2_testcase",
    label: "Testcase writer",
    running: "Test case'lar yozilmoqda…",
    done: "8 test case yozildi",
    model: "Pro",
  },
  {
    key: "agent3_audit",
    label: "Audit",
    running: "Audit va guruhlash…",
    done: "Qamrov tekshirildi",
    model: "Pro",
  },
];

export const DEMO_TESTCASE_EVENTS: DemoEvent[] = [
  { agent: "queue", message: "Run navbatga qo'yildi" },
  { agent: "agent1_requirements", message: "8 ta talab aniqlandi" },
  { agent: "agent2_testcase", message: "Positive va negative senariylar yozilmoqda" },
  { agent: "agent2_testcase", message: "8 test case yaratildi" },
  { agent: "agent3_audit", message: "Qamrov: 8/8 talab qoplandi" },
  { agent: "done", message: "Natija tayyor · JIRA'ga izoh yozildi" },
];

export type DemoTestCase = {
  id: string;
  title: string;
  type: "positive" | "negative";
  priority: "High" | "Medium" | "Low";
  description: string;
  preconditions: string;
  steps: string[];
  expected: string;
  requirementIds: string[];
};

export const DEMO_TESTCASE_RESULT = {
  taskKey: DEMO_TASK_KEY,
  totalTestCases: 8,
  totalRequirements: 8,
  covered: 8,
  highPriority: 4,
  byType: { positive: 5, negative: 3 },
  testCases: [
    {
      id: "TC-01",
      title: "To'g'ri kod bilan parol tiklash",
      type: "positive",
      priority: "High",
      description: "To'liq muvaffaqiyatli oqim — telefon → kod → yangi parol.",
      preconditions: "Ro'yxatdan o'tgan foydalanuvchi, faol telefon raqami.",
      steps: [
        "Telefon raqamini kiriting va \"Kod yuborish\"ni bosing",
        "SMS'dagi 6 xonali kodni kiriting",
        "Yangi parolni o'rnating va tasdiqlang",
      ],
      expected: "Parol yangilanadi, foydalanuvchi login sahifasiga yo'naltiriladi.",
      requirementIds: ["REQ-1", "REQ-2", "REQ-5"],
    },
    {
      id: "TC-02",
      title: "Noto'g'ri kod kiritilganda xatolik",
      type: "negative",
      priority: "High",
      description: "Xato kod urinishlarida to'g'ri xabar va hisoblagich.",
      preconditions: "Kod yuborilgan, tasdiqlash sahifasi ochiq.",
      steps: ["Xato 6 xonali kod kiriting", "Tasdiqlashni bosing"],
      expected: "\"Kod noto'g'ri\" xatosi ko'rinadi, urinishlar soni ortadi.",
      requirementIds: ["REQ-1", "REQ-4"],
    },
    {
      id: "TC-03",
      title: "Kod muddati o'tganda (60 soniya)",
      type: "negative",
      priority: "Medium",
      description: "Muddati o'tgan kod qabul qilinmasligi kerak.",
      preconditions: "Kod yuborilgan.",
      steps: ["Kodni oling va 60 soniya kuting", "Eski kodni kiriting"],
      expected: "\"Kod muddati tugagan, qayta yuboring\" xabari ko'rinadi.",
      requirementIds: ["REQ-3"],
    },
    {
      id: "TC-04",
      title: "3 marta xatodan keyin bloklash",
      type: "negative",
      priority: "High",
      description: "Ketma-ket 3 xato urinishdan keyin 5 daqiqa bloklash.",
      preconditions: "Kod yuborilgan.",
      steps: ["Ketma-ket 3 marta xato kod kiriting", "4-marta urinib ko'ring"],
      expected: "Hisob 5 daqiqaga bloklanadi, tegishli xabar ko'rinadi.",
      requirementIds: ["REQ-4"],
    },
    {
      id: "TC-05",
      title: "Yangi parol talablariga mos kelishi",
      type: "positive",
      priority: "Medium",
      description: "Parol siyosati (uzunlik, belgilar) tekshiriladi.",
      preconditions: "Kod muvaffaqiyatli tasdiqlangan.",
      steps: ["Qisqa parol kiriting", "Keyin to'g'ri parol kiriting"],
      expected: "Zaif parol rad etiladi, to'g'ri parol qabul qilinadi.",
      requirementIds: ["REQ-5"],
    },
  ] as DemoTestCase[],
};

// ─────────────────────────── MONITORING ───────────────────────────

export const DEMO_MONITORING = {
  health: {
    status: "healthy",
    services: [
      { name: "database", status: "ok" },
      { name: "gemini", status: "ok" },
      { name: "jira", status: "ok" },
      { name: "github", status: "ok" },
      { name: "queue", status: "ok" },
    ],
    executionMode: "multi_agent",
    timestamp: "2026-07-20 15:42",
  },
  metrics: {
    total: 342,
    completed: 289,
    progressing: 6,
    returned: 34,
    error: 9,
    blocked: 4,
    avgCompliance: 86.4,
  },
  service1: { done: 318, pending: 6, error: 9, blocked: 4, skip: 5 },
  service2: { done: 271, pending: 12, error: 5, blocked: 3 },
  recentTasks: [
    { id: "DEV-1284", status: "completed", s1: "done", s2: "done", score: 88, returns: 0, updated: "20.07 15:42" },
    { id: "DEV-1279", status: "returned", s1: "done", s2: "pending", score: 57, returns: 1, updated: "20.07 15:31" },
    { id: "DEV-1276", status: "completed", s1: "done", s2: "done", score: 94, returns: 0, updated: "20.07 15:18" },
    { id: "DEV-1274", status: "progressing", s1: "done", s2: "pending", score: null, returns: 0, updated: "20.07 15:09" },
    { id: "DEV-1268", status: "completed", s1: "done", s2: "done", score: 81, returns: 0, updated: "20.07 14:55" },
    { id: "DEV-1265", status: "error", s1: "error", s2: "pending", score: null, returns: 0, updated: "20.07 14:40" },
    { id: "DEV-1261", status: "completed", s1: "done", s2: "done", score: 90, returns: 0, updated: "20.07 14:22" },
    { id: "DEV-1258", status: "returned", s1: "done", s2: "pending", score: 62, returns: 2, updated: "20.07 14:03" },
  ],
  errors: [
    { id: "DEV-1265", updated: "20.07 14:40", message: "GitHub PR topilmadi — havola noto'g'ri", s1: "PR link 404", s2: "kutilmoqda" },
    { id: "DEV-1240", updated: "20.07 12:18", message: "Gemini timeout — barcha kalitlar band", s1: "WARN_AI_TIMEOUT", s2: "—" },
  ],
  blocked: [
    { id: "DEV-1258", retryAt: "20.07 16:03", s1: "done", s2: "blocked", reason: "Kvota tugadi — retry rejalashtirildi" },
  ],
};

// ─────────────────────────── ABOUT / CONTACT ───────────────────────────

export const DEMO_ABOUT = {
  productName: "QA-Assistant",
  tagline: "AI multi-agentlarga asoslangan zamonaviy QA yordamchisi",
  intro:
    "QA-Assistant — JIRA bilan integratsiyalashgan, TZ va PR mosligini tekshirib, test case'larni avtomatik yozadigan sun'iy intellekt yordamchisi. Har bir tekshiruv bitta AI emas, bir nechta agent (scope → verify → arbiter) tomonidan bajariladi — natija ishonchli va tekshiriladigan bo'ladi.",
  highlights: [
    { title: "Multi-agent aniqlik", text: "Har modul 3 agentdan iborat: biri ajratadi, biri tekshiradi, biri yakuniy qaror chiqaradi." },
    { title: "JIRA'da avtonom", text: "Task \"Testing\"ga o'tishi bilan o'zi ishlaydi va izohni to'g'ridan-to'g'ri JIRA'ga yozadi." },
    { title: "Ko'p tenantli", text: "Har kompaniyaning o'z kalitlari va sozlamalari — xavfsiz va ajratilgan." },
  ],
};
