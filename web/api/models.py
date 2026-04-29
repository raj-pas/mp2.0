from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


def uuid_string() -> str:
    return str(uuid.uuid4())


class Household(models.Model):
    external_id = models.CharField(max_length=120, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="households",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    display_name = models.CharField(max_length=255)
    household_type = models.CharField(
        max_length=20, choices=[("single", "Single"), ("couple", "Couple")]
    )
    household_risk_score = models.PositiveSmallIntegerField(default=5)
    external_assets = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    last_engine_output = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name


class Person(models.Model):
    external_id = models.CharField(max_length=120, unique=True)
    household = models.ForeignKey(Household, related_name="members", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    dob = models.DateField()
    marital_status = models.CharField(max_length=80, blank=True)
    blended_family_flag = models.BooleanField(default=False)
    citizenship = models.CharField(max_length=120, default="Canada")
    residency = models.CharField(max_length=120, default="Canada")
    health_indicators = models.JSONField(default=dict, blank=True)
    longevity_assumption = models.PositiveSmallIntegerField(null=True, blank=True)
    employment = models.JSONField(default=dict, blank=True)
    pensions = models.JSONField(default=list, blank=True)
    investment_knowledge = models.CharField(
        max_length=20,
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
        default="medium",
    )
    trusted_contact_person = models.CharField(max_length=255, blank=True)
    poa_status = models.CharField(max_length=120, blank=True)
    will_status = models.CharField(max_length=120, blank=True)
    beneficiary_designations = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["dob"]

    def __str__(self) -> str:
        return self.name


class Account(models.Model):
    external_id = models.CharField(max_length=120, unique=True)
    household = models.ForeignKey(Household, related_name="accounts", on_delete=models.CASCADE)
    owner_person = models.ForeignKey(
        Person,
        related_name="accounts",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    account_type = models.CharField(max_length=40)
    regulatory_objective = models.CharField(max_length=40)
    regulatory_time_horizon = models.CharField(max_length=20)
    regulatory_risk_rating = models.CharField(max_length=20)
    current_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    contribution_room = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    contribution_history = models.JSONField(default=list, blank=True)
    is_held_at_purpose = models.BooleanField(default=True)
    missing_holdings_confirmed = models.BooleanField(default=False)

    class Meta:
        ordering = ["account_type", "external_id"]

    def __str__(self) -> str:
        return f"{self.household.display_name} {self.account_type}"


class Holding(models.Model):
    account = models.ForeignKey(Account, related_name="holdings", on_delete=models.CASCADE)
    sleeve_id = models.CharField(max_length=120)
    sleeve_name = models.CharField(max_length=255)
    weight = models.DecimalField(max_digits=8, decimal_places=6)
    market_value = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ["sleeve_name"]

    def __str__(self) -> str:
        return f"{self.sleeve_name} {self.weight}"


class Goal(models.Model):
    external_id = models.CharField(max_length=120, unique=True)
    household = models.ForeignKey(Household, related_name="goals", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    target_date = models.DateField()
    necessity_score = models.PositiveSmallIntegerField(default=3)
    current_funded_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    contribution_plan = models.JSONField(default=dict, blank=True)
    goal_risk_score = models.PositiveSmallIntegerField(default=3)
    status = models.CharField(max_length=40, default="watch")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["target_date"]

    def __str__(self) -> str:
        return self.name


class GoalAccountLink(models.Model):
    goal = models.ForeignKey(Goal, related_name="account_allocations", on_delete=models.CASCADE)
    account = models.ForeignKey(Account, related_name="goal_allocations", on_delete=models.CASCADE)
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    allocated_pct = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["goal", "account"], name="unique_goal_account_link")
        ]

    def __str__(self) -> str:
        return f"{self.goal} ← {self.account}"


class CMASnapshot(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    external_id = models.CharField(max_length=120, unique=True, default=uuid_string)
    name = models.CharField(max_length=255, default="Fraser CMA")
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    source = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_cma_snapshots",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="published_cma_snapshots",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["status"],
                condition=models.Q(status="active"),
                name="unique_active_cma_snapshot",
            ),
            models.UniqueConstraint(fields=["version"], name="unique_cma_snapshot_version"),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version} ({self.status})"


class CMAFundAssumption(models.Model):
    snapshot = models.ForeignKey(
        CMASnapshot, related_name="fund_assumptions", on_delete=models.CASCADE
    )
    fund_id = models.CharField(max_length=120)
    name = models.CharField(max_length=255)
    expected_return = models.DecimalField(max_digits=10, decimal_places=8)
    volatility = models.DecimalField(max_digits=10, decimal_places=8)
    optimizer_eligible = models.BooleanField(default=True)
    is_whole_portfolio = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)
    asset_class_weights = models.JSONField(default=dict, blank=True)
    tax_drag = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["display_order", "fund_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "fund_id"], name="unique_cma_fund_per_snapshot"
            )
        ]

    def __str__(self) -> str:
        return f"{self.snapshot} {self.name}"


