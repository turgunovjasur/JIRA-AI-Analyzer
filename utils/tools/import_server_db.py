#!/usr/bin/env python3
"""
Server DB Import Tool

Serverdan olingan processing.db ni import qilish va validate qilish.
Agar DB buzilgan bo'lsa, dump/restore qiladi.

Author: JASUR TURGUNOV
Version: 1.0
"""
import sqlite3
import sys
import os
import shutil
from datetime import datetime

# Project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def log(emoji, color, message):
    """Colorful log"""
    print(f"{color}{emoji} {message}{RESET}")


def validate_db(db_path):
    """
    DB faylni validate qilish

    Returns:
        tuple: (is_valid, error_message)
    """
    # 1. Fayl mavjudmi?
    if not os.path.exists(db_path):
        return False, "Fayl topilmadi"

    # 2. Fayl hajmi
    size = os.path.getsize(db_path)
    if size == 0:
        return False, "Fayl bo'sh (0 bytes)"

    # 3. SQLite header
    try:
        with open(db_path, 'rb') as f:
            header = f.read(16)
            if not header.startswith(b'SQLite format 3'):
                return False, f"SQLite header noto'g'ri: {header[:16]}"
    except Exception as e:
        return False, f"Faylni o'qishda xato: {e}"

    # 4. Database integrity
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Integrity check
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()[0]

        if result != "ok":
            conn.close()
            return False, f"Integrity check failed: {result}"

        # Tables check
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]

        if 'task_processing' not in tables:
            conn.close()
            return False, "task_processing jadvali topilmadi"

        # Count check
        cursor.execute("SELECT COUNT(*) FROM task_processing;")
        count = cursor.fetchone()[0]

        conn.close()

        log("✅", GREEN, f"DB valid: {count} ta task")
        return True, None

    except sqlite3.DatabaseError as e:
        return False, f"SQLite xato: {e}"
    except Exception as e:
        return False, f"Kutilmagan xato: {e}"


def backup_current_db():
    """Hozirgi DB ni backup qilish"""
    # Project root/data papkasi
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, 'data')
    current_db = os.path.join(data_dir, 'processing.db')

    if not os.path.exists(current_db):
        log("ℹ️", BLUE, "Hozirgi DB yo'q, backup kerak emas")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(data_dir, f"processing_backup_{timestamp}.db")

    shutil.copy2(current_db, backup_path)
    log("💾", GREEN, f"Backup: {backup_path}")
    return backup_path


def dump_and_restore(source_db, target_db):
    """
    Buzilgan DB ni dump qilish va qayta restore qilish

    Bu metod DB buzilgan bo'lsa ishlatiladi.
    SQLite dump → SQL script → yangi DB
    """
    log("🔧", YELLOW, "DB dump va restore boshlanmoqda...")

    try:
        # 1. Dump to SQL
        dump_file = "/tmp/db_dump.sql"

        conn = sqlite3.connect(source_db)
        with open(dump_file, 'w') as f:
            for line in conn.iterdump():
                f.write(f'{line}\n')
        conn.close()

        log("✅", GREEN, f"Dump yaratildi: {dump_file}")

        # 2. Create new DB from dump
        if os.path.exists(target_db):
            os.remove(target_db)

        conn = sqlite3.connect(target_db)
        with open(dump_file, 'r') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()

        log("✅", GREEN, f"Yangi DB yaratildi: {target_db}")

        # 3. Validate new DB
        is_valid, error = validate_db(target_db)
        if not is_valid:
            return False, f"Restore failed: {error}"

        return True, None

    except Exception as e:
        return False, f"Dump/Restore xato: {e}"


