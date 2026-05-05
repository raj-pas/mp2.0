/**
 * Interactive 5-band canon risk picker (locked decision #6).
 *
 * Wraps the read-only `RiskBandTrack` with band-selection + override-
 * rationale capture. Per locked decision #6 the picker NEVER exposes
 * Goal_50 / 0-50; the surface is canon 1-5 + descriptor only.
 *
 * Permission gate: only advisors can save an override (locked decision
 * #4 + plan parking-lot #1). Analysts see a locked overlay; the
 * "Request access" affordance is a tooltip in v1 (canon §13.0.1
 * Phase B re-wires to a real flow).
 *
 * Form stack: react-hook-form + zod (locked decision #29). Rationale
 * minimum length is enforced both client and server side (`min(10)`).
 *
 * Save → POST `/api/goals/{id}/override/` → fires AuditEvent
 * `goal_risk_override_created` (locked decision #37 regression
 * suite covers this).
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { Lock } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { useCreateOverride, type GoalScoreResponse } from "../../lib/preview";
import { BUCKET_COLORS, RISK_DESCRIPTOR_KEYS } from "../../lib/risk";
import { toastError, toastSuccess } from "../../lib/toast";
import { normalizeApiError } from "../../lib/api-error";
import { cn } from "../../lib/cn";
import { Button } from "./button";

const ALL_BANDS: (1 | 2 | 3 | 4 | 5)[] = [1, 2, 3, 4, 5];

const overrideSchema = z.object({
  rationale: z.string().trim().min(10, "Rationale must be at least 10 characters."),
});

type OverrideFormValues = z.infer<typeof overrideSchema>;

interface RiskSliderProps {
  goalId: string;
  /** Current effective score (system or active override); marker. */
  effectiveScore: 1 | 2 | 3 | 4 | 5;
  /** System-derived score (no override applied). Ghost tick on the band. */
  systemScore: 1 | 2 | 3 | 4 | 5;
  /** Derivation breakdown from the goal-score preview, for explanation copy. */
  derivation?: GoalScoreResponse["derivation"];
  /** Whether the override surface is currently active (latest-row-wins). */
  isOverridden: boolean;
  /** Advisor (`advisor:risk:write`) — false locks the slider. */
  canEdit: boolean;
  /** Goal AUM share of household (0..1) for derivation copy. */
  sizeShare?: number | null;
  /** Goal tier ("need" | "want" | "wish" | "unsure") for derivation copy. */
  tier?: "need" | "want" | "wish" | "unsure" | null;
  /**
   * Optional callback fired whenever `selectedScore !== systemScore`
   * (i.e., advisor is previewing an override but hasn't saved yet).
   *
   * Per locked decision §3.7: lifts `isOverrideDraft` state to `GoalRoute`
   * so `GoalAllocationSection` can flip its source pill to
   * "calibration_drag" while the slider is being dragged. On save
   * (override commits + engine auto-regenerates per locked #74), the
   * pill flips back to "engine".
   */
  onPreviewChange?: (isPreviewing: boolean) => void;
}

