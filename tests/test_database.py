import sys
import unittest
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database.connection import get_engine


def run_database_checks() -> None:
    engine = get_engine()

    print("=" * 60)
    print("SMART RETAIL - POSTGRESQL DATABASE TEST")
    print("=" * 60)

    try:
        # --------------------------------------------------
        # 1. Test PostgreSQL connection
        # --------------------------------------------------
        print("\n[1] Testing PostgreSQL connection...")

        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            value = result.scalar()

        if value == 1:
            print("SUCCESS: PostgreSQL connection works.")
        else:
            raise AssertionError("SELECT 1 returned an unexpected value.")

        # --------------------------------------------------
        # 2. Check PostgreSQL version
        # --------------------------------------------------
        print("\n[2] Checking PostgreSQL version...")

        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT version()")
            )

            version = result.scalar()

        print(version)

        # --------------------------------------------------
        # 3. Check current database
        # --------------------------------------------------
        print("\n[3] Checking current database...")

        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT current_database()")
            )

            database_name = result.scalar()

        print(f"Database: {database_name}")

        # --------------------------------------------------
        # 4. Check current schema
        # --------------------------------------------------
        print("\n[4] Checking current schema...")

        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT current_schema()")
            )

            schema_name = result.scalar()

        print(f"Schema: {schema_name}")

        # --------------------------------------------------
        # 5. List tables
        # --------------------------------------------------
        print("\n[5] Checking database tables...")

        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
            )

            tables = [row[0] for row in result]

        if not tables:
            raise AssertionError("No tables found in public schema.")

        print("Tables found:")

        for table in tables:
            print(f"  - {table}")

        # --------------------------------------------------
        # 6. Check core SmartRetail tables
        # --------------------------------------------------
        print("\n[6] Checking core SmartRetail tables...")

        expected_tables = {
            "customers",
            "products",
            "sales",
            "sale_items",
            "inventory",
            "stores",
        }

        actual_tables = set(tables)

        missing_tables = expected_tables - actual_tables

        if missing_tables:
            print("FAILED: Missing tables:")

            for table in sorted(missing_tables):
                print(f"  - {table}")

            raise AssertionError(
                f"Missing core SmartRetail tables: {sorted(missing_tables)}"
            )

        print("SUCCESS: Core SmartRetail tables exist.")

        # --------------------------------------------------
        # 7. Test INSERT + SELECT + ROLLBACK
        # --------------------------------------------------
        print("\n[7] Testing INSERT, SELECT and ROLLBACK...")

        with engine.begin() as connection:

            connection.execute(text("DROP TABLE IF EXISTS database_test"))
            connection.execute(
                text("""
                    CREATE TEMPORARY TABLE database_test (
                        id SERIAL PRIMARY KEY,
                        message TEXT NOT NULL
                    ) ON COMMIT DROP
                """)
            )

            connection.execute(
                text("""
                    INSERT INTO database_test (message)
                    VALUES (:message)
                """),
                {
                    "message": "SmartRetail PostgreSQL test"
                }
            )

            result = connection.execute(
                text("""
                    SELECT id, message
                    FROM database_test
                    ORDER BY id DESC
                    LIMIT 1
                """)
            )

            row = result.fetchone()

        if row is None:
            print("FAILED: Could not retrieve inserted test data.")
            raise AssertionError("Could not retrieve inserted test data.")

        print(f"Retrieved ID: {row.id}")
        print(f"Retrieved message: {row.message}")

        if row.message != "SmartRetail PostgreSQL test":
            print("FAILED: Retrieved data does not match.")
            raise AssertionError("Retrieved data does not match.")

        print("SUCCESS: INSERT and SELECT work.")

        # --------------------------------------------------
        # 8. Test PostgreSQL transaction
        # --------------------------------------------------
        print("\n[8] Testing transaction support...")

        with engine.connect() as connection:

            transaction = connection.begin()

            try:
                connection.execute(
                    text("""
                        SELECT 1
                    """)
                )

                transaction.rollback()

                print("SUCCESS: Transaction rollback works.")

            except Exception:
                transaction.rollback()
                raise

        # --------------------------------------------------
        # FINAL RESULT
        # --------------------------------------------------
        print("\n" + "=" * 60)
        print("DATABASE TEST PASSED")
        print("=" * 60)

        print("\nYour application can successfully:")
        print("  - Connect to Supabase PostgreSQL")
        print("  - Execute PostgreSQL queries")
        print("  - Read database metadata")
        print("  - See your SmartRetail tables")
        print("  - Insert data")
        print("  - Retrieve data")
        print("  - Use transactions")

    except Exception as error:

        print("\n" + "=" * 60)
        print("DATABASE TEST FAILED")
        print("=" * 60)

        print("\nError type:")
        print(type(error).__name__)

        print("\nError message:")
        print(error)
        raise


class DatabaseSmokeTest(unittest.TestCase):
    """Verify connectivity and the migrated SmartRetail schema."""

    def test_database_checks(self) -> None:
        run_database_checks()


if __name__ == "__main__":
    run_database_checks()