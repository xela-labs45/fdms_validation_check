import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import time

st.set_page_config(page_title="FDMS Validator", layout="wide")

# Constants
SEARCH_TEXTS = ["Invoice is valid", "Credit note is valid"]
MAX_RETRIES = 3
RETRY_DELAY = 2
MAX_THREADS = 10
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
REQUIRED_COLUMNS = {
    "verification url": "Verification Url",
    "document no.": "Document No.",
}

# UI Instructions
st.title("📄 FDMS Link Validator")
st.markdown("""
### 📤 Instructions

Upload a **CSV or Excel file** that includes:
- **'Verification Url'** column → FDMS URL to validate
- **'Document No.'** column → Invoice Number (used as reference)

> 📝 File must include headers. Additional columns are fine.
""")

def normalize_column_name(column_name):
    return " ".join(str(column_name).strip().lower().split())


def normalize_input_columns(df):
    normalized_to_actual = {normalize_column_name(col): col for col in df.columns}
    missing = [display_name for normalized_name, display_name in REQUIRED_COLUMNS.items() if normalized_name not in normalized_to_actual]

    if missing:
        return None, missing

    selected_columns = {
        normalized_to_actual[normalized_name]: display_name
        for normalized_name, display_name in REQUIRED_COLUMNS.items()
    }
    return df[list(selected_columns.keys())].rename(columns=selected_columns), []


def result_row(url, invoice_number, status, validation_error, row_number):
    return {
        "Row Number": row_number,
        "URL": url,
        "Invoice Number": invoice_number,
        "Status": status,
        "Validation Error": validation_error,
    }


# Scraping function
def scrape_url(url, invoice_number, row_number):
    url = "" if pd.isna(url) else str(url).strip()
    invoice_number = "" if pd.isna(invoice_number) else str(invoice_number).strip()

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return result_row(url, invoice_number, "Error", "Invalid URL", row_number)

    last_error = "Max retries exceeded"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=10, headers=HEADERS)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")
                text = soup.get_text()
                found = any(msg in text for msg in SEARCH_TEXTS)

                if found:
                    return result_row(url, invoice_number, "Valid", "", row_number)

                val_error = soup.select_one(".val-errors-block .col")
                error_text = val_error.get_text(strip=True) if val_error else "Validation error not found"
                return result_row(url, invoice_number, "Not Valid", error_text, row_number)

            last_error = f"HTTP {response.status_code}"
            if response.status_code not in RETRYABLE_STATUS_CODES:
                return result_row(url, invoice_number, "Error", last_error, row_number)
        except requests.RequestException as exc:
            last_error = f"Request failed: {exc}"
        except Exception as exc:
            last_error = f"Validation failed: {exc}"
            return result_row(url, invoice_number, "Error", last_error, row_number)

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    return result_row(url, invoice_number, "Error", last_error, row_number)

# File uploader
uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # Detect and read file type
        if uploaded_file.name.endswith(".csv"):
            df_input = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(".xlsx"):
            df_input = pd.read_excel(uploaded_file)
        else:
            st.error("Unsupported file type.")
            df_input = None

        if df_input is not None:
            # Validate required columns
            df_required, missing_cols = normalize_input_columns(df_input)
            if missing_cols:
                st.error(f"❌ Missing required columns. Please ensure your file includes: {', '.join(missing_cols)}")
            else:
                df_filtered = df_required.dropna().copy()
                valid_rows = [
                    (row_number, row["Verification Url"], row["Document No."])
                    for row_number, row in df_filtered.iterrows()
                ]

                if not valid_rows:
                    st.warning("⚠️ No valid rows to process after filtering missing values.")
                else:
                    st.success(f"✅ {len(valid_rows)} valid rows loaded from file.")

                    if st.button("Start Validation 🚀"):
                        with st.spinner("Validation in progress... This may take a moment..."):
                            results = []
                            total = len(valid_rows)
                            progress_bar = st.progress(0, text="Starting...")
                            status_placeholder = st.empty()

                            completed = 0
                            start_time = time.time()

                            with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                                future_to_row = {
                                    executor.submit(scrape_url, url, inv, row_number): (url, inv, row_number)
                                    for row_number, url, inv in valid_rows
                                }
                                for future in as_completed(future_to_row):
                                    url, inv, row_number = future_to_row[future]
                                    try:
                                        result = future.result()
                                    except Exception as exc:
                                        result = result_row(url, inv, "Error", f"Unexpected validation error: {exc}", row_number)

                                    results.append(result)
                                    completed += 1

                                    # Estimate time
                                    elapsed = time.time() - start_time
                                    avg_time = elapsed / completed
                                    remaining = int(avg_time * (total - completed))
                                    mins, secs = divmod(remaining, 60)
                                    percent = int((completed / total) * 100)

                                    progress_bar.progress(completed / total, text=f"Validation... {percent}%")
                                    status_placeholder.markdown(f"⏱️ Estimated time remaining: **{mins}m {secs}s**")

                            progress_bar.empty()
                            status_placeholder.empty()

                        df_result = pd.DataFrame(results).sort_values("Row Number").drop(columns=["Row Number"])
                        st.session_state["results"] = df_result
                        st.success("✅ Validation completed!")

    except Exception as e:
        st.error(f"❌ Error reading file: {str(e)}")

# Tabs to show results
if "results" in st.session_state:
    df = st.session_state["results"]
    tab_all, tab_valid, tab_not_valid, tab_errors = st.tabs(["📄 All", "✅ Valid", "❌ Not Valid", "⚠️ Errors"])

    with tab_all:
        st.dataframe(df, use_container_width=True)

    with tab_valid:
        st.dataframe(df[df["Status"] == "Valid"], use_container_width=True)

    with tab_not_valid:
        st.dataframe(df[df["Status"] == "Not Valid"][["URL", "Invoice Number", "Validation Error"]], use_container_width=True)

    with tab_errors:
        st.dataframe(df[df["Status"] == "Error"][["URL", "Invoice Number", "Validation Error"]], use_container_width=True)

    st.download_button("📥 Download Results as CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="fdms_results.csv", mime="text/csv")
