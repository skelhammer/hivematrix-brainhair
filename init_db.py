#!/usr/bin/env python3
"""
Brain Hair Database Initialization Script

Interactively configures the database connection and initializes the schema.
"""

import os
import sys
import argparse
import configparser
import subprocess
from getpass import getpass
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.flaskenv')

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# NOTE: We import app later in functions to allow config file to be created first
# For headless mode, app is imported AFTER config file is written
app = None
db = None

def _import_app():
    """Import app and db after config file exists."""
    global app, db
    if app is None:
        from app import app as flask_app
        from extensions import db as database
        # Import ALL models so SQLAlchemy knows about them
        from models import ChatSession, ChatMessage
        app = flask_app
        db = database
    return app, db


def get_db_credentials(config):
    """
    Prompts the user for PostgreSQL connection details.

    Args:
        config: ConfigParser instance with existing config (if any)

    Returns:
        Dictionary with database credentials
    """
    print("\n" + "="*60)
    print("Brain Hair - Database Configuration")
    print("="*60)
    print("\nThis script will set up the PostgreSQL database for Brain Hair.")
    print("You need to create the database and user in PostgreSQL first.\n")

    # Load existing or use defaults
    db_details = {
        'host': config.get('database', 'db_host', fallback='localhost'),
        'port': config.get('database', 'db_port', fallback='5432'),
        'user': config.get('database', 'db_user', fallback='brainhair_user'),
        'dbname': config.get('database', 'db_name', fallback='brainhair_db')
    }

    print("Current/Default values are shown in brackets.\n")

    host = input(f"PostgreSQL Host [{db_details['host']}]: ") or db_details['host']
    port = input(f"PostgreSQL Port [{db_details['port']}]: ") or db_details['port']
    dbname = input(f"Database Name [{db_details['dbname']}]: ") or db_details['dbname']
    user = input(f"Database User [{db_details['user']}]: ") or db_details['user']
    password = getpass("Database Password: ")

    if not password:
        print("\n❌ Password is required!")
        sys.exit(1)

    return {
        'host': host,
        'port': port,
        'dbname': dbname,
        'user': user,
        'password': password
    }


