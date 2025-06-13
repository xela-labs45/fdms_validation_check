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
HEADERS = {
    "User-Agent": "Mozilla/5.0"
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

# Scraping function
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
                    val_error = soup.select_one(".val-errors-block .col")
                    error_text = val_error.get_text(strip=True) if val_error else "Validation error not found"
                    return {"URL": url, "Invoice Number": invoice_number, "Status": "Not Found", "Validation Error": error_text}
            else:
                return {"URL": url, "Invoice Number": invoice_number, "Status": "Error", "Validation Error": f"HTTP {response.status_code}"}
        except Exception:
            time.sleep(RETRY_DELAY)

    return {"URL": url, "Invoice Number": invoice_number, "Status": "Error", "Validation Error": "Max retries exceeded"}

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
            required_cols = ["Verification Url", "Document No."]
            if not all(col in df_input.columns for col in required_cols):
                st.error(f"❌ Missing required columns. Please ensure your file includes: {', '.join(required_cols)}")
            else:
                df_filtered = df_input[required_cols].dropna()
                valid_rows = list(df_filtered.itertuples(index=False, name=None))

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
                                    executor.submit(scrape_url, url, inv): (url, inv)
                                    for url, inv in valid_rows
                                }
                                for future in as_completed(future_to_row):
                                    result = future.result()
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

                        df_result = pd.DataFrame(results)
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
