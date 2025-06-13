import streamlit as st
import pandas as pd
import csv
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import time

st.set_page_config(page_title="FDMS Scraper", layout="wide")

# Constants
SEARCH_TEXTS = ["Invoice is valid", "Credit note is valid"]
MAX_RETRIES = 3
RETRY_DELAY = 2
MAX_THREADS = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# UI Instructions
st.title("📄 FDMS Link Validator")
st.markdown("""
### 📤 Instructions

Please upload a **CSV file** formatted as follows:

- **Column A:** FDMS Links (e.g. `https://fdms.zimra.co.zw/...`)
- **Column B:** Invoice Numbers (used for reference)

> ⚠️ Ensure the file **has no header row** and each row has **at least two columns**.
""")

# Scraping Function
def scrape_url(url, invoice_number):
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return {"URL": url, "Invoice Number": invoice_number, "Status": "Error", "Validation Error": "Invalid URL"}

    for _ in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=10, headers=HEADERS)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")
                text = soup.get_text()
                found = any(msg in text for msg in SEARCH_TEXTS)

                if found:
                    return {"URL": url, "Invoice Number": invoice_number, "Status": "Found", "Validation Error": ""}
                else:
                    # Try to extract the validation error message
                    val_error = soup.select_one(".val-errors-block .col")
                    error_text = val_error.get_text(strip=True) if val_error else "Validation error not found"
                    return {"URL": url, "Invoice Number": invoice_number, "Status": "Not Found", "Validation Error": error_text}
            else:
                return {"URL": url, "Invoice Number": invoice_number, "Status": "Error", "Validation Error": f"HTTP {response.status_code}"}
        except Exception as e:
            time.sleep(RETRY_DELAY)

    return {"URL": url, "Invoice Number": invoice_number, "Status": "Error", "Validation Error": "Max retries exceeded"}

# CSV Upload and Processing
uploaded_file = st.file_uploader("Upload CSV file with FDMS URLs", type=["csv"])

if uploaded_file:
    # Read and validate CSV
    rows = list(csv.reader(uploaded_file.read().decode("utf-8").splitlines()))
    valid_rows = []
    skipped_rows = 0

    for row in rows:
        if len(row) >= 2 and row[0].strip() and row[1].strip():
            valid_rows.append((row[0].strip(), row[1].strip()))
        else:
            skipped_rows += 1

    if not valid_rows:
        st.error("❌ No valid rows found in the uploaded file. Please check formatting.")
    else:
        st.success(f"✅ {len(valid_rows)} valid rows loaded. {skipped_rows} rows skipped.")

        if st.button("Start Scraping 🚀"):
            with st.spinner("Scraping in progress... This may take a moment..."):
                results = []
                with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                    future_to_row = {executor.submit(scrape_url, url, inv): (url, inv) for url, inv in valid_rows}
                    for future in as_completed(future_to_row):
                        results.append(future.result())

            df = pd.DataFrame(results)
            st.session_state["results"] = df
            st.success("✅ Scraping completed!")

# Results Filtering with Tabs
if "results" in st.session_state:
    df = st.session_state["results"]
    tab_all, tab_found, tab_not_found, tab_errors = st.tabs(["📄 All", "✅ Found", "❌ Not Found", "⚠️ Errors"])

    with tab_all:
        st.dataframe(df, use_container_width=True)

    with tab_found:
        st.dataframe(df[df["Status"] == "Found"], use_container_width=True)

    with tab_not_found:
        st.dataframe(df[df["Status"] == "Not Found"][["URL", "Invoice Number", "Validation Error"]], use_container_width=True)

    with tab_errors:
        st.dataframe(df[df["Status"] == "Error"][["URL", "Invoice Number", "Validation Error"]], use_container_width=True)

    st.download_button("📥 Download Results as CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="fdms_results.csv", mime="text/csv")
