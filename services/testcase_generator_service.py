# services/testcase_generator_service.py
"""
Test Case Generator Service with Smart Patch & Custom Context Support

OPTIMIZED VERSION:
- BaseService'dan meros oladi
- PRHelper ishlatadi (Smart Patch bilan)
- TZHelper ishlatadi
- Custom Context support (AI ga qo'shimcha buyruq)
- Kod dublikatsiyasi yo'q

Author: JASUR TURGUNOV
Version: 6.0 CUSTOM CONTEXT
"""
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
import json

# Core imports
from core import BaseService, PRHelper, TZHelper


@dataclass
class TestCase:
    """Test case structure"""
    id: str
    title: str
    description: str
    preconditions: str
    steps: List[str]
    expected_result: str
    test_type: str
    priority: str
    severity: str
    tags: List[str] = field(default_factory=list)


@dataclass
class TestCaseGenerationResult:
    """Test case generation natijasi"""
    task_key: str
    task_summary: str
    test_cases: List[TestCase] = field(default_factory=list)
    tz_content: str = ""
    pr_count: int = 0
    files_changed: int = 0
    pr_details: List[Dict] = field(default_factory=list)  # PR details for Code Changes tab
    task_full_details: Dict = field(default_factory=dict)
    task_overview: str = ""
    comment_changes_detected: bool = False
    comment_summary: str = ""
    comment_details: List[str] = field(default_factory=list)
    total_test_cases: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_priority: Dict[str, int] = field(default_factory=dict)
    success: bool = True
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)
    custom_context_used: bool = False  # ✅ NEW


