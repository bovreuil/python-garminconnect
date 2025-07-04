#!/usr/bin/env python3
"""
Initialize new schema and run migration.
"""

from database import init_database
from migrate_schema import migrate_schema

def main():
    """Initialize new schema and migrate existing data."""
    print("Initializing new database schema...")
    init_database()
    
    print("Running migration...")
    migrate_schema()
    
    print("Schema migration completed!")

if __name__ == "__main__":
    main() 