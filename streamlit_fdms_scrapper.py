import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Constants
MAX_THREADS = 10
SEARCH_TEXTS = ["Invoice is valid", "Credit note is valid"]
VALIDATION_ERROR_CLASS = "val-errors-block"

def scrape_url(url, invoice_number):
    headers = {"User-Agent": "Mozilla/5.0"}
    result = {
        "URL": url,
        "Invoice Number": invoice_number,
        "Status": "Error",
        "Validation Error": ""
    }

    try:
        response = requests.get(url, timeout=10, headers=headers, allow_redirects=True)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            page_text = soup.get_text()

            if any(text in page_text for text in SEARCH_TEXTS):
                result["Status"] = "Found"
            else:
                result["Status"] = "Not Found"
                error_block = soup.find("div", class_=VALIDATION_ERROR_CLASS)
                if error_block:
                    result["Validation Error"] = error_block.get_text(strip=True)
        else:
            result["Status"] = f"Error: HTTP {response.status_code}"
    except requests.RequestException as e:
        result["Status"] = f"Error: {str(e)}"

    return result

# Streamlit UI
st.set_page_config(page_title="FDMS Scraper", layout="wide")
st.title("📄 FDMS Invoice Validation Scraper")

# Instructions
with st.expander("📌 CSV Format Instructions"):
    st.markdown("""
    - **Column A**: FDMS validation **Links**
    - **Column B**: Corresponding **Invoice Numbers**
    - Ensure the file has **no headers**
    """)

uploaded_file = st.file_uploader("Upload your CSV", type="csv")

if uploaded_file:
    df_input = pd.read_csv(uploaded_file, header=None)

    if df_input.shape[1] < 2:
        st.error("❗️ CSV must contain at least two columns: Link (A) and Invoice Number (B).")
    else:
        df_input.columns = ["URL", "Invoice Number"]
        valid_rows = [
            (row["URL"], row["Invoice Number"])
            for _, row in df_input.iterrows()
            if pd.notna(row["URL"]) and pd.notna(row["Invoice Number"])
        ]

        if not valid_rows:
            st.warning("⚠️ No valid rows found in the uploaded file.")
        else:
            if st.button("Start Scraping 🚀"):
                with st.spinner("Scraping in progress... This may take a moment..."):
                    results = []
                    total = len(valid_rows)
                    progress_bar = st.progress(0, text="Starting...")
                    status_placeholder = st.empty()

                    completed = 0
                    start_time = time.time()

                    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                        future_to_row = {executor.submit(scrape_url, url, inv): (url, inv) for url, inv in valid_rows}
                        for future in as_completed(future_to_row):
                            result = future.result()
                            results.append(result)
                            completed += 1

                            elapsed = time.time() - start_time
                            avg_time = elapsed / completed
                            remaining = int(avg_time * (total - completed))
                            mins, secs = divmod(remaining, 60)
                            percent = int(completed / total * 100)

                            progress_bar.progress(completed / total, text=f"Scraping... {percent}%")
                            status_placeholder.markdown(f"⏱️ Estimated time remaining: **{mins}m {secs}s**")

                    progress_bar.empty()
                    status_placeholder.empty()

                df = pd.DataFrame(results)
                st.session_state["results"] = df
                st.success("✅ Scraping completed!")

# Show Results in Tabs
if "results" in st.session_state:
    df = st.session_state["results"]
    tab_all, tab_found, tab_not_found, tab_errors = st.tabs(["📋 All", "✅ Found", "❌ Not Found", "⚠️ Errors"])

    with tab_all:
        st.dataframe(df, use_container_width=True)

    with tab_found:
        st.dataframe(df[df["Status"] == "Found"], use_container_width=True)

    with tab_not_found:
        st.dataframe(df[df["Status"] == "Not Found"], use_container_width=True)

    with tab_errors:
        st.dataframe(df[df["Status"].str.contains("Error")], use_container_width=True)
