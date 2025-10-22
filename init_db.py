#!/usr/bin/env python3
"""
Brain Hair Database Initialization Script

Interactively configures the database connection and initializes the schema.
"""

import os
import sys
import configparser
from getpass import getpass
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.flaskenv')

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db
from models import ChatSession, ChatMessage


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
    Tests the database connection with the provided credentials.

    Args:
        creds: Dictionary with database credentials

    Returns:
        Tuple of (connection_string, success_boolean)
    """
    from urllib.parse import quote_plus

    print("\n" + "-"*60)
    print("Testing database connection...")
    print("-"*60)

    # Escape special characters in password
    escaped_password = quote_plus(creds['password'])
    conn_string = f"postgresql://{creds['user']}:{escaped_password}@{creds['host']}:{creds['port']}/{creds['dbname']}"

    try:
        engine = create_engine(conn_string)
        with engine.connect() as connection:
            print("\n✅ Database connection successful!")
            return conn_string, True
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nMake sure you have:")
        print(f"  1. Created the database: CREATE DATABASE {creds['dbname']};")
        print(f"  2. Created the user: CREATE USER {creds['user']} WITH PASSWORD 'your_password';")
        print(f"  3. Granted permissions: GRANT ALL PRIVILEGES ON DATABASE {creds['dbname']} TO {creds['user']};")
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


def init_db():
    """
    Main initialization function.

    Interactively configures and initializes the Brain Hair database.
    """
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

        with app.app_context():
            # Create all tables
            db.create_all()

            # Verify tables were created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            print(f"\n✅ Database schema initialized successfully!")
            print(f"\nCreated tables:")
            for table in tables:
                print(f"  - {table}")

            # Show some helpful info
            print(f"\n📊 Database Info:")
            print(f"  Database: {creds['dbname']}")
            print(f"  User: {creds['user']}")
            print(f"  Host: {creds['host']}:{creds['port']}")
            print(f"  Tables: {len(tables)}")

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
    try:
        init_db()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
