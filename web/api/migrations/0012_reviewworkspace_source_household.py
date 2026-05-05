"""Phase P2.1: re-open committed household for new statement.

Adds a nullable ForeignKey to ReviewWorkspace pointing at the source
Household that the workspace was re-opened from. The presence of the
field gates two behaviors per plan v20 §A1.30:

  - ReviewWorkspaceListCreateView excludes reopen workspaces from the
    main /review queue (`source_household__isnull=False`).
  - ReviewWorkspaceUncommitView forbids soft-undo on reopen workspaces
    (returns 403 with code "soft_undo_forbidden_on_reopen").

`on_delete=SET_NULL` so legacy households deleted via the Phase 1
soft-undo path don't cascade-delete their reopen workspaces (which
would lose audit context). `related_name="reopen_workspaces"` so we
can query `household.reopen_workspaces.filter(status__in=...)` to
gate the Re-open / Re-reconcile CTAs in the HouseholdRoute.

Backwards-compat (sister §3.16): existing pre-tag workspaces have
`source_household=None`, which is the default; no data migration
needed.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0011_extractedfact_canonical_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="reviewworkspace",
            name="source_household",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="reopen_workspaces",
                to="api.household",
            ),
        ),
    ]
