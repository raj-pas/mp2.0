from __future__ import annotations

from rest_framework import serializers

from web.api import models
from web.audit.models import AuditEvent
from web.audit.writer import record_event


class PersonSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id")

    class Meta:
        model = models.Person
        fields = [
            "id",
            "name",
            "dob",
            "marital_status",
            "investment_knowledge",
            "employment",
            "pensions",
        ]


class HoldingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Holding
        fields = ["sleeve_id", "sleeve_name", "weight", "market_value"]


class AccountSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id")
    type = serializers.CharField(source="account_type")
    owner_person_id = serializers.CharField(source="owner_person.external_id", allow_null=True)
    holdings = HoldingSerializer(many=True)

    class Meta:
        model = models.Account
        fields = [
            "id",
            "owner_person_id",
            "type",
            "regulatory_objective",
            "regulatory_time_horizon",
            "regulatory_risk_rating",
            "current_value",
            "contribution_room",
            "is_held_at_purpose",
            "missing_holdings_confirmed",
            "cash_state",
            "holdings",
        ]


class GoalAccountLinkSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id")
    goal_id = serializers.CharField(source="goal.external_id")
    account_id = serializers.CharField(source="account.external_id")

    class Meta:
        model = models.GoalAccountLink
        fields = ["id", "goal_id", "account_id", "allocated_amount", "allocated_pct"]


class GoalSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id")
    account_allocations = GoalAccountLinkSerializer(many=True)

    class Meta:
        model = models.Goal
        fields = [
            "id",
            "name",
            "target_amount",
            "target_date",
            "necessity_score",
            "current_funded_amount",
            "contribution_plan",
            "goal_risk_score",
            "status",
            "notes",
            "account_allocations",
        ]


class HouseholdListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id")
    goal_count = serializers.SerializerMethodField()
    total_assets = serializers.SerializerMethodField()

    class Meta:
        model = models.Household
        fields = [
            "id",
            "display_name",
            "household_type",
            "household_risk_score",
            "goal_count",
            "total_assets",
        ]

    def get_goal_count(self, obj: models.Household) -> int:
        return obj.goals.count()

    def get_total_assets(self, obj: models.Household) -> float:
        return float(sum(account.current_value for account in obj.accounts.all()))


class HouseholdDetailSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id")
    goal_count = serializers.SerializerMethodField()
    total_assets = serializers.SerializerMethodField()
    members = PersonSerializer(many=True)
    goals = GoalSerializer(many=True)
    accounts = AccountSerializer(many=True)
    latest_portfolio_run = serializers.SerializerMethodField()
    latest_portfolio_failure = serializers.SerializerMethodField()
    readiness_blockers = serializers.SerializerMethodField()
    structured_readiness_blockers = serializers.SerializerMethodField()
    portfolio_runs = serializers.SerializerMethodField()

    class Meta:
        model = models.Household
        fields = [
            "id",
            "display_name",
            "household_type",
            "household_risk_score",
            "goal_count",
            "total_assets",
            "external_assets",
            "notes",
            "members",
            "goals",
            "accounts",
            "latest_portfolio_run",
            "latest_portfolio_failure",
            "readiness_blockers",
            "structured_readiness_blockers",
            "portfolio_runs",
        ]

    def get_goal_count(self, obj: models.Household) -> int:
        return obj.goals.count()

    def get_total_assets(self, obj: models.Household) -> float:
        return float(sum(account.current_value for account in obj.accounts.all()))

    def get_latest_portfolio_run(self, obj: models.Household) -> dict | None:
        run = obj.portfolio_runs.order_by("-created_at").first()
        return PortfolioRunSerializer(run, context=self.context).data if run else None

    def get_structured_readiness_blockers(self, obj: models.Household) -> list[dict] | None:
        """Structured TypedDict-shaped blockers per plan v20 §A1.27 / Round 14 #3.

        ADDITIVE companion to `readiness_blockers` (the humanized
        list[str] surfaced for backwards-compat). Frontend reads
        `structured_blocker_list` when present, falling back to the
        humanized strings on older payloads.

        Returns `None` when no engine output exists AND no review
        workspace is open — preserves the §3.16 backwards-compat
        contract (pre-tag GET on a fresh household must not crash).

        Emits a rate-limited `portfolio_generation_blocker_surfaced`
        audit event per §A1.23 schema, deduped on
        (household, len(blockers), first_code) so a household with
        unchanged blocker state doesn't emit on every GET. The dedup
        mirrors the existing `AuditEvent.objects.filter(...).exists()`
        pattern used in views.py.
        """
        from web.api.review_state import (
            portfolio_generation_blockers_structured_for_household,
        )
        from web.audit.models import AuditEvent

        try:
            structured = portfolio_generation_blockers_structured_for_household(obj)
        except Exception:  # noqa: BLE001 — defensive; never fail the GET
            return None

        if not structured:
            return []

        # §A1.23 audit metadata schema:
        #   action: portfolio_generation_blocker_surfaced
        #   metadata: {
        #     "blocker_count": int,
        #     "blocker_codes": list[str],  # closed Literal set; PII-safe
        #     "first_code": str,           # for dedup keying
        #   }
        # Rate-limited dedup: skip emission if same (count, first_code)
        # exists within last 24h on this household (mirror of the
        # existing pattern; full window-based dedup is out of P11 scope).
        try:
            blocker_codes = [b["code"] for b in structured]
            first_code = blocker_codes[0]
            already_emitted = AuditEvent.objects.filter(
                action="portfolio_generation_blocker_surfaced",
                entity_type="household",
                entity_id=obj.external_id,
                metadata__first_code=first_code,
                metadata__blocker_count=len(structured),
            ).exists()
            if not already_emitted:
                record_event(
                    action="portfolio_generation_blocker_surfaced",
                    entity_type="household",
                    entity_id=obj.external_id,
                    actor="system",
                    metadata={
                        "blocker_count": len(structured),
                        "blocker_codes": blocker_codes,
                        "first_code": first_code,
                    },
                )
        except Exception:  # noqa: BLE001 — audit failures must not block the GET
            pass

        return list(structured)

    def get_latest_portfolio_failure(self, obj: models.Household) -> dict | None:
        """Most recent portfolio_generation_*_failed AuditEvent newer than the
        household's latest PortfolioRun (if any). Drives RecommendationBanner's
        inline-error state per locked decision #9.
        """
        from web.audit.models import AuditEvent

        latest_run = obj.portfolio_runs.order_by("-created_at").first()
        cutoff = latest_run.created_at if latest_run else obj.created_at
        failure = (
            AuditEvent.objects.filter(
                entity_type="household",
                entity_id=obj.external_id,
                action__startswith="portfolio_generation_post_",
                action__endswith="_failed",
                created_at__gt=cutoff,
            )
            .order_by("-created_at")
            .first()
        )
        if failure is None:
            return None
        # Production audit metadata uses safe_audit_metadata which writes
        # `failure_code` (PII-safe exception class name like "RuntimeError"
        # or "InvalidCMAUniverse"). Frontend Banner / Panel display this as
        # the user-facing reason. `source` (review_commit / wizard_commit
        # / etc.) is the trigger source — NOT a useful failure reason for
        # advisor copy.
        failure_code = failure.metadata.get("failure_code") or "unknown"
        return {
            "action": failure.action,
            "reason_code": failure_code,
            "exception_summary": failure_code,  # alias for back-compat
            "occurred_at": failure.created_at.isoformat() if failure.created_at else None,
        }

    def get_readiness_blockers(self, obj: models.Household) -> list[str]:
        """Return advisor-actionable blockers preventing portfolio generation,
        OR an empty list if the household is engine-ready.

        Backed by `portfolio_generation_blockers_for_household` in
        `web/api/review_state.py` — same function the helper trio uses to
        decide whether to raise `ReviewedStateNotConstructionReady`. Surfacing
        this list on the household payload lets the advisor see WHY they
        can't generate without having to click Generate first (the typed-
        skip path is silent per locked #9; before this field, advisors had
        no persistent signal of the gap).

        UUID `external_id` references in the raw blocker strings are
        substituted with friendlier "<account_type> (<8-char prefix>)" form
        so the advisor can identify which account each blocker applies to.
        Synthetic external_ids (e.g., `acct_mike_rrsp`) don't match the
        UUID regex and pass through unchanged.

        Strings are PII-safe: internal external_ids only (not real client
        identifiers), advisor-set goal names, and account_type enums. No
        raw exception text, no extracted client content.
        """
        import re

        from web.api.review_state import portfolio_generation_blockers_for_household

        raw = portfolio_generation_blockers_for_household(obj)
        if not raw:
            return []

        # Build friendly-label map: external_id -> "RRSP (be3337bc)".
        # Truncated UUID prefix is enough to disambiguate same-type accounts.
        labels: dict[str, str] = {
            acct.external_id: f"{acct.account_type or 'Account'} ({acct.external_id[:8]})"
            for acct in obj.accounts.all()
        }
        uuid_re = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")

        def _humanize(blocker: str) -> str:
            return uuid_re.sub(lambda m: labels.get(m.group(0), m.group(0)), blocker)

        return [_humanize(b) for b in raw]

    def get_portfolio_runs(self, obj: models.Household) -> list[dict]:
        runs = obj.portfolio_runs.order_by("-created_at")[:10]
        return PortfolioRunSummarySerializer(runs, many=True, context=self.context).data


class PortfolioRunLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PortfolioRunLinkRecommendation
        fields = [
            "link_external_id",
            "goal_external_id",
            "account_external_id",
            "allocated_amount",
            "frontier_percentile",
            "expected_return",
            "volatility",
            "allocations",
            "current_comparison",
            "explanation",
            "warnings",
        ]


class PortfolioRunEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PortfolioRunEvent
        fields = ["event_type", "actor", "reason_code", "note", "metadata", "created_at"]


class PortfolioRunSummarySerializer(serializers.ModelSerializer):
    cma_snapshot_id = serializers.CharField(source="cma_snapshot.external_id")
    generated_by_email = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    warnings = serializers.SerializerMethodField()

    class Meta:
        model = models.PortfolioRun
        fields = [
            "id",
            "external_id",
            "status",
            "as_of_date",
            "cma_snapshot_id",
            "engine_version",
            "advisor_summary",
            "input_hash",
            "output_hash",
            "cma_hash",
            "reviewed_state_hash",
            "approval_snapshot_hash",
            "run_signature",
            "warnings",
            "generated_by_email",
            "created_at",
        ]

    def get_generated_by_email(self, obj: models.PortfolioRun) -> str:
        return obj.generated_by.email if obj.generated_by else "system"

    def get_status(self, obj: models.PortfolioRun) -> str:
        status = _portfolio_run_status(obj)
        if status == "hash_mismatch":
            self._maybe_emit_integrity_alert(obj)
        return status

    def _maybe_emit_integrity_alert(self, obj: models.PortfolioRun) -> None:
        """Emit `portfolio_run_integrity_alert` AuditEvent on first
        observation per (run, advisor) when status resolves to
        `hash_mismatch`.

        Per locked decision §3.5: integrity issues route to engineering
        via the audit trail; the advisor sees `IntegrityAlertOverlay`
        on the frontend (no Regenerate button — engineering action
        required). Dedup mirrors the pattern at
        `views._record_current_run_invalidations` (events.filter(...).
        exists()) so the audit table doesn't inflate per GET.
        """
        request = self.context.get("request")
        actor = "system"
        if request is not None:
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                actor = (
                    getattr(user, "email", None) or getattr(user, "username", "system") or "system"
                )
        already_emitted = AuditEvent.objects.filter(
            action="portfolio_run_integrity_alert",
            entity_type="portfolio_run",
            entity_id=obj.external_id,
            actor=actor,
        ).exists()
        if already_emitted:
            return
        record_event(
            action="portfolio_run_integrity_alert",
            entity_type="portfolio_run",
            entity_id=obj.external_id,
            actor=actor,
            metadata={
                "run_external_id": obj.external_id,
                "household_id": obj.household.external_id,
                "status": "hash_mismatch",
                "engine_version": obj.engine_version,
            },
        )

    def get_warnings(self, obj: models.PortfolioRun) -> list[str]:
        return list((obj.output or {}).get("warnings") or [])