class TestCaseGeneratorService(BaseService):
    """
    Test Case Generator Service

    REFACTORED VERSION with Smart Patch & Custom Context:
    - BaseService'dan meros oladi
    - PRHelper ishlatadi (Smart Patch bilan)
    - TZHelper ishlatadi
    - Custom Context support
    - Kod dublikatsiyasi yo'q
    """

    def __init__(self):
        """Initialize service"""
        super().__init__()
        self._pr_helper = None

    @property
    def pr_helper(self):
        """Lazy PR Helper"""
        if self._pr_helper is None:
            self._pr_helper = PRHelper(self.github)
        return self._pr_helper

    def generate_test_cases(
            self,
            task_key: str,
            include_pr: bool = True,
            use_smart_patch: bool = True,
            test_types: List[str] = None,
            custom_context: str = "",  # ✅ NEW PARAMETER
            status_callback: Optional[Callable[[str, str], None]] = None
    ) -> TestCaseGenerationResult:
        """
        Task uchun test case'lar yaratish

        Args:
            task_key: JIRA task key
            include_pr: PR'ni hisobga olish
            use_smart_patch: Smart Patch ishlatish
            test_types: Test turlari ['positive', 'negative', 'boundary', ...]
            custom_context: Foydalanuvchidan qo'shimcha ma'lumot (product nomlari, narxlar, etc.)
            status_callback: Status update callback

        Returns:
            TestCaseGenerationResult
        """
        # Status updater (BaseService'dan)
        update_status = self._create_status_updater(status_callback)

        try:
            if not test_types:
                test_types = ['positive', 'negative']

            update_status("info", f"🔍 {task_key} tahlil qilinmoqda...")

            # 1. JIRA dan task olish
            task_details = self.jira.get_task_details(task_key)
            if not task_details:
                return TestCaseGenerationResult(
                    task_key=task_key,
                    task_summary="",
                    success=False,
                    error_message=f"❌ {task_key} topilmadi"
                )

            # 2. TZ va Comment tahlili (TZHelper ishlatamiz)
            tz_content, comment_analysis = TZHelper.format_tz_with_comments(task_details)
            update_status("success", f"✅ TZ: {len(task_details.get('comments', []))} comment")

            # 3. PR ma'lumotlari (PRHelper ishlatamiz - Smart Patch bilan)
            pr_info = None
            pr_details_list = []
            if include_pr:
                pr_info = self.pr_helper.get_pr_full_info(
                    task_key,
                    task_details,
                    status_callback,
                    use_smart_patch=use_smart_patch  # Smart Patch parametri
                )
                if pr_info:
                    update_status("success", f"✅ PR: {pr_info['pr_count']} ta")
                    pr_details_list = pr_info.get('pr_details', [])

            # 4. Overview yaratish (TZHelper ishlatamiz)
            overview = TZHelper.create_task_overview(
                task_details,
                comment_analysis,
                pr_info
            )

            # 5. AI bilan test case'lar yaratish (WITH CUSTOM CONTEXT)
            update_status("progress", "🤖 AI test case'lar yaratmoqda...")

            ai_result = self._generate_with_ai(
                task_key=task_key,
                task_details=task_details,
                tz_content=tz_content,
                comment_analysis=comment_analysis,
                pr_info=pr_info,
                test_types=test_types,
                custom_context=custom_context  # ✅ NEW
            )

            if not ai_result['success']:
                return TestCaseGenerationResult(
                    task_key=task_key,
                    task_summary=task_details['summary'],
                    task_full_details=task_details,
                    task_overview=overview,
                    success=False,
                    error_message=ai_result['error']
                )

            # 6. Test case'larni parse qilish
            test_cases = self._parse_test_cases(ai_result['raw_response'])

            # Statistika
            by_type = {}
            by_priority = {}
            for tc in test_cases:
                by_type[tc.test_type] = by_type.get(tc.test_type, 0) + 1
                by_priority[tc.priority] = by_priority.get(tc.priority, 0) + 1

            update_status("success", f"✅ {len(test_cases)} ta test case yaratildi!")

            return TestCaseGenerationResult(
                task_key=task_key,
                task_summary=task_details['summary'],
                test_cases=test_cases,
                tz_content=tz_content,
                pr_count=pr_info['pr_count'] if pr_info else 0,
                files_changed=pr_info['files_changed'] if pr_info else 0,
                pr_details=pr_details_list,  # PR details for Code Changes tab
                task_full_details=task_details,
                task_overview=overview,
                comment_changes_detected=comment_analysis['has_changes'],
                comment_summary=comment_analysis['summary'],
                comment_details=comment_analysis.get('important_comments', []),
                total_test_cases=len(test_cases),
                by_type=by_type,
                by_priority=by_priority,
                success=True,
                custom_context_used=bool(custom_context)  # ✅ NEW
            )

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return TestCaseGenerationResult(
                task_key=task_key,
                task_summary="",
                success=False,
                error_message=f"❌ {str(e)}"
            )

    def _generate_with_ai(
            self,
            task_key: str,
            task_details: Dict,
            tz_content: str,
            comment_analysis: Dict,
            pr_info: Optional[Dict],
            test_types: List[str],
            custom_context: str = ""  # ✅ NEW
    ) -> Dict:
        """
        AI bilan test case'lar yaratish

        Returns:
            {
                'success': bool,
                'raw_response': str,
                'error': str (if failed)
            }
        """
        try:
            # Prompt yaratish (WITH CUSTOM CONTEXT)
            prompt = self._create_test_case_prompt(
                task_key=task_key,
                task_details=task_details,
                tz_content=tz_content,
                comment_analysis=comment_analysis,
                pr_info=pr_info,
                test_types=test_types,
                custom_context=custom_context  # ✅ NEW
            )

            # Text hajmini tekshirish (BaseService'dan)
            text_info = self._calculate_text_length(prompt)

            if not text_info['within_limit']:
                # Qisqartirish (BaseService'dan)
                prompt = self._truncate_text(prompt)

            # AI chaqirish
            response = self.gemini.analyze(prompt)

            return {
                'success': True,
                'raw_response': response
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"AI xatosi: {str(e)}"
            }

    def _create_test_case_prompt(
            self,
            task_key: str,
            task_details: Dict,
            tz_content: str,
            comment_analysis: Dict,
            pr_info: Optional[Dict],
            test_types: List[str],
            custom_context: str = ""  # ✅ NEW
    ) -> str:
        """
        Test case generation uchun prompt yaratish (WITH CUSTOM CONTEXT)
        """
        # Test types description
        test_types_desc = {
            'positive': 'To\'g\'ri ma\'lumotlar bilan ishlash',
            'negative': 'Noto\'g\'ri ma\'lumotlar, xato holatlar',
            'boundary': 'Limit qiymatlari (min/max)',
            'edge': 'Maxsus/chekka holatlar',
            'integration': 'Tizim integratsiyasi',
            'regression': 'Regression testing'
        }

        types_text = ', '.join([f"{t} ({test_types_desc.get(t, t)})" for t in test_types])

        prompt = f"""
**VAZIFA:** JIRA task uchun QA test case'lar yaratish (O'ZBEK TILIDA)

═══════════════════════════════════════════════════════════════════════════════
📋 TASK MA'LUMOTLARI
═══════════════════════════════════════════════════════════════════════════════

**Task Key:** {task_key}
**Summary:** {task_details['summary']}
**Type:** {task_details['type']}
**Priority:** {task_details['priority']}

═══════════════════════════════════════════════════════════════════════════════
📝 TEXNIK TOPSHIRIQ (TZ)
═══════════════════════════════════════════════════════════════════════════════

{tz_content}

"""

        # ✅ NEW: CUSTOM CONTEXT SECTION
        if custom_context:
            prompt += f"""
═══════════════════════════════════════════════════════════════════════════════
💬 QO'SHIMCHA MA'LUMOTLAR (FOYDALANUVCHIDAN)
═══════════════════════════════════════════════════════════════════════════════

{custom_context}

⚠️ **MUHIM:** Yuqoridagi qo'shimcha ma'lumotlarni test case'larda ALBATTA ishlatish kerak!
- Product nomlari, narxlar va boshqa ma'lumotlarni test datalarida ishlating
- Chegirmalar, limitlar va maxsus shartlarni test scenario'larda qamrab oling
- Foydalanuvchi aytgan barcha narsalarni hisobga oling

"""

        # Comment analysis
        if comment_analysis['has_changes']:
            prompt += f"""
═══════════════════════════════════════════════════════════════════════════════
⚠️ MUHIM: COMMENT'LARDA O'ZGARISHLAR ANIQLANDI
═══════════════════════════════════════════════════════════════════════════════

{comment_analysis['summary']}

Comment'lardagi o'zgarishlar test case'larda ALBATTA hisobga olinishi kerak!

"""

        # PR info
        if pr_info:
            prompt += f"""
═══════════════════════════════════════════════════════════════════════════════
💻 KOD O'ZGARISHLARI
═══════════════════════════════════════════════════════════════════════════════

- PR'lar: {pr_info['pr_count']} ta
- Fayllar: {pr_info['files_changed']} ta
- Qo'shilgan: +{pr_info['total_additions']} qator
- O'chirilgan: -{pr_info['total_deletions']} qator

Kod o'zgarishlarini hisobga olib test case'lar yarating.

"""

        prompt += f"""
═══════════════════════════════════════════════════════════════════════════════
🎯 TEST CASE TALABLARI
═══════════════════════════════════════════════════════════════════════════════

**Test turlari:** {types_text}

**Har bir test case uchun:**
1. TZ'dagi barcha talablarni qamrab olish
2. Comment'lardagi o'zgarishlarni hisobga olish
3. Kod o'zgarishlarini test qilish
4. Edge case'larni tekshirish
{"5. QO'SHIMCHA MA'LUMOTLARDAGI barcha shartlarni test qilish" if custom_context else ""}

**Sifat talablari:**
1. Har bir test case TO'LIQ va ANIQ bo'lishi kerak
2. Steps BATAFSIL (har bir qadam alohida)
3. Expected result ANIQ (nima kutiladi)
4. O'zbek tilida, tushunarli
5. Haqiqiy test scenario'lar (copy-paste emas!)
{"6. QO'SHIMCHA MA'LUMOTLARDAGI product nomlari va narxlarni ishlatish" if custom_context else ""}

═══════════════════════════════════════════════════════════════════════════════
📊 JAVOB FORMATI (JSON)
═══════════════════════════════════════════════════════════════════════════════

Javobni FAQAT JSON formatda bering, boshqa hech narsa yo'q:

```json
{{
  "test_cases": [
    {{
      "id": "TC-001",
      "title": "Test case nomi (qisqa va aniq)",
      "description": "Test case tavsifi (nima test qilinadi)",
      "preconditions": "Boshlang'ich shartlar (system holati, ma'lumotlar)",
      "steps": [
        "1. Birinchi qadam (batafsil)",
        "2. Ikkinchi qadam (batafsil)",
        "3. Uchinchi qadam (batafsil)"
      ],
      "expected_result": "Kutilayotgan natija (aniq)",
      "test_type": "positive/negative/boundary/edge",
      "priority": "High/Medium/Low",
      "severity": "Critical/Major/Minor",
      "tags": ["tag1", "tag2"]
    }}
  ]
}}
```

**MUHIM:**
- Kamida {len(test_types) * 3} ta test case yarating
- Har bir test type uchun kamida 3 ta test case
- JSON to'g'ri formatda bo'lishi kerak
- Steps ro'yxat (list) bo'lishi kerak
- Har bir step alohida element
{"- QO'SHIMCHA MA'LUMOTLARDAGI ma'lumotlarni test data sifatida ishlating" if custom_context else ""}

Endi {len(test_types)} xil test ({types_text}) uchun test case'lar yarating!
"""

        return prompt

    def _parse_test_cases(self, raw_response: str) -> List[TestCase]:
        """
        AI javobidan test case'larni parse qilish

        Args:
            raw_response: AI'dan kelgan javob

        Returns:
            List[TestCase]: Parse qilingan test case'lar
        """
        test_cases = []

        try:
            # JSON'ni extract qilish
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                print("JSON topilmadi!")
                return []

            json_str = raw_response[json_start:json_end]

            # Parse
            data = json.loads(json_str)

            # Test case'larni yaratish
            for tc_data in data.get('test_cases', []):
                try:
                    test_case = TestCase(
                        id=tc_data.get('id', 'TC-XXX'),
                        title=tc_data.get('title', ''),
                        description=tc_data.get('description', ''),
                        preconditions=tc_data.get('preconditions', ''),
                        steps=tc_data.get('steps', []),
                        expected_result=tc_data.get('expected_result', ''),
                        test_type=tc_data.get('test_type', 'positive'),
                        priority=tc_data.get('priority', 'Medium'),
                        severity=tc_data.get('severity', 'Major'),
                        tags=tc_data.get('tags', [])
                    )
                    test_cases.append(test_case)
                except Exception as e:
                    print(f"Test case parse xatosi: {e}")
                    continue

        except json.JSONDecodeError as e:
            print(f"JSON parse xatosi: {e}")
            print(f"Response: {raw_response[:500]}")
        except Exception as e:
            print(f"Parse xatosi: {e}")

        return test_cases