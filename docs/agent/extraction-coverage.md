# MP2.0 Extraction Coverage Matrix

This matrix is intentionally PII-free. Use generic bundle numbers, document
families, parser routes, failure codes, and readiness blockers only. Do not add
real names, filenames, account values, raw text, evidence quotes, screenshots,
or client IDs.

| Document family | Extensions | Parser route | Classifier route | Schema/prompt route | Current status | Required tests |
| --- | --- | --- | --- | --- | --- | --- |
| KYC / profile | pdf, docx | native text, OCR when needed | adaptive content + filename signals | `kyc_review_facts_v1` | implemented route, needs real-bundle validation | identity, risk, KYC fields, low-confidence fallback |
| Statement / account / holdings | pdf, xlsx, csv | native text, tables, sheets, OCR when needed | adaptive content + sheet signals | `statement_review_facts_v1` | implemented route, needs real-bundle validation | account values, holdings, missing-holdings marker, identifier hashing |
| Meeting notes | docx, txt, md, pdf | document text/tables | adaptive content + filename signals | `meeting_note_review_facts_v1` | implemented route, needs factual-vs-behavioral validation | goals, horizons, behavioral context, no invented numbers |
| Planning / projection | pdf, xlsx, docx | native text/tables/sheets | adaptive content + sheet signals | planning generic v1 | implemented route, needs authority validation | goals, horizons, target amounts, cash-flow facts |
| CRM/export/spreadsheet | xlsx, csv, pdf | sheets/rows/text | adaptive content + sheet signals | CRM/spreadsheet generic v1 | implemented route, needs source-precedence validation | household identity, client IDs, account identifiers |
| Identity/address/DOB support | pdf, image, docx | native text or OCR | adaptive identity signals | identity generic v1 | implemented route, TIFF conversion still explicit failure | DOB/address facts, source authority, no raw identifier storage |
| Ambiguous financial document | pdf, docx, xlsx, txt | parser by extension | low-confidence multi-schema sweep | generic financial sweep | implemented fallback route | classifier ambiguity, generic candidate confirmation |
| Image/TIFF | png, jpg, jpeg, tif, tiff | Bedrock vision for png/jpeg; TIFF currently needs conversion | image route | generic/identity sweep | png/jpeg route implemented; TIFF failure is typed | OCR failure visibility, overflow metadata, retry/manual review |

## Real-Bundle Gate

- Run all available secure-root bundles and continue after failures.
- Collate one sanitized aggregate manifest.
- Treat parser/classifier/Bedrock/schema failures as gate failures.
- Treat missing business facts as review blockers, not parser failures.
- After fixes, rerun the full gate until clean.
