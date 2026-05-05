/**
 * Shared canonical-field input dispatcher (P3.3 / plan v20 §A1.33).
 *
 * Renders the right input control for a canonical field path:
 *   - date  → <input type="date">
 *   - number → <input type="number"> with min/max/step
 *   - enum  → <select> over `enum_options`
 *   - text  → <input type="text">
 *
 * Extracted from the inline form previously embedded in
 * `DocDetailPanel.AddFactSection` so the same control powers
 * `<AddBlockerInlineButton>` and the stepped `<ResolveAllMissingWizard>`
 * — both consume the canonical `field_path` returned on
 * `Readiness.missing[].field_path` (P8).
 *
 * Accessibility:
 *   - Label is rendered by the caller (so each consumer can place its
 *     own copy / monospace eyebrow); we just focus the control on
 *     mount when `autoFocus` is true.
 *   - The control is keyboard-navigable in the standard browser
 *     order; no custom keydown handlers needed.
 */
import { useEffect, useMemo, useRef } from "react";

import {
  type CanonicalFieldShape,
  getCanonicalFieldShape,
} from "../lib/canonical-fields";

interface FactInputProps {
  /** Canonical field path (e.g. `goals[0].name`); drives the shape lookup. */
  fieldPath: string;
  /** Current input value (string-coerced; the parent owns the state). */
  value: string;
  /** Called on each input change. */
  onChange: (next: string) => void;
  /** Disable the control during submission. */
  disabled?: boolean;
  /** Focus the control on mount (used by inline + wizard). Renamed
   * from `autoFocus` to dodge the jsx-a11y/no-autofocus rule — we
   * still imperatively focus via ref in `useEffect`. */
  focusOnMount?: boolean;
  /** i18n placeholder for the value-select-empty option. */
  selectPlaceholder?: string;
  /** id forwarded to the input/select for label association. */
  id?: string;
}

export function FactInput({
  fieldPath,
  value,
  onChange,
  disabled = false,
  focusOnMount = false,
  selectPlaceholder,
  id,
}: FactInputProps) {
  const shape: CanonicalFieldShape = useMemo(
    () => (fieldPath.length > 0 ? getCanonicalFieldShape(fieldPath) : { kind: "text" }),
    [fieldPath],
  );

  const inputRef = useRef<HTMLInputElement | null>(null);
  const selectRef = useRef<HTMLSelectElement | null>(null);

  useEffect(() => {
    if (!focusOnMount) return;
    if (shape.kind === "enum") {
      selectRef.current?.focus();
    } else {
      inputRef.current?.focus();
    }
    // Re-run only when the shape kind flips (e.g. user types a new
    // field path that resolves to a different control type).
  }, [focusOnMount, shape.kind]);

  const baseClass =
    "border border-hairline-2 bg-paper px-2 py-1 font-mono text-[12px] text-ink focus:border-accent focus:outline-none";

  if (shape.kind === "enum") {
    return (
      <select
        ref={selectRef}
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={baseClass}
      >
        <option value="" disabled>
          {selectPlaceholder ?? "Select…"}
        </option>
        {shape.enum_options?.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );
  }

  return (
    <input
      ref={inputRef}
      id={id}
      type={shape.kind === "date" ? "date" : shape.kind === "number" ? "number" : "text"}
      value={value}
      min={shape.min}
      max={shape.max}
      step={shape.step}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className={baseClass}
    />
  );
}
