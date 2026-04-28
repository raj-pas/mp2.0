# MP2.0 Open Questions

These questions are tracked but do not block Phase 1 unless a task explicitly
touches the affected behavior.

| Question | Owner | Phase Impact |
| --- | --- | --- |
| Capital market assumptions source for sleeve return/vol/correlation inputs | Saranyaraj + Fraser | Blocks real engine outputs; Phase 1 uses placeholders |
| Specific household × goal risk composite weighting | Team | Phase 1 stubs a documented deterministic blend |
| Compliance risk-rating thresholds | Lori + Saranyaraj | Phase 1 uses placeholder volatility/equity thresholds |
| Real meeting-note shape and conventions | Lori → Raj | Blocks production extraction prompts; Phase 1 does not parse real notes |
| Real sleeve numerical inputs | Saranyaraj + Nafal | Phase 1 keeps illustrative assumptions clearly named |
| Strict PII handling for extraction | Raj | Expand before real raw files enter `personas/*/raw/` |
| Staging deployment timing | Team | Deferred until after demo-ready local flow |
