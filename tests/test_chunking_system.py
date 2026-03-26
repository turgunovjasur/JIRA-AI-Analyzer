# test_chunking_system.py
"""
Smart Chunking System Test Script

Bu script chunking quality va embedding accuracy'ni test qiladi
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ai.chunking_helper import ChunkingHelper
from utils.database.metadata_helper import MetadataHelper


def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f"🔍 {title}")
    print("=" * 80 + "\n")


def test_multilingual_detection():
    """Test language detection"""
    print_section("TEST 1: Multilingual Detection")

    chunker = ChunkingHelper()

    test_cases = [
        ("Login page error occurred", "en"),
        ("Ошибка на странице входа", "ru"),
        ("Login sahifasida xatolik", "uz"),
        ("Пользователь не может войти в систему", "ru"),
        ("User can't login to system", "en"),
        ("Foydalanuvchi tizimga kira olmayapti", "uz"),
        ("This is mixed Ва это русский", "mixed")
    ]

    results = []
    for text, expected_lang in test_cases:
        detected = chunker._detect_primary_language(text)
        status = "✅" if detected == expected_lang else "❌"
        results.append((status, text[:50], expected_lang, detected))

    # Display results
    print(f"{'Status':<8} {'Text':<55} {'Expected':<10} {'Detected':<10}")
    print("-" * 85)
    for status, text, expected, detected in results:
        print(f"{status:<8} {text:<55} {expected:<10} {detected:<10}")

    success_rate = sum(1 for r in results if r[0] == "✅") / len(results) * 100
    print(f"\n📊 Success Rate: {success_rate:.1f}%")


def test_root_cause_detection():
    """Test root cause extraction"""
    print_section("TEST 2: Root Cause Detection")

    chunker = ChunkingHelper()

    test_cases = [
        {
            'text': """
            Bug Report: Login fails

            Root cause: The authentication service was not properly handling null
            tokens. Due to a race condition in the token validation logic, some
            requests were processed without valid tokens.

            Steps: User clicks login -> Error 500
            """,
            'should_detect': True,
            'language': 'en'
        },
        {
            'text': """
            БАГ: Ошибка авторизации

            Причина: Сервис аутентификации не корректно обрабатывал пустые токены.
            Из-за состояния гонки в логике валидации, некоторые запросы обрабатывались
            без валидных токенов.

            Проблема в том что токен не проверяется.
            """,
            'should_detect': True,
            'language': 'ru'
        },
        {
            'text': """
            BUG: Login xatoligi

            Sabab: Authentication service null tokenlarni to'g'ri handle qilmayapti.
            Token validation logikasida race condition sababli ba'zi requestlar
            valid token'siz process bo'lmoqda.

            Muammo shundaki token tekshirilmayapti.
            """,
            'should_detect': True,
            'language': 'uz'
        },
        {
            'text': """
            Simple description without root cause.
            User can't login. Please fix it.
            """,
            'should_detect': False,
            'language': 'en'
        }
    ]

    print(f"{'Test':<6} {'Language':<10} {'Should Detect':<15} {'Detected':<10} {'Status':<8}")
    print("-" * 60)

    results = []
    for i, test in enumerate(test_cases, 1):
        root_cause = chunker._extract_root_cause(test['text'])
        detected = len(root_cause) > 0
        should_detect = test['should_detect']
        status = "✅" if detected == should_detect else "❌"

        print(f"{i:<6} {test['language']:<10} {str(should_detect):<15} "
              f"{str(detected):<10} {status:<8}")

        if detected:
            print(f"   → Extracted: {root_cause[:100]}...")

        results.append(status == "✅")

    success_rate = sum(results) / len(results) * 100
    print(f"\n📊 Success Rate: {success_rate:.1f}%")


def test_solution_extraction():
    """Test solution extraction"""
    print_section("TEST 3: Solution Extraction")

    chunker = ChunkingHelper()

    test_cases = [
        {
            'text': """
            Solution: Added null check in token validation.
            Fixed by implementing proper token verification before processing requests.
            Changed the authentication flow to validate tokens first.
            """,
            'should_detect': True,
            'language': 'en'
        },
        {
            'text': """
            Решение: Добавлена проверка на null в валидации токена.
            Исправлено путем реализации правильной верификации токена.
            Изменен flow аутентификации для проверки токенов сначала.
            """,
            'should_detect': True,
            'language': 'ru'
        },
        {
            'text': """
            Yechim: Token validation'ga null check qo'shildi.
            Token'ni tekshirish uchun to'g'ri verification qo'shish orqali tuzatildi.
            Authentication flow o'zgartirildi - avval token tekshiriladi.
            """,
            'should_detect': True,
            'language': 'uz'
        }
    ]

    print(f"{'Test':<6} {'Language':<10} {'Detected':<10} {'Status':<8}")
    print("-" * 40)

    results = []
    for i, test in enumerate(test_cases, 1):
        solution = chunker._extract_solution(test['text'])
        detected = len(solution) > 0
        status = "✅" if detected else "❌"

        print(f"{i:<6} {test['language']:<10} {str(detected):<10} {status:<8}")

        if detected:
            print(f"   → Extracted: {solution[:100]}...")

        results.append(status == "✅")

    success_rate = sum(results) / len(results) * 100
    print(f"\n📊 Success Rate: {success_rate:.1f}%")


def test_chunk_creation():
    """Test full chunk creation"""
    print_section("TEST 4: Full Chunk Creation")

    chunker = ChunkingHelper(max_chunk_length=800)

    # Test issue data
    issue_data = {
        'key': 'TEST-123',
        'summary': 'Login authentication fails for users',
        'description': """
        Users are unable to login to the system.

        Root cause: The authentication service was not properly handling null
        tokens. Due to a race condition in the token validation logic, some
        requests were processed without valid tokens.

        Solution: Added null check in token validation and fixed the race
        condition by implementing proper synchronization.
        """,
        'comments': """
        [2025-01-01] Developer: Investigating the issue.
        [2025-01-02] QA: Still failing in production.
        [2025-01-03] Developer: Fixed by adding token validation.
        """,
        'return_reasons': """
        Return #1 [2025-01-02]: TESTING → RETURN TEST (by QA Team)
        Reason: Authentication still fails
        """,
        'status_history': """
        2025-01-01 10:00: None → IN PROGRESS
        2025-01-01 15:00: IN PROGRESS → TESTING
        2025-01-02 09:00: TESTING → RETURN TEST
        2025-01-03 14:00: RETURN TEST → TESTING
        2025-01-03 17:00: TESTING → CLOSED
        """,
        'type': 'Bug',
        'priority': 'High',
        'assignee': 'John Doe',
        'reporter': 'QA Team',
        'components': 'Authentication, Security',
        'labels': 'production, critical',
        'story_points': '5',
        'return_count': 1,
        'pr_status': 'MERGED'
    }

    # Create chunks
    chunks = chunker.create_chunks(issue_data)

    print(f"Total Chunks: {len(chunks)}\n")

    # Display chunks
    chunk_stats = {}
    for i, chunk in enumerate(chunks, 1):
        chunk_type = chunk['type']
        chunk_stats[chunk_type] = chunk_stats.get(chunk_type, 0) + 1

        print(f"Chunk {i}: {chunk_type.upper()}")
        print(f"   Weight: {chunk['weight']}")
        print(f"   Language: {chunk['language']}")
        print(f"   Length: {len(chunk['text'])} chars")
        print(f"   Text: {chunk['text'][:150]}...")
        print()

    # Statistics
    print("📊 Chunk Type Distribution:")
    for chunk_type, count in sorted(chunk_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {chunk_type}: {count}")

    # Check detection
    has_root_cause = any(c['type'] == 'root_cause' for c in chunks)
    has_solution = any(c['type'] == 'solution' for c in chunks)

    print(f"\n🎯 Detection Results:")
    print(f"   • Root Cause: {'✅ Detected' if has_root_cause else '❌ Not detected'}")
    print(f"   • Solution: {'✅ Detected' if has_solution else '❌ Not detected'}")

    # Weighted average simulation
    total_weight = sum(c['weight'] for c in chunks)
    print(f"\n⚖️  Total Weight: {total_weight:.1f}")


def test_metadata_extraction():
    """Test metadata extraction"""
    print_section("TEST 5: Metadata Extraction")

    test_issue = {
        'key': 'TEST-456',
        'type': 'Bug',
        'status': 'Closed',
        'sprint_id': '2842',
        'assignee': 'Developer Name',
        'reporter': 'QA Team',
        'priority': 'High',
        'story_points': 5,
        'created_date': '2025-01-01 10:00:00',
        'resolved_date': '2025-01-05 17:00:00',
        'comments': 'Some comments here',
        'return_count': 2,
        'labels': 'production, critical',
        'components': 'Authentication, API',
        'pr_status': 'MERGED',
        'pr_count': 1,
        'testing_time': '2.5h',
        'linked_issues': 'TEST-123, TEST-789'
    }

    # Extract metadata
    search_meta = MetadataHelper.extract_search_metadata(test_issue)
    display_info = MetadataHelper.extract_display_info(test_issue)

    print("🔍 Search Metadata (for VectorDB filters):")
    for key, value in sorted(search_meta.items()):
        print(f"   • {key}: {value}")

    print("\n📺 Display Info (for UI):")
    for key, value in sorted(display_info.items()):
        print(f"   • {key}: {value}")

    # Test filter creation
    print("\n🎯 Sample Filters:")

    filter1 = MetadataHelper.create_search_filters(
        types=['Bug'],
        statuses=['Closed', 'Done']
    )
    print(f"\n1. Bug search filter:")
    print(f"   {filter1}")

    filter2 = MetadataHelper.create_search_filters(
        types=['Bug'],
        min_return_count=1,
        has_pr=True
    )
    print(f"\n2. Bugs with returns and PR:")
    print(f"   {filter2}")


def test_full_pipeline():
    """Test kelajakda - full embedding pipeline"""
    print_section("TEST 6: Full Pipeline (Placeholder)")

    print("⚠️  Bu test embedding_helper va vectordb_helper ni talab qiladi.")
    print("   Faqat chunking va metadata testlari tugadi.\n")
    print("   Full pipeline test uchun 2_load_sprints_v2.py ni ishlatish kerak.")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("🧪 SMART CHUNKING SYSTEM - TEST SUITE")
    print("=" * 80)

    try:
        test_multilingual_detection()
        test_root_cause_detection()
        test_solution_extraction()
        test_chunk_creation()
        test_metadata_extraction()
        test_full_pipeline()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()