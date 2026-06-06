# FDMS Validation Check

A Streamlit web app for validating FDMS verification links in bulk from a CSV or Excel file.

The app reads invoice verification URLs, visits each link, checks whether the FDMS validation page reports the invoice or credit note as valid, and returns a downloadable CSV with the validation result for every document.

## Features

- Upload CSV or Excel files directly in the browser
- Validate multiple FDMS links concurrently
- Match successful validation messages for invoices and credit notes
- Capture validation error text when a document is not valid
- Separate result views for all records, valid records, invalid records, and request errors
- Download validation results as a CSV file

## Input File Format

Your input file must include headers and the following columns:

| Column | Description |
| --- | --- |
| `Verification Url` | The FDMS verification URL to validate |
| `Document No.` | The invoice or credit note number used as the reference |

Additional columns are allowed, but only these two columns are used by the app.

Rows with missing values in either required column are skipped.

## Output

The app generates a results table with:

| Column | Description |
| --- | --- |
| `URL` | The FDMS URL that was checked |
| `Invoice Number` | The document number from the uploaded file |
| `Status` | `Valid`, `Not Valid`, or `Error` |
| `Validation Error` | Error details from the FDMS page or request failure |

You can download the full result set as `fdms_results.csv`.

## How Validation Works

For each uploaded URL, the app:

1. Checks that the URL is structurally valid.
2. Sends an HTTP request to the verification page.
3. Parses the returned HTML.
4. Marks the document as `Valid` if the page contains either:
   - `Invoice is valid`
   - `Credit note is valid`
5. Marks the document as `Not Valid` if the page loads but no valid message is found.
6. Extracts the validation error from `.val-errors-block .col` when available.
7. Marks the document as `Error` for invalid URLs, failed requests, non-200 HTTP responses, or repeated retry failures.

## Requirements

- Python 3.9 or newer recommended
- pip

Python dependencies are listed in [requirements.txt](requirements.txt).

## Installation

Clone the repository:

```bash
git clone https://github.com/your-username/fdms_validation_check.git
cd fdms_validation_check
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Start the Streamlit app:

```bash
streamlit run streamlit_fdms_scrapper.py
```

Then open the local URL shown by Streamlit, usually:

```text
http://localhost:8501
```

In the app:

1. Upload a `.csv` or `.xlsx` file.
2. Confirm that valid rows were loaded.
3. Click `Start Validation`.
4. Review the result tabs.
5. Download the results CSV.

## Configuration

The main runtime settings are defined near the top of [streamlit_fdms_scrapper.py](streamlit_fdms_scrapper.py):

| Setting | Default | Description |
| --- | ---: | --- |
| `MAX_RETRIES` | `3` | Number of attempts before marking a request as failed |
| `RETRY_DELAY` | `2` | Seconds to wait between failed request attempts |
| `MAX_THREADS` | `10` | Maximum number of concurrent validation requests |
| `SEARCH_TEXTS` | `["Invoice is valid", "Credit note is valid"]` | Page text used to identify valid documents |

Adjust these values if you need slower or faster validation behavior.

## Notes and Limitations

- The app depends on the structure and text returned by the FDMS verification pages.
- Very large uploads may take time depending on network speed and FDMS response times.
- The app retries request failures, but persistent network issues or unavailable URLs are reported as errors.
- This project does not permanently store uploaded files or validation results; results live in the Streamlit session until the page is refreshed or the app restarts.

## Project Structure

```text
.
|-- README.md
|-- requirements.txt
`-- streamlit_fdms_scrapper.py
```

## Contributing

Contributions are welcome. Useful improvements could include:

- Better request error reporting
- Support for more input column names
- Exporting Excel results
- Automated tests for the URL validation logic
- Deployment instructions for Streamlit Community Cloud or another host

## License

No license file is currently included. Add a `LICENSE` file before publishing if you want others to use, modify, or redistribute the project under explicit open source terms.
