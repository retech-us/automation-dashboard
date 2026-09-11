#!/usr/bin/env python3
"""
Database initialization script
Creates PostgreSQL database and runs migrations
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import Base, db_manager, ProjectSettings
from sqlalchemy import text, inspect


def init_database(database_url=None):
    """Initialize database with schema"""
    if database_url is None:
        # Read from environment or use default
        database_url = os.getenv(
            'DATABASE_URL',
            'postgresql://automation_user:automation_password@localhost:5432/automation_dashboard'
        )

    print(f"Initializing database: {database_url}")

    # Initialize manager with database URL
    db_manager.database_url = database_url
    db_manager.initialize()

    print("✓ Database schema created successfully")

    # Create default project settings if not exists
    session = db_manager.get_session()
    try:
        existing = session.query(ProjectSettings).filter_by(
            jira_instance_url='https://retech.atlassian.net'
        ).first()

        if not existing:
            default_settings = ProjectSettings(
                jira_instance_url='https://retech.atlassian.net',
                project_key='REB3',
                test_case_issue_type='Story',
                auto_sync_enabled=True,
                notification_enabled=True
            )
            session.add(default_settings)
            session.commit()
            print("✓ Default project settings created")
        else:
            print("✓ Project settings already exist")

        session.close()
    except Exception as e:
        print(f"✗ Error creating default settings: {e}")
        session.rollback()
        raise


def check_database(database_url=None):
    """Check if database is initialized and show table statistics"""
    if database_url is None:
        database_url = os.getenv(
            'DATABASE_URL',
            'postgresql://automation_user:automation_password@localhost:5432/automation_dashboard'
        )

    print(f"\nChecking database: {database_url}")

    db_manager.database_url = database_url
    db_manager.initialize()

    session = db_manager.get_session()
    try:
        # Get table info
        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()

        print(f"✓ Found {len(tables)} tables:")
        for table in sorted(tables):
            # Get row count
            result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"  - {table}: {count} rows")

        session.close()
        return True

    except Exception as e:
        print(f"✗ Error checking database: {e}")
        return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Initialize Automation Dashboard database')
    parser.add_argument('--url', help='Database URL (postgresql://user:pass@host/dbname)')
    parser.add_argument('--check', action='store_true', help='Check database status instead of init')

    args = parser.parse_args()

    try:
        if args.check:
            check_database(args.url)
        else:
            init_database(args.url)
            print("\n✓ Database initialization complete!")
            print("\nNext steps:")
            print("1. Update DATABASE_URL in your .env or environment")
            print("2. Update server.py to use database models")
            print("3. Run API endpoints to generate and store test cases")
    except Exception as e:
        print(f"\n✗ Failed to initialize database: {e}")
        sys.exit(1)
