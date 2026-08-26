from sqlalchemy import Index

from app.models.clinical import ClinicalFact, Conflict, Highlight, Task
from app.models.timeline import Entry


def index_by_name(table) -> dict[str, Index]:
    return {index.name: index for index in table.indexes}


def column_names(index: Index) -> list[str]:
    return [expression.name for expression in index.expressions]


def test_patient_care_query_indexes_cover_frozen_access_paths() -> None:
    entry_indexes = index_by_name(Entry.__table__)
    fact_indexes = index_by_name(ClinicalFact.__table__)
    highlight_indexes = index_by_name(Highlight.__table__)
    task_indexes = index_by_name(Task.__table__)
    conflict_indexes = index_by_name(Conflict.__table__)

    assert column_names(entry_indexes["ix_entries_patient_created_at"]) == [
        "patient_id",
        "created_at",
    ]
    assert column_names(fact_indexes["ix_clinical_facts_patient_entry"]) == [
        "patient_id",
        "entry_id",
    ]
    assert "ix_highlights_patient_status_score" in highlight_indexes
    assert column_names(task_indexes["ix_tasks_patient_status"]) == [
        "patient_id",
        "status",
    ]
    assert column_names(conflict_indexes["ix_conflicts_patient_status"]) == [
        "patient_id",
        "status",
    ]


def test_highlight_sort_index_uses_bounded_learning_expression() -> None:
    index = index_by_name(Highlight.__table__)[
        "ix_highlights_patient_status_score"
    ]
    expression_sql = " ".join(str(item) for item in index.expressions)

    assert "patient_id" in expression_sql
    assert "status" in expression_sql
    assert "base_score + learned_score" in expression_sql