export function RiskSlider({
  goalId,
  effectiveScore,
  systemScore,
  derivation,
  isOverridden,
  canEdit,
  sizeShare,
  tier,
  onPreviewChange,
}: RiskSliderProps) {
  const { t } = useTranslation();
  const [selectedScore, setSelectedScore] = useState<1 | 2 | 3 | 4 | 5>(effectiveScore);
  const createOverride = useCreateOverride(goalId);

  // Sync selection when the parent updates effectiveScore (e.g., after a save).
  useEffect(() => {
    setSelectedScore(effectiveScore);
  }, [effectiveScore]);

  // Two distinct semantics (sub-session #3 A5 regression fix):
  //   - isOverrideDraft: selectedScore differs from the system-derived score;
  //     gates the SaveOverrideForm so the advisor can confirm/adjust an
  //     existing saved override AND draft a new one. (Pre-A2 behavior; do
  //     not change.)
  //   - isDragPreview: selectedScore differs from the CURRENT effective score
  //     (saved override OR system, whichever is in effect). Only true while
  //     the advisor is actively dragging away from the committed value.
  //     This is the lift-to-parent semantic per locked §3.1 + §3.7 — the
  //     SourcePill flips to "calibration_drag" only during a real drag, not
  //     on every page load of a goal that happens to have a saved override.
  const isOverrideDraft = selectedScore !== systemScore;
  const isDragPreview = selectedScore !== effectiveScore;

  useEffect(() => {
    onPreviewChange?.(isDragPreview);
  }, [isDragPreview, onPreviewChange]);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isValid },
  } = useForm<OverrideFormValues>({
    resolver: zodResolver(overrideSchema),
    mode: "onChange",
    defaultValues: { rationale: "" },
  });

  function onSubmit(values: OverrideFormValues) {
    const descriptor = canonDescriptorByScore[selectedScore];
    createOverride.mutate(
      {
        score_1_5: selectedScore,
        descriptor,
        rationale: values.rationale.trim(),
      },
      {
        onSuccess: () => {
          reset({ rationale: "" });
          toastSuccess(t(RISK_DESCRIPTOR_KEYS[selectedScore]), t("risk_slider.toast_saved"));
        },
        onError: (err) => {
          const e = normalizeApiError(err, t("risk_slider.save_failed"));
          toastError(t("risk_slider.save_failed"), { description: e.message });
        },
      },
    );
  }

  function reverseToSystem() {
    setSelectedScore(systemScore);
    reset({ rationale: "" });
  }

  if (!canEdit) {
    return <RiskSliderLocked effectiveScore={effectiveScore} systemScore={systemScore} />;
  }

  return (
    <section
      aria-label={t("risk_slider.aria_label")}
      className="border border-hairline-2 bg-paper p-4 shadow-sm"
    >
      <header className="mb-3 flex items-center justify-between">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("risk_slider.title")}
        </h3>
        <ReadoutLine
          selectedScore={selectedScore}
          systemScore={systemScore}
          isOverridden={isOverridden}
        />
      </header>

      <BandPicker
        selectedScore={selectedScore}
        systemScore={systemScore}
        onSelect={setSelectedScore}
      />

      <Derivation derivation={derivation} sizeShare={sizeShare} tier={tier} />

      {isOverrideDraft && (
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="mt-4 border border-accent-2/40 bg-paper-2 p-3"
        >
          <div className="mb-2 flex items-center gap-2">
            <span aria-hidden className="font-mono text-[12px] text-accent-2">
              ⚠
            </span>
            <p className="font-mono text-[10px] uppercase tracking-widest text-accent-2">
              {t("risk_slider.override_active_banner")}
            </p>
          </div>
          <label className="flex flex-col gap-1">
            <span className="font-mono text-[9px] uppercase tracking-widest text-muted">
              {t("risk_slider.rationale_label")}
            </span>
            <textarea
              {...register("rationale")}
              rows={3}
              maxLength={2000}
              placeholder={t("risk_slider.rationale_placeholder")}
              className="resize-y border border-hairline-2 bg-paper px-3 py-2 font-sans text-[12px] text-ink focus:border-accent focus:outline-none"
              aria-invalid={errors.rationale !== undefined}
            />
            {errors.rationale !== undefined && (
              <span role="alert" className="font-mono text-[10px] text-danger">
                {errors.rationale.message}
              </span>
            )}
          </label>
          <div className="mt-3 flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={reverseToSystem}
              disabled={createOverride.isPending}
            >
              {t("risk_slider.cancel_to_system")}
            </Button>
            <Button type="submit" size="sm" disabled={!isValid || createOverride.isPending}>
              {createOverride.isPending ? t("risk_slider.saving") : t("risk_slider.save_override")}
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}

function BandPicker({
  selectedScore,
  systemScore,
  onSelect,
}: {
  selectedScore: 1 | 2 | 3 | 4 | 5;
  systemScore: 1 | 2 | 3 | 4 | 5;
  onSelect: (score: 1 | 2 | 3 | 4 | 5) => void;
}) {
  const { t } = useTranslation();
  return (
    <div
      role="radiogroup"
      aria-label={t("risk_slider.bands_label")}
      className="flex flex-col gap-1.5"
    >
      <div className="flex w-full overflow-hidden border border-hairline">
        {ALL_BANDS.map((band) => {
          const active = band === selectedScore;
          const ghost = band === systemScore && band !== selectedScore;
          const descriptor = t(RISK_DESCRIPTOR_KEYS[band]);
          return (
            <button
              key={band}
              type="button"
              role="radio"
              aria-checked={active}
              aria-label={`${descriptor} (${band} / 5)`}
              onClick={() => onSelect(band)}
              className={cn(
                "relative flex-1 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
                !active && !ghost && "opacity-40",
                "min-h-[40px]",
              )}
              style={{ background: BUCKET_COLORS[band] }}
            >
              {active && <span aria-hidden className="absolute inset-0 border-2 border-ink" />}
              {ghost && (
                <span
                  aria-hidden
                  className="absolute inset-0 border-2 border-dashed border-ink/60"
                />
              )}
            </button>
          );
        })}
      </div>
      <div className="flex justify-between font-mono text-[9px] uppercase tracking-widest text-muted">
        {ALL_BANDS.map((band) => (
          <span key={band} className="flex-1 text-center">
            {t(RISK_DESCRIPTOR_KEYS[band])}
          </span>
        ))}
      </div>
    </div>
  );
}

function ReadoutLine({
  selectedScore,
  systemScore,
  isOverridden,
}: {
  selectedScore: 1 | 2 | 3 | 4 | 5;
  systemScore: 1 | 2 | 3 | 4 | 5;
  isOverridden: boolean;
}) {
  const { t } = useTranslation();
  const planDescriptor = t(RISK_DESCRIPTOR_KEYS[systemScore]);
  const draftDescriptor = t(RISK_DESCRIPTOR_KEYS[selectedScore]);
  if (selectedScore === systemScore) {
    return (
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted">
        {isOverridden
          ? t("risk_slider.override_matches_system")
          : t("risk_slider.system_only", { descriptor: planDescriptor })}
      </p>
    );
  }
  return (
    <p className="font-mono text-[10px] uppercase tracking-widest text-accent-2">
      {t("risk_slider.what_if", { plan: planDescriptor, whatif: draftDescriptor })}
    </p>
  );
}

function Derivation({
  derivation,
  sizeShare,
  tier,
}: {
  derivation: GoalScoreResponse["derivation"] | undefined;
  sizeShare: number | null | undefined;
  tier: RiskSliderProps["tier"];
}) {
  const { t } = useTranslation();
  if (derivation === undefined) return null;
  const tierLabel = tier !== null && tier !== undefined ? t(`routes.goal.tier_${tier}`) : null;
  return (
    <dl className="mt-3 grid grid-cols-3 gap-3 border-t border-hairline pt-3">
      <DerivationRow
        label={t("risk_slider.derivation_anchor")}
        value={derivation.anchor.toFixed(1)}
      />
      <DerivationRow
        label={
          tierLabel !== null
            ? t("risk_slider.derivation_imp_with_tier", { tier: tierLabel })
            : t("risk_slider.derivation_imp")
        }
        value={signed(derivation.imp_shift)}
      />
      <DerivationRow
        label={
          sizeShare !== null && sizeShare !== undefined
            ? t("risk_slider.derivation_size_with_share", {
                pct: (sizeShare * 100).toFixed(0),
              })
            : t("risk_slider.derivation_size")
        }
        value={signed(derivation.size_shift)}
      />
    </dl>
  );
}

function DerivationRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <dt className="font-mono text-[9px] uppercase tracking-widest text-muted">{label}</dt>
      <dd className="font-mono text-[12px] text-ink">{value}</dd>
    </div>
  );
}

