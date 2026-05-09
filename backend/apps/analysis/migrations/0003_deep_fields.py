"""Add deep-analysis fields to AnalysisJob (idempotent)."""
from django.db import migrations, models


def add_columns_if_missing(apps, schema_editor):
    """Fallback path: add columns directly if Django schema-editor misses them."""
    cur = schema_editor.connection.cursor()
    cur.execute("PRAGMA table_info(analysis_analysisjob)")
    existing = {row[1] for row in cur.fetchall()}

    if "mode" not in existing:
        cur.execute(
            "ALTER TABLE analysis_analysisjob "
            "ADD COLUMN mode varchar(16) NOT NULL DEFAULT 'standard'"
        )
    if "detections" not in existing:
        cur.execute(
            "ALTER TABLE analysis_analysisjob "
            "ADD COLUMN detections text NOT NULL DEFAULT '[]'"
        )
    if "mitre_techniques" not in existing:
        cur.execute(
            "ALTER TABLE analysis_analysisjob "
            "ADD COLUMN mitre_techniques text NOT NULL DEFAULT '[]'"
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("analysis", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(add_columns_if_missing, noop_reverse),
        # Tell Django the model state now includes these fields (no SQL — DB
        # already matches after the RunPython above).
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="analysisjob",
                    name="mode",
                    field=models.CharField(
                        choices=[("standard", "Standard"), ("deep", "Deep")],
                        db_index=True, default="standard", max_length=16,
                    ),
                ),
                migrations.AddField(
                    model_name="analysisjob",
                    name="detections",
                    field=models.JSONField(
                        blank=True, default=list,
                        help_text="Persisted Detection records (post-processing).",
                    ),
                ),
                migrations.AddField(
                    model_name="analysisjob",
                    name="mitre_techniques",
                    field=models.JSONField(
                        blank=True, default=list,
                        help_text="Distinct ATT&CK technique IDs across all detections.",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