def test_db_connection(creds):
    """
    Tests the database connection, automatically creating database if needed.

    Args:
        creds: Dictionary with database credentials

    Returns:
        Tuple of (connection_string, success_boolean)
    """
    from urllib.parse import quote_plus

    print("\n" + "-"*60)
    print("Testing database connection...")
    print("-"*60)

    # First check if database exists using psql (more reliable than SQLAlchemy connection attempt)
    check_cmd = f"sudo -u postgres psql -tAc \"SELECT 1 FROM pg_database WHERE datname='{creds['dbname']}'\""
    try:
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, timeout=5)
        db_exists = "1" in result.stdout
    except Exception:
        # If check fails, assume database doesn't exist and try to create it
        db_exists = False

    # Create database if it doesn't exist
    if not db_exists:
        print(f"\n→ Database '{creds['dbname']}' does not exist. Creating it...")
        create_cmd = f"sudo -u postgres psql -c \"CREATE DATABASE {creds['dbname']} OWNER {creds['user']};\""
        try:
            result = subprocess.run(create_cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✓ Database '{creds['dbname']}' created successfully!")
            else:
                print(f"\n✗ Failed to create database: {result.stderr}", file=sys.stderr)
                print(f"  You may need to create it manually:")
                print(f"  sudo -u postgres psql -c \"CREATE DATABASE {creds['dbname']} OWNER {creds['user']};\"")
                return None, False
        except Exception as e:
            print(f"\n✗ Failed to create database: {e}", file=sys.stderr)
            return None, False

    # Escape special characters in password
    escaped_password = quote_plus(creds['password'])
    conn_string = f"postgresql+psycopg://{creds['user']}:{escaped_password}@{creds['host']}:{creds['port']}/{creds['dbname']}"

    try:
        engine = create_engine(conn_string)
        with engine.connect() as connection:
            print("\n✅ Database connection successful!")
            return conn_string, True
    except OperationalError as e:
        print(f"\n❌ Connection failed: {e}", file=sys.stderr)
        return None, False


def save_config(config_path, creds, conn_string):
    """
    Saves the database configuration to instance/brainhair.conf.

    Args:
        config_path: Path to the config file
        creds: Dictionary with database credentials
        conn_string: Database connection string
    """
    config = configparser.RawConfigParser()

    # Database section
    if not config.has_section('database'):
        config.add_section('database')

    config.set('database', 'connection_string', conn_string)
    config.set('database', 'db_host', creds['host'])
    config.set('database', 'db_port', creds['port'])
    config.set('database', 'db_name', creds['dbname'])
    config.set('database', 'db_user', creds['user'])

    # Write config file
    with open(config_path, 'w') as configfile:
        config.write(configfile)

    print(f"\n✅ Configuration saved to: {config_path}")


def migrate_schema():
    """
    Intelligently migrates database schema without losing data.

    This function:
    1. Inspects existing tables and columns
    2. Compares with models defined in models.py
    3. Adds missing columns (with defaults)
    4. Creates missing tables
    5. Does NOT drop columns or tables (safe for production)
    """
    print("\n" + "="*80)
    print("DATABASE SCHEMA MIGRATION")
    print("="*80)

    app, db = _import_app()
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        print(f"\nFound {len(existing_tables)} existing tables in database")

        # Get all tables defined in models
        model_tables = db.metadata.tables

        # Track changes
        tables_created = []
        columns_added = []

        # Create tables in dependency order (association tables last)
        # First, create all base tables (no foreign keys to other app tables)
        base_tables = []
        association_tables = []

        for table_name, table in model_tables.items():
            # Association tables typically have multiple foreign keys and no primary key of their own
            # or have 'link' in the name
            if 'link' in table_name.lower() or len([c for c in table.columns if c.foreign_keys]) >= 2:
                association_tables.append((table_name, table))
            else:
                base_tables.append((table_name, table))

        # Create base tables first
        for table_name, table in base_tables:
            if table_name not in existing_tables:
                # Table doesn't exist - create it
                print(f"\n→ Creating new table: {table_name}")
                table.create(db.engine)
                tables_created.append(table_name)
            else:
                # Table exists - check for missing columns (below)
                pass

        # Then create association tables
        for table_name, table in association_tables:
            if table_name not in existing_tables:
                # Table doesn't exist - create it
                print(f"\n→ Creating new association table: {table_name}")
                table.create(db.engine)
                tables_created.append(table_name)
            else:
                # Table exists - check for missing columns (below)
                pass

        # Now check all tables for missing columns
        for table_name, table in base_tables + association_tables:
            if table_name in existing_tables:
                # Table exists - check for missing columns
                existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
                model_columns = {col.name for col in table.columns}
                missing_columns = model_columns - existing_columns

                if missing_columns:
                    print(f"\n→ Updating table '{table_name}' - adding {len(missing_columns)} columns:")

                    # Validate table name is a valid identifier
                    import re
                    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
                        print(f"   ✗ Invalid table name format: {table_name}")
                        continue

                    for col_name in missing_columns:
                        # Validate column name is a valid identifier
                        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col_name):
                            print(f"   ✗ Invalid column name format: {col_name}")
                            continue

                        col = table.columns[col_name]
                        col_type = col.type.compile(db.engine.dialect)

                        # Build ALTER TABLE statement
                        nullable = "NULL" if col.nullable else "NOT NULL"
                        default = ""

                        # Add default value if specified
                        if col.default is not None:
                            if hasattr(col.default, 'arg'):
                                # Column default (e.g., default=True)
                                default_val = col.default.arg
                                if isinstance(default_val, str):
                                    default = f"DEFAULT '{default_val}'"
                                elif isinstance(default_val, bool):
                                    default = f"DEFAULT {str(default_val).upper()}"
                                else:
                                    default = f"DEFAULT {default_val}"

                        # For NOT NULL columns without default, make them nullable for migration
                        if not col.nullable and not default:
                            nullable = "NULL"
                            print(f"   ⚠ Column '{col_name}' is NOT NULL but has no default - making nullable for safety")

                        # Use quoted identifiers for safety
                        sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type} {default} {nullable}'

                        try:
                            with db.engine.connect() as conn:
                                conn.execute(text(sql))
                                conn.commit()
                            print(f"   ✓ Added column: {col_name} ({col_type})")
                            columns_added.append(f"{table_name}.{col_name}")
                        except Exception as e:
                            print(f"   ✗ Failed to add column {col_name}: {e}")

        # Summary
        print("\n" + "="*80)
        print("MIGRATION SUMMARY")
        print("="*80)

        if tables_created:
            print(f"\n✓ Created {len(tables_created)} new table(s):")
            for t in tables_created:
                print(f"  - {t}")
        else:
            print("\n• No new tables created")

        if columns_added:
            print(f"\n✓ Added {len(columns_added)} new column(s):")
            for c in columns_added:
                print(f"  - {c}")
        else:
            print("\n• No new columns added")

        if not tables_created and not columns_added:
            print("\n✓ Schema is up to date - no changes needed")

        print("\n" + "="*80)


