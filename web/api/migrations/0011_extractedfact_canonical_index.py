"""Phase P1.1: cross-document entity alignment canonical_index column.

Adds a nullable IntegerField to ExtractedFact that stores the
workspace-canonical entity index (per
`extraction.entity_alignment.EntityAlignment`) for facts whose field
matches `(people|accounts|goals)[N].suffix`. Backwards-compat: existing
rows persist with NULL until the next `reconcile_workspace` run rewrites
them in-place.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0010_advisorprofile_factoverride_feedback"),
    ]

    operations = [
        migrations.AddField(
            model_name="extractedfact",
            name="canonical_index",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
