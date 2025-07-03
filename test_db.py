#!/usr/bin/env python3
"""
Database testing script to catch issues before deployment.
"""
import os
import sys
from datetime import datetime
import psycopg2.extras

# Set test database URL
os.environ["DATABASE_URL"] = "postgresql://naman@localhost/stockalerts_test"

try:
    from db_manager import DatabaseManager
    from app import app
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_database_connection():
    """Test basic database connection."""
    print("🔍 Testing database connection...")
    try:
        db = DatabaseManager()
        print("✅ Database connection successful")
        return db
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None


def test_migrations(db):
    """Test that migrations run correctly."""
    print("🔍 Testing migrations...")
    try:
        # Migrations should have run during DatabaseManager init
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
            )
            table_count = cursor.fetchone()[0]
            print(f"✅ Migrations successful - {table_count} tables created")
            return True
    except Exception as e:
        print(f"❌ Migration test failed: {e}")
        return False


def test_basic_operations(db):
    """Test basic CRUD operations."""
    print("🔍 Testing basic operations...")
    try:
        # Test user operations
        success = db.add_user("test_user", "Test User")
        if not success:
            raise Exception("Failed to add user")

        # Test watchlist operations
        success, error = db.add_to_watchlist("test_user", "AAPL")
        if not success:
            raise Exception(f"Failed to add to watchlist: {error}")

        # Test cache operations
        success = db.update_stock_cache("AAPL", 150.0, 145.0, '{"test": "data"}')
        if not success:
            raise Exception("Failed to update cache")

        print("✅ Basic operations successful")
        return True
    except Exception as e:
        print(f"❌ Basic operations failed: {e}")
        return False


def test_admin_panel_queries(db):
    """Test admin panel database queries."""
    print("🔍 Testing admin panel queries...")
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Test each query from admin panel
            queries = [
                "SELECT * FROM users",
                "SELECT * FROM watchlist_items ORDER BY user_id, symbol",
                "SELECT * FROM alert_history ORDER BY sent_at DESC LIMIT 50",
                "SELECT * FROM stock_cache ORDER BY last_check DESC",
                "SELECT * FROM config WHERE key != 'telegram_token'",
            ]

            for query in queries:
                cursor.execute(query)
                results = cursor.fetchall()
                print(f"  ✅ Query successful: {query[:30]}... ({len(results)} rows)")

        print("✅ Admin panel queries successful")
        return True
    except Exception as e:
        print(f"❌ Admin panel queries failed: {e}")
        return False


def test_flask_app():
    """Test Flask app startup."""
    print("🔍 Testing Flask app startup...")
    try:
        with app.test_client() as client:
            # Test health endpoint
            response = client.get("/health")
            if response.status_code == 200:
                print("✅ Flask app startup successful")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Flask app test failed: {e}")
        return False


def test_data_types():
    """Test PostgreSQL vs SQLite data type differences."""
    print("🔍 Testing data type compatibility...")
    try:
        db = DatabaseManager()
        with db._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Test that we get dict-like objects, not tuples
            cursor.execute("SELECT * FROM config LIMIT 1")
            result = cursor.fetchone()

            if result is None:
                print("  ⚠️  No config data found, but query structure is correct")
            else:
                # Try to access by key (should work with RealDictCursor)
                test_key = result["key"]
                print(f"  ✅ Dictionary access works: {test_key}")

        print("✅ Data type compatibility successful")
        return True
    except Exception as e:
        print(f"❌ Data type test failed: {e}")
        return False


def cleanup_test_data(db):
    """Clean up test data."""
    print("🔍 Cleaning up test data...")
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watchlist_items WHERE user_id = 'test_user'")
            cursor.execute("DELETE FROM users WHERE id = 'test_user'")
            cursor.execute("DELETE FROM stock_cache WHERE symbol = 'AAPL'")
            conn.commit()
        print("✅ Cleanup successful")
    except Exception as e:
        print(f"⚠️  Cleanup failed: {e}")


def main():
    """Run all tests."""
    print("=" * 50)
    print("🚀 Database Testing Script")
    print("=" * 50)

    # Test database connection
    db = test_database_connection()
    if not db:
        print("\n❌ Cannot continue without database connection")
        sys.exit(1)

    # Run all tests
    tests = [
        (test_migrations, db),
        (test_basic_operations, db),
        (test_admin_panel_queries, db),
        (test_flask_app,),
        (test_data_types,),
    ]

    passed = 0
    total = len(tests)

    for test_func, *args in tests:
        if test_func(*args):
            passed += 1
        print()

    # Cleanup
    cleanup_test_data(db)

    # Results
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed! Safe to deploy.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Fix issues before deploying.")
        sys.exit(1)


if __name__ == "__main__":
    main()
