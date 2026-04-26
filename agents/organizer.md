# Organizer Agent

## Role
Copies all PDF and markdown files into the new subfolder structure under the output folder. Source files are never modified.

## Responsibilities
- Create all required subdirectories under `output_folder`
- Copy each PDF to `output_folder/{target_subfolder}/{stem}.pdf`
- Copy each `.md` file to the same subfolder
- Generate `_index.md` in `output_folder` summarizing all documents
- In `dry_run` mode: print a rich table of planned operations without touching any files

## Inputs
- `output_folder: str`
- `dry_run: bool`
- All `DocumentMetadata` with `file_path`, `target_subfolder`, `markdown_path` populated

## Outputs
- Files written to disk (or dry-run table printed)
- Updated `final_pdf_path` on each `DocumentMetadata`
- `_index.md` written to `output_folder`

## Filename Sanitization
- ä → ae, ö → oe, ü → ue, ß → ss
- Special characters stripped
- Spaces → underscores

## _index.md format
A markdown table listing all documents:

```markdown
# Document Index

Generated: {today}
Source: {source_folder}
Total documents: {N}

| Subfolder | Filename | Type | Date | Sender | Amount |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |
```

## No LLM calls
This agent performs purely local file system operations.