def import_server_db(server_db_path, force=False):
    """
    Serverdan olingan DB ni import qilish

    Args:
        server_db_path: Serverdan olingan DB fayl yo'li
        force: Validation'siz import qilish

    Returns:
        bool: Success
    """
    log("📦", BLUE, "Server DB Import Tool")
    print("=" * 60)

    # 1. Source DB validate
    log("🔍", BLUE, f"Source DB tekshirilmoqda: {server_db_path}")
    is_valid, error = validate_db(server_db_path)

    if not is_valid:
        log("❌", RED, f"Source DB noto'g'ri: {error}")

        if not force:
            log("ℹ️", BLUE, "Dump/Restore rejimida qayta urinilmoqda...")

            # Try dump/restore
            temp_db = "/tmp/restored.db"
            success, error = dump_and_restore(server_db_path, temp_db)

            if not success:
                log("❌", RED, f"Dump/Restore failed: {error}")
                return False

            server_db_path = temp_db
            log("✅", GREEN, "DB restore qilindi!")

    # 2. Backup current DB
    log("💾", BLUE, "Hozirgi DB backup qilinmoqda...")
    backup_path = backup_current_db()

    # 3. Import
    # Project root/data papkasi
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, 'data')
    os.makedirs(data_dir, exist_ok=True)
    target_db = os.path.join(data_dir, 'processing.db')

    log("📥", BLUE, f"Import: {server_db_path} → {target_db}")

    try:
        shutil.copy2(server_db_path, target_db)
        log("✅", GREEN, "Import muvaffaqiyatli!")

        # 4. Validate imported DB
        is_valid, error = validate_db(target_db)
        if not is_valid:
            log("❌", RED, f"Imported DB noto'g'ri: {error}")

            # Restore backup
            if backup_path:
                log("🔄", YELLOW, "Backup qaytarilmoqda...")
                shutil.copy2(backup_path, target_db)
                log("✅", GREEN, "Backup qaytarildi")

            return False

        # 5. Statistics
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM task_processing;")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT task_status, COUNT(*) FROM task_processing GROUP BY task_status;")
        stats = cursor.fetchall()

        conn.close()

        print("\n" + "=" * 60)
        log("📊", GREEN, "STATISTIKA:")
        log("🎯", BLUE, f"  Jami tasklar: {total}")
        for status, count in stats:
            log("  •", BLUE, f"{status}: {count}")

        print("=" * 60)
        log("✅", GREEN, "Import tugadi!")

        if backup_path:
            log("ℹ️", BLUE, f"Backup: {backup_path}")

        return True

    except Exception as e:
        log("❌", RED, f"Import xato: {e}")

        # Restore backup
        if backup_path:
            log("🔄", YELLOW, "Backup qaytarilmoqda...")
            shutil.copy2(backup_path, target_db)

        return False


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(f"""
{BLUE}╔════════════════════════════════════════════════════════════╗
║           SERVER DB IMPORT TOOL                            ║
╚════════════════════════════════════════════════════════════╝{RESET}

{GREEN}Usage:{RESET}
    python3 utils/import_server_db.py <server_db_path>

{GREEN}Examples:{RESET}
    # Serverdan olingan DB ni import qilish
    python3 utils/import_server_db.py ~/Downloads/processing.db

    # Desktop'dan import qilish
    python3 utils/import_server_db.py ~/Desktop/processing.db

    # Force mode (validation'siz)
    python3 utils/import_server_db.py ~/Downloads/processing.db --force

{GREEN}Features:{RESET}
    ✅ DB validation (integrity check)
    ✅ Automatic backup
    ✅ Dump/Restore (buzilgan DB uchun)
    ✅ Statistics
    ✅ Rollback on error

{YELLOW}Note:{RESET}
    Agar DB buzilgan bo'lsa, avtomatik dump/restore qiladi.
    Hozirgi DB avtomatik backup qilinadi: data/processing_backup_*.db
        """)
        sys.exit(1)

    server_db_path = sys.argv[1]
    force = "--force" in sys.argv

    if not os.path.exists(server_db_path):
        log("❌", RED, f"Fayl topilmadi: {server_db_path}")
        sys.exit(1)

    success = import_server_db(server_db_path, force=force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
