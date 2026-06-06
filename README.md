# FDMS Validation Check

FDMS Validation Check is a simple Streamlit app for checking many FDMS verification links at once.

Upload a CSV or Excel file with your FDMS verification URLs, start the validation, and download a results file showing which documents are valid, not valid, or could not be checked.

## What It Does

- Accepts `.csv` and `.xlsx` files
- Checks invoice and credit note verification links in bulk
- Shows progress while validation is running
- Keeps the results in the same order as the uploaded file
- Separates results into `All`, `Valid`, `Not Valid`, and `Errors` tabs
- Shows available FDMS validation error text for failed documents
- Retries temporary connection and server issues before marking a link as an error
- Exports the full validation result as `fdms_results.csv`

## File Format

Your upload must include these columns:

| Column | Description |
| --- | --- |
| `Verification Url` | The FDMS verification link to check |
| `Document No.` | The invoice or credit note number |

Column names are matched without caring about extra spaces or letter case. For example, `verification url`, `Verification Url`, and ` Verification Url ` are treated as the same column.

Extra columns are allowed. Rows with a missing verification URL or document number are skipped.

## Result Columns

The downloaded results include:

| Column | Description |
| --- | --- |
| `URL` | The FDMS link that was checked |
| `Invoice Number` | The document number from the uploaded file |
| `Status` | `Valid`, `Not Valid`, or `Error` |
| `Validation Error` | FDMS validation message or request error details |

## Status Meanings

| Status | Meaning |
| --- | --- |
| `Valid` | The FDMS page says the invoice or credit note is valid |
| `Not Valid` | The FDMS page loaded, but it did not show a valid message |
| `Error` | The URL was invalid, unavailable, returned an HTTP error, or could not be checked after retries |

The app checks for these FDMS success messages:

- `Invoice is valid`
- `Credit note is valid`

## Installation

Clone the repository:

```bash
git clone https://github.com/xela-labs45/fdms_validation_check.git
cd fdms_validation_check
```

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the required packages:

```bash
pip install -r requirements.txt
```

## Running the App

Start Streamlit:

```bash
streamlit run streamlit_fdms_scrapper.py
```

Open the local Streamlit link shown in the terminal. It is usually:

```text
http://localhost:8501
```

## Using the App

1. Upload a CSV or Excel file.
2. Check that the app loaded the expected number of valid rows.
3. Click `Start Validation`.
4. Review the result tabs.
5. Download the results CSV.

## Reliability Notes

The app retries temporary request failures and common temporary HTTP responses such as `429`, `500`, `502`, `503`, and `504`.

If a link still cannot be checked, the result is marked as `Error` with the available error detail. The app does not stop the whole validation run because of a single bad URL or failed request.

Validation depends on the text and page structure returned by the FDMS verification site. If the FDMS page wording or layout changes, the matching rules may need to be updated.

## Requirements

- Python 3.9 or newer recommended
- pip

Dependencies are listed in [requirements.txt](requirements.txt).
