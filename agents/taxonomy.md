# Taxonomy Agent

## Role
Assigns each document a target subfolder using a fixed deterministic scheme: `{sender}/{doc_type}`.

## Responsibilities
- Derive `target_subfolder` for every document from its Analyst-extracted metadata
- Sanitize path components (umlauts → ASCII, spaces → underscores, lowercase)

## Structure
```
{sender}/{doc_type}/
```
Examples:
- `purpura_gmbh/rechnung/`
- `ofa_geruest/bericht/`
- `unknown/unknown/` (fallback when metadata is missing)

## No LLM calls
Fully deterministic — fast, predictable, and consistent across runs.

## Inputs
- All `DocumentMetadata` objects with `sender` and `doc_type` populated by the Analyst

## Outputs
- Updated `target_subfolder` on each `DocumentMetadata`