def init_db_headless(db_host, db_port, db_name, db_user, db_password, migrate_only=False):
    """Non-interactive database initialization for automated installation."""
    from urllib.parse import quote_plus

    print("\n" + "="*80)
    print("BRAINHAIR DATABASE INITIALIZATION (HEADLESS MODE)")
    print("="*80)

    # Determine instance path without importing app yet
    script_dir = os.path.dirname(os.path.abspath(__file__))
    instance_path = os.path.join(script_dir, 'instance')
    os.makedirs(instance_path, exist_ok=True)
    config_path = os.path.join(instance_path, 'brainhair.conf')

    # Build connection string
    escaped_password = quote_plus(db_password)
    conn_string = f"postgresql+psycopg://{db_user}:{escaped_password}@{db_host}:{db_port}/{db_name}"

    # Test connection
    print(f"\n→ Testing database connection to {db_host}:{db_port}/{db_name}...")
    try:
        engine = create_engine(conn_string)
        with engine.connect() as connection:
            print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Connection failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Save configuration
    creds = {
        'host': db_host,
        'port': db_port,
        'dbname': db_name,
        'user': db_user,
        'password': db_password
    }
    save_config(config_path, creds, conn_string)

    # Run schema migration
    migrate_schema()

    print("\n" + "="*80)
    print(" ✓ BrainHair Initialization Complete!")
    print("="*80)


def init_db():
    """
    Main initialization function.

    Interactively configures and initializes the Brain Hair database.
    """
    app, db = _import_app()
    # Ensure instance directory exists
    instance_path = app.instance_path
    os.makedirs(instance_path, exist_ok=True)

    config_path = os.path.join(instance_path, 'brainhair.conf')

    # Load existing config if it exists
    config = configparser.RawConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
        print(f"\n📄 Found existing configuration: {config_path}")
    else:
        print(f"\n📝 Creating new configuration: {config_path}")

    # Get database credentials
    while True:
        creds = get_db_credentials(config)
        conn_string, success = test_db_connection(creds)

        if success:
            # Save configuration
            save_config(config_path, creds, conn_string)
            break
        else:
            retry = input("\n🔄 Retry connection? (y/n): ")
            if retry.lower() != 'y':
                print("\n❌ Database configuration aborted.")
                sys.exit(1)

    # Initialize database schema
    print("\n" + "-"*60)
    print("Initializing database schema...")
    print("-"*60)

    try:
        # Update app config with new connection string
        app.config['SQLALCHEMY_DATABASE_URI'] = conn_string

        # Run schema migration (replaces db.create_all() - handles both creation and updates)
        migrate_schema()

        print(f"\n📊 Database Info:")
        print(f"  Database: {creds['dbname']}")
        print(f"  User: {creds['user']}")
        print(f"  Host: {creds['host']}:{creds['port']}")

    except Exception as e:
        print(f"\n❌ Failed to initialize database schema: {e}")
        sys.exit(1)

    print("\n" + "="*60)
    print("✅ Brain Hair database setup complete!")
    print("="*60)
    print("\nYou can now start the Brain Hair service:")
    print("  source pyenv/bin/activate")
    print("  python run.py")
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Initialize BrainHair database schema',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Non-interactive mode for automated installation'
    )
    parser.add_argument(
        '--db-host',
        type=str,
        default='localhost',
        help='Database host (default: localhost)'
    )
    parser.add_argument(
        '--db-port',
        type=str,
        default='5432',
        help='Database port (default: 5432)'
    )
    parser.add_argument(
        '--db-name',
        type=str,
        default='brainhair_db',
        help='Database name (default: brainhair_db)'
    )
    parser.add_argument(
        '--db-user',
        type=str,
        default='brainhair_user',
        help='Database user (default: brainhair_user)'
    )
    parser.add_argument(
        '--db-password',
        type=str,
        help='Database password (required for headless mode)'
    )
    parser.add_argument(
        '--migrate-only',
        action='store_true',
        help='Only run migrations on existing database'
    )

    args = parser.parse_args()

    try:
        if args.headless:
            if not args.db_password:
                print("ERROR: --db-password is required for headless mode", file=sys.stderr)
                sys.exit(1)

            init_db_headless(
                db_host=args.db_host,
                db_port=args.db_port,
                db_name=args.db_name,
                db_user=args.db_user,
                db_password=args.db_password,
                migrate_only=args.migrate_only
            )
        else:
            init_db()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