function RiskSliderLocked({
  effectiveScore,
  systemScore,
}: {
  effectiveScore: 1 | 2 | 3 | 4 | 5;
  systemScore: 1 | 2 | 3 | 4 | 5;
}) {
  const { t } = useTranslation();
  return (
    <section
      aria-label={t("risk_slider.aria_label")}
      className="relative border border-hairline-2 bg-paper p-4 shadow-sm"
    >
      <header className="mb-3 flex items-center justify-between">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-muted">
          {t("risk_slider.title")}
        </h3>
        <span
          className="inline-flex items-center gap-1 font-mono text-[9px] uppercase tracking-widest text-muted"
          title={t("risk_slider.locked_tooltip")}
        >
          <Lock aria-hidden className="h-3 w-3" />
          {t("risk_slider.locked_badge")}
        </span>
      </header>
      <BandPicker selectedScore={effectiveScore} systemScore={systemScore} onSelect={() => {}} />
      <p className="mt-3 font-mono text-[10px] uppercase tracking-widest text-muted">
        {t("risk_slider.locked_description")}
      </p>
    </section>
  );
}

function signed(n: number): string {
  if (n > 0) return `+${n.toFixed(1)}`;
  if (n < 0) return n.toFixed(1);
  return "0.0";
}

const canonDescriptorByScore: Record<1 | 2 | 3 | 4 | 5, string> = {
  1: "Cautious",
  2: "Conservative-balanced",
  3: "Balanced",
  4: "Balanced-growth",
  5: "Growth-oriented",
};

// Used for tests / external imports — match the canon serializer choices.
export { canonDescriptorByScore as CANON_DESCRIPTOR_BY_SCORE };
