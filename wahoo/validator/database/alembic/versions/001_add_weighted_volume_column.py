"""Wipe database and recreate schema with weighted_volume support

Revision ID: 001_add_weighted_volume
Revises: 
Create Date: 2026-02-02

WARNING: This is a DESTRUCTIVE migration that drops ALL tables and recreates
the schema from scratch. All existing data (miners, performance_snapshots, 
scoring_runs, validation_cache) will be PERMANENTLY DELETED.

This migration:
1. Drops all existing tables
2. Recreates the schema from schema.sql with weighted_volume column support
3. Resets all EMA scores to start fresh with the new v2 API metrics

Run with: alembic upgrade head
"""

import os
from pathlib import Path

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001_add_weighted_volume"
down_revision = None
branch_labels = None
depends_on = None


# Tables to drop in order (respecting foreign key constraints)
TABLES_TO_DROP = [
    "scoring_runs", 
    "performance_snapshots",
    "miners",
]


def upgrade() -> None:
    """
    DESTRUCTIVE: Drop all tables and recreate schema from scratch.
    
    This ensures a clean slate for the v2 API migration with weighted_volume.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    print("\n" + "=" * 60)
    print("WARNING: DESTRUCTIVE MIGRATION - WIPING ALL DATA")
    print("=" * 60)
    
    # Drop existing tables
    for table in TABLES_TO_DROP:
        if table in existing_tables:
            print(f"Dropping table: {table}")
            op.drop_table(table)
        else:
            print(f"Table '{table}' does not exist, skipping drop.")
    
    # Also drop alembic_version tracking to allow clean re-run if needed
    # (We'll let alembic recreate it)
    
    # Load and execute schema.sql to recreate all tables
    schema_path = Path(__file__).parent.parent.parent / "schema.sql"
    
    if not schema_path.exists():
        raise FileNotFoundError(
            f"schema.sql not found at {schema_path}. "
            "Cannot recreate database schema."
        )
    
    print(f"\nRecreating schema from: {schema_path}")
    
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    
    # Execute schema SQL statements
    # Split by semicolons and execute each statement
    for statement in schema_sql.split(";"):
        statement = statement.strip()
        if statement and not statement.startswith("--"):
            # Skip PRAGMA statements as they may not work in all contexts
            if not statement.upper().startswith("PRAGMA"):
                conn.execute(sa.text(statement))
    
    print("\n" + "=" * 60)
    print("Schema recreated successfully with weighted_volume support!")
    print("All EMA scores have been reset. Scores will rebuild from scratch.")
    print("=" * 60 + "\n")


def downgrade() -> None:
    """
    Downgrade is not supported for this destructive migration.
    
    To restore data, you must restore from a backup taken before the migration.
    """
    raise NotImplementedError(
        "Downgrade not supported for destructive migration. "
        "Restore from backup if needed."
    )
