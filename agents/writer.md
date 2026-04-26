# Writer Agent

## Role
Generates a markdown summary file for each document using metadata extracted by the Analyst.

## Responsibilities
- Render a markdown file from a template for each document
- Write the `.md` file alongside where the PDF will land (temp dir or output path)
- Set `doc.markdown_path` in state

## No LLM calls
All content comes from the Analyst. This agent is fast and deterministic.

## Markdown Template

```markdown
# {original_filename}

## Metadata

| Field         | Value                  |
|---------------|------------------------|
| Type          | {doc_type}             |
| Date          | {date}                 |
| Sender        | {sender}               |
| Recipient     | {recipient}            |
| Amount        | {amount} {currency}    |
| Invoice No.   | {invoice_number}       |
| Project       | {project_ref}          |

## Summary

{summary}

## Source

- Original file: `{original_filename}`
- Processed: {today}
```

## Inputs
- All `DocumentMetadata` objects with metadata fields populated

## Outputs
- Markdown files written to a temp directory
- Updated `markdown_path` on each `DocumentMetadata`

## Error Handling
- Missing metadata fields are rendered as `—` (em dash)
- Unreadable PDFs get a note: `> Note: Text could not be extracted from this PDF (possibly a scanned image).`