class PortfolioRunSerializer(PortfolioRunSummarySerializer):
    link_recommendation_rows = PortfolioRunLinkSerializer(many=True)
    events = PortfolioRunEventSerializer(many=True)

    class Meta(PortfolioRunSummarySerializer.Meta):
        fields = [
            *PortfolioRunSummarySerializer.Meta.fields,
            "output",
            "technical_trace",
            "link_recommendation_rows",
            "events",
        ]


def _portfolio_run_status(obj: models.PortfolioRun) -> str:
    event_types = set(obj.events.values_list("event_type", flat=True))
    if models.PortfolioRunEvent.EventType.ADVISOR_DECLINED in event_types:
        return "declined"
    if models.PortfolioRunEvent.EventType.HASH_MISMATCH in event_types:
        return "hash_mismatch"
    if {
        models.PortfolioRunEvent.EventType.INVALIDATED_BY_CMA,
        models.PortfolioRunEvent.EventType.INVALIDATED_BY_HOUSEHOLD_CHANGE,
    } & event_types:
        return "invalidated"
    newer_run_exists = models.PortfolioRun.objects.filter(
        household=obj.household,
        created_at__gt=obj.created_at,
    ).exists()
    return "superseded" if newer_run_exists else "current"


class PlanningVersionSerializer(serializers.ModelSerializer):
    created_by_email = serializers.SerializerMethodField()

    class Meta:
        model = models.PlanningVersion
        fields = [
            "id",
            "version",
            "state",
            "rationale",
            "created_by_email",
            "created_at",
        ]

    def get_created_by_email(self, obj: models.PlanningVersion) -> str:
        return obj.created_by.email if obj.created_by else "system"


class CMAFundAssumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CMAFundAssumption
        fields = [
            "fund_id",
            "name",
            "expected_return",
            "volatility",
            "optimizer_eligible",
            "is_whole_portfolio",
            "display_order",
            "aliases",
            "asset_class_weights",
            "geography_weights",
            "tax_drag",
        ]


class CMACorrelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CMACorrelation
        fields = ["row_fund_id", "col_fund_id", "correlation"]


class CMASnapshotSerializer(serializers.ModelSerializer):
    fund_assumptions = CMAFundAssumptionSerializer(many=True)
    correlations = CMACorrelationSerializer(many=True)
    latest_publish_note = serializers.SerializerMethodField()

    class Meta:
        model = models.CMASnapshot
        fields = [
            "id",
            "external_id",
            "name",
            "version",
            "status",
            "source",
            "notes",
            "latest_publish_note",
            "published_at",
            "created_at",
            "updated_at",
            "fund_assumptions",
            "correlations",
        ]

    def get_latest_publish_note(self, obj: models.CMASnapshot) -> str:
        event = (
            AuditEvent.objects.filter(
                action="cma_snapshot_published",
                entity_type="cma_snapshot",
                entity_id=obj.external_id,
            )
            .order_by("-created_at")
            .first()
        )
        return str((event.metadata if event else {}).get("publish_note", ""))