class CMACorrelation(models.Model):
    snapshot = models.ForeignKey(CMASnapshot, related_name="correlations", on_delete=models.CASCADE)
    row_fund_id = models.CharField(max_length=120)
    col_fund_id = models.CharField(max_length=120)
    correlation = models.DecimalField(max_digits=8, decimal_places=5)

    class Meta:
        ordering = ["row_fund_id", "col_fund_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "row_fund_id", "col_fund_id"],
                name="unique_cma_correlation_cell",
            )
        ]


class PortfolioRun(models.Model):
    class Status(models.TextChoices):
        CURRENT = "current", "Current"
        STALE = "stale", "Stale"

    external_id = models.CharField(max_length=120, unique=True, default=uuid_string)
    household = models.ForeignKey(
        Household, related_name="portfolio_runs", on_delete=models.CASCADE
    )
    cma_snapshot = models.ForeignKey(
        CMASnapshot, related_name="portfolio_runs", on_delete=models.PROTECT
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="portfolio_runs",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CURRENT)
    stale_reason = models.CharField(max_length=255, blank=True)
    input_snapshot = models.JSONField(default=dict)
    output = models.JSONField(default=dict)
    input_hash = models.CharField(max_length=64)
    output_hash = models.CharField(max_length=64)
    engine_version = models.CharField(max_length=120)
    advisor_summary = models.TextField(blank=True)
    technical_trace = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.household} portfolio run {self.external_id}"


class PortfolioRunLinkRecommendation(models.Model):
    portfolio_run = models.ForeignKey(
        PortfolioRun, related_name="link_recommendation_rows", on_delete=models.CASCADE
    )
    goal = models.ForeignKey(Goal, on_delete=models.SET_NULL, null=True, blank=True)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    goal_external_id = models.CharField(max_length=120)
    account_external_id = models.CharField(max_length=120)
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2)
    frontier_percentile = models.PositiveSmallIntegerField()
    expected_return = models.DecimalField(max_digits=10, decimal_places=8)
    volatility = models.DecimalField(max_digits=10, decimal_places=8)
    allocations = models.JSONField(default=list)

    class Meta:
        ordering = ["goal_external_id", "account_external_id"]


class PlanningVersion(models.Model):
    household = models.ForeignKey(
        Household, related_name="planning_versions", on_delete=models.CASCADE
    )
    version = models.PositiveIntegerField()
    state = models.JSONField(default=dict)
    rationale = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="planning_versions",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["household", "version"], name="unique_planning_version_per_household"
            )
        ]


class ReviewWorkspace(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PROCESSING = "processing", "Processing"
        REVIEW_READY = "review_ready", "Review ready"
        ENGINE_READY = "engine_ready", "Engine ready"
        COMMITTED = "committed", "Committed"

    class DataOrigin(models.TextChoices):
        SYNTHETIC = "synthetic", "Synthetic"
        REAL_DERIVED = "real_derived", "Real-derived"

    external_id = models.CharField(max_length=120, unique=True, default=uuid_string)
    label = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="review_workspaces",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.DRAFT)
    data_origin = models.CharField(
        max_length=40, choices=DataOrigin.choices, default=DataOrigin.REAL_DERIVED
    )
    linked_household = models.ForeignKey(
        Household,
        related_name="review_workspaces",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reviewed_state = models.JSONField(default=dict, blank=True)
    readiness = models.JSONField(default=dict, blank=True)
    match_candidates = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]

    def __str__(self) -> str:
        return self.label


