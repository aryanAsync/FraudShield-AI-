"""Tests for Alembic Migrations and Database Schema Integrity."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from app.db.base import Base


def test_alembic_configuration_and_revisions():
    """Verify that Alembic configuration and revision files are valid and discoverable."""
    base_dir = Path(__file__).resolve().parent.parent
    ini_path = base_dir / "alembic.ini"
    assert ini_path.is_file(), f"alembic.ini missing at {ini_path}"

    alembic_cfg = Config(str(ini_path))
    script = ScriptDirectory.from_config(alembic_cfg)

    # Check that revisions exist and head is not None
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected 1 head revision, found {heads}"
    assert heads[0] is not None


def test_metadata_contains_all_required_tables():
    """Verify that Base.metadata defines all required tables including users and case_notes."""
    tables = Base.metadata.tables.keys()
    assert "users" in tables
    assert "transactions" in tables
    assert "predictions" in tables
    assert "investigation_cases" in tables
    assert "case_notes" in tables
    assert "audit_logs" in tables


def test_table_schema_integrity(test_engine):
    """Verify that inspect(engine) confirms all columns, primary keys, and foreign keys."""
    inspector = inspect(test_engine)
    existing_tables = inspector.get_table_names()

    for expected in ["users", "transactions", "predictions", "investigation_cases", "case_notes", "audit_logs"]:
        assert expected in existing_tables, f"Table '{expected}' missing from database."

    # Verify users columns
    user_cols = {col["name"]: col for col in inspector.get_columns("users")}
    assert "id" in user_cols
    assert "name" in user_cols
    assert "email" in user_cols
    assert "password_hash" in user_cols
    assert "role" in user_cols
    assert "is_active" in user_cols
    assert "created_at" in user_cols
    assert "updated_at" in user_cols
    assert "last_login_at" in user_cols

    # Verify transactions columns
    tx_cols = {col["name"]: col for col in inspector.get_columns("transactions")}
    assert "id" in tx_cols
    assert "external_reference" in tx_cols
    assert "transaction_time" in tx_cols
    assert "amount" in tx_cols
    assert "features" in tx_cols
    assert "submitted_by" in tx_cols
    assert "created_at" in tx_cols

    # Verify predictions columns
    pred_cols = {col["name"]: col for col in inspector.get_columns("predictions")}
    assert "id" in pred_cols
    assert "transaction_id" in pred_cols
    assert "fraud_probability" in pred_cols
    assert "risk_score" in pred_cols
    assert "predicted_class" in pred_cols
    assert "risk_level" in pred_cols
    assert "decision_threshold" in pred_cols
    assert "model_version" in pred_cols
    assert "explanation" in pred_cols
    assert "predicted_at" in pred_cols

    # Verify investigation_cases columns
    case_cols = {col["name"]: col for col in inspector.get_columns("investigation_cases")}
    assert "id" in case_cols
    assert "transaction_id" in case_cols
    assert "status" in case_cols
    assert "assigned_user_id" in case_cols
    assert "assigned_to" in case_cols
    assert "description" in case_cols
    assert "notes" in case_cols
    assert "created_at" in case_cols
    assert "updated_at" in case_cols
    assert "resolved_at" in case_cols

    # Verify case_notes columns
    note_cols = {col["name"]: col for col in inspector.get_columns("case_notes")}
    assert "id" in note_cols
    assert "case_id" in note_cols
    assert "author_id" in note_cols
    assert "author_name" in note_cols
    assert "author_email" in note_cols
    assert "author_role" in note_cols
    assert "body" in note_cols
    assert "created_at" in note_cols

    # Verify foreign key constraint on predictions -> transactions
    pred_fks = inspector.get_foreign_keys("predictions")
    assert any(
        fk["referred_table"] == "transactions" and fk["referred_columns"] == ["id"]
        for fk in pred_fks
    )

    # Verify foreign key constraint on case_notes -> investigation_cases
    note_fks = inspector.get_foreign_keys("case_notes")
    assert any(
        fk["referred_table"] == "investigation_cases" and fk["referred_columns"] == ["id"]
        for fk in note_fks
    )
