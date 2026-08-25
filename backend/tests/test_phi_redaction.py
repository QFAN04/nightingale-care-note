import pytest

from app.ai.redaction import redact_phi


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Sarah Lim reports chest pressure.", "[PATIENT_NAME] reports chest pressure."),
        ("Sarah reports chest pressure.", "[PATIENT_NAME] reports chest pressure."),
        ("Call 91234567 tomorrow.", "Call [PHONE] tomorrow."),
        ("Call +65 9123 4567 tomorrow.", "Call [PHONE] tomorrow."),
        ("Synthetic ID S1234567A.", "Synthetic ID [ID]."),
    ],
)
def test_redacts_frozen_phi_categories(source: str, expected: str) -> None:
    result = redact_phi(source, known_names=["Sarah Lim", "Sarah"])

    assert result.text == expected


def test_redaction_is_case_insensitive_and_reports_counts() -> None:
    result = redact_phi(
        "sarah lim can be reached at +65-9123-4567; ID s1234567a.",
        known_names=["Sarah Lim", "Sarah"],
    )

    assert result.text == "[PATIENT_NAME] can be reached at [PHONE]; ID [ID]."
    assert result.replacements == {"name": 1, "phone": 1, "id": 1}