class ReviewDocument(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        DUPLICATE = "duplicate", "Duplicate"
        CLASSIFIED = "classified", "Classified"
        TEXT_EXTRACTED = "text_extracted", "Text extracted"
        OCR_REQUIRED = "ocr_required", "OCR required"
        OCR_COMPLETE = "ocr_complete", "OCR complete"
        FACTS_EXTRACTED = "facts_extracted", "Facts extracted"
        RECONCILED = "reconciled", "Reconciled"
        UNSUPPORTED = "unsupported", "Unsupported"
        FAILED = "failed", "Failed"

    workspace = models.ForeignKey(
        ReviewWorkspace, related_name="documents", on_delete=models.CASCADE
    )
    original_filename = models.CharField(max_length=500)
    content_type = models.CharField(max_length=255, blank=True)
    extension = models.CharField(max_length=20, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64)
    storage_path = models.CharField(max_length=1000, blank=True)
    document_type = models.CharField(max_length=80, default="unknown")
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.UPLOADED)
    failure_reason = models.TextField(blank=True)
    processing_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "sha256"], name="unique_review_document_workspace_sha"
            )
        ]

    def __str__(self) -> str:
        return self.original_filename


class ProcessingJob(models.Model):
    class JobType(models.TextChoices):
        PROCESS_DOCUMENT = "process_document", "Process document"
        RECONCILE_WORKSPACE = "reconcile_workspace", "Reconcile workspace"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    workspace = models.ForeignKey(
        ReviewWorkspace, related_name="processing_jobs", on_delete=models.CASCADE
    )
    document = models.ForeignKey(
        ReviewDocument,
        related_name="processing_jobs",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    job_type = models.CharField(
        max_length=40, choices=JobType.choices, default=JobType.PROCESS_DOCUMENT
    )
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.QUEUED)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    locked_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.job_type}:{self.status}"


class WorkerHeartbeat(models.Model):
    name = models.CharField(max_length=120, unique=True)
    last_seen_at = models.DateTimeField()
    current_job = models.ForeignKey(
        ProcessingJob,
        related_name="worker_heartbeats",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at"]

    def __str__(self) -> str:
        return f"{self.name}:{self.last_seen_at.isoformat()}"


class ExtractedFact(models.Model):
    class Confidence(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    class DerivationMethod(models.TextChoices):
        EXTRACTED = "extracted", "Extracted"
        INFERRED = "inferred", "Inferred"
        DEFAULTED = "defaulted", "Defaulted"

    workspace = models.ForeignKey(
        ReviewWorkspace, related_name="extracted_facts", on_delete=models.CASCADE
    )
    document = models.ForeignKey(
        ReviewDocument, related_name="extracted_facts", on_delete=models.CASCADE
    )
    field = models.CharField(max_length=255)
    value = models.JSONField(default=dict)
    asserted_at = models.DateField(null=True, blank=True)
    confidence = models.CharField(
        max_length=20, choices=Confidence.choices, default=Confidence.MEDIUM
    )
    derivation_method = models.CharField(
        max_length=20, choices=DerivationMethod.choices, default=DerivationMethod.EXTRACTED
    )
    source_page = models.PositiveIntegerField(null=True, blank=True)
    source_location = models.CharField(max_length=255, blank=True)
    evidence_quote = models.TextField(blank=True)
    extraction_run_id = models.CharField(max_length=255)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["field", "-asserted_at", "-created_at"]

    def __str__(self) -> str:
        return self.field


class ReviewedClientStateVersion(models.Model):
    workspace = models.ForeignKey(
        ReviewWorkspace, related_name="state_versions", on_delete=models.CASCADE
    )
    version = models.PositiveIntegerField()
    schema_version = models.CharField(max_length=40, default="reviewed_client_state.v1")
    state = models.JSONField(default=dict)
    readiness = models.JSONField(default=dict)
    is_committed = models.BooleanField(default=False)
    committed_household = models.ForeignKey(
        Household,
        related_name="reviewed_state_versions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reviewed_state_versions",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["workspace", "version"], name="unique_state_version")
        ]

    def __str__(self) -> str:
        return f"{self.workspace_id}:v{self.version}"


class SectionApproval(models.Model):
    class Status(models.TextChoices):
        APPROVED = "approved", "Approved"
        APPROVED_WITH_UNKNOWNS = "approved_with_unknowns", "Approved with unknowns"
        NEEDS_ATTENTION = "needs_attention", "Needs attention"
        NOT_READY = "not_ready_for_recommendation", "Not ready for recommendation"

    workspace = models.ForeignKey(
        ReviewWorkspace, related_name="section_approvals", on_delete=models.CASCADE
    )
    section = models.CharField(max_length=80)
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.NEEDS_ATTENTION)
    notes = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="section_approvals",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["section"]
        constraints = [
            models.UniqueConstraint(fields=["workspace", "section"], name="unique_section_approval")
        ]

    def __str__(self) -> str:
        return f"{self.section}:{self.status}"
