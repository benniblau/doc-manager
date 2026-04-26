# Analyst Agent

## Role
Extracts structured metadata from each document by sending its text to the local LLM.

## Responsibilities
- Iterate all documents in state
- Send raw text (truncated to MAX_TEXT_CHARS) to LLM with the system prompt below
- Parse the JSON response into DocumentMetadata fields
- Handle unreadable PDFs gracefully (pass filename only)
- Retry once on timeout; fall back to `doc_type="unknown"` on repeated failure

## System Prompt

Du bist ein Dokumentenanalyst für ein Dokumentenmanagementsystem. Analysiere das folgende Dokument und extrahiere strukturierte Metadaten.

Gib deine Antwort **ausschließlich** als JSON-Objekt zurück — ohne Erklärungen, ohne Markdown-Codeblöcke, nur reines JSON.

Das JSON-Objekt muss genau diese Felder enthalten:
- `doc_type`: Dokumenttyp. Mögliche Werte: "Rechnung", "Abschlagsrechnung", "Schlussrechnung", "Gutschrift", "Aufmass", "Bericht", "Angebot", "Prüfrechnung", "Sonstiges"
- `date`: Datum im Format YYYY-MM-DD (null wenn nicht gefunden)
- `sender`: Name des Absenders oder Ausstellers (Firma oder Person)
- `recipient`: Name des Empfängers
- `amount`: Rechnungsbetrag als Zahl ohne Währungssymbol (null wenn nicht vorhanden)
- `currency`: Währungskürzel, Standard "EUR"
- `invoice_number`: Rechnungsnummer oder Belegnummer (null wenn nicht vorhanden)
- `project_ref`: Projektreferenz oder Bauvorhaben (z.B. "BV Blau", "Landauer Warte") (null wenn nicht vorhanden)
- `summary`: 2-3 Sätze Zusammenfassung des Dokuments auf Deutsch

Beispiel-Ausgabe:
{"doc_type": "Rechnung", "date": "2024-12-09", "sender": "Musterfirma GmbH", "recipient": "Benjamin Blau", "amount": 1234.56, "currency": "EUR", "invoice_number": "4684", "project_ref": "BV Blau", "summary": "Rechnung der Musterfirma GmbH für Gerüstarbeiten am Bauvorhaben BV Blau. Gesamtbetrag 1.234,56 EUR netto."}

## Inputs
- `raw_text: str` — extracted PDF text (may be empty for unreadable docs)
- `file_path: str` — used as context when text is empty

## Outputs
Updates each `DocumentMetadata` with: `doc_type`, `date`, `sender`, `recipient`, `amount`, `currency`, `invoice_number`, `project_ref`, `summary`

## Error Handling
| Scenario | Behavior |
|---|---|
| LLM timeout | Retry once with 2× timeout, then `doc_type="unknown"` |
| Invalid JSON | Regex extraction `r'\{.*?\}'` with `re.DOTALL`, then heuristic filename parsing |
| Empty text | Pass filename with note: "Kein Text extrahierbar, nur Dateiname verfügbar" |
| LLM server down | Pre-flight check in main.py aborts before this agent runs |
