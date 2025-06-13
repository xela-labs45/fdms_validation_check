import csv
import time
import requests
import streamlit as st
import pandas as pd
import concurrent.futures
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from streamlit.components.v1 import html as components_html

# ----- Settings -----
search_texts = ["Invoice is valid", "Credit note is valid"]
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/91.0.4472.124 Safari/537.36"
}
max_retries = 3
retry_delay = 2  # seconds

def scrape_url(url):
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return [url, "Error: Invalid URL", "", ""]

    for _ in range(max_retries):
        try:
            response = requests.get(url, timeout=10, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                page_text = soup.get_text()

                if any(text in page_text for text in search_texts):
                    return [url, "Found", "", ""]
                else:
                    # Extract validation errors from .val-errors-block
                    errors = soup.select(".val-errors-block .col")
                    error_messages = [e.get_text(strip=True) for e in errors]
                    return [url, "Not Found", response.text, "\n".join(error_messages)]
            else:
                return [url, f"Error: HTTP {response.status_code}", "", ""]
        except requests.RequestException:
            time.sleep(retry_delay)

    return [url, "Error: Max retries exceeded", "", ""]

def main():
    st.title("📄 FDMS Web Scraper")
    st.markdown(
        """
        Upload a `.csv` file with a list of FDMS links (1 per row). 
        The scraper will check if the page contains:
        - "Invoice is valid"
        - "Credit note is valid"

        Pages without these will be scanned for **validation errors**.
        """
    )

    uploaded_file = st.file_uploader("Upload CSV file with links", type="csv")
    if uploaded_file:
        urls = [row[0] for row in csv.reader(uploaded_file.read().decode("utf-8").splitlines()) if row and row[0].strip()]
        st.success(f"✅ Loaded {len(urls)} links")

        if st.button("🚀 Start Scraping"):
            st.markdown("### ⏳ Scraping in progress...")
            progress = st.progress(0)
            status_placeholder = st.empty()

            results = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_url = {executor.submit(scrape_url, url): url for url in urls}

                for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = [url, f"Error: Exception - {exc}", "", ""]
                    results.append(result)
                    progress.progress((i + 1) / len(urls))
                    status_placeholder.markdown(f"Scraped: {i+1}/{len(urls)}")

            # Display DataFrame
            df_results = pd.DataFrame(
                [[r[0], r[1], r[3]] for r in results],
                columns=["URL", "Result", "Validation Error"]
            )
            st.markdown("### 📊 Results Summary")
            st.dataframe(df_results)

            # Show Not Found HTML Previews
            not_found_pages = [r for r in results if r[1] == "Not Found" and r[2]]
            if not_found_pages:
                st.markdown("### 👀 Preview of 'Not Found' Pages with Validation Errors")
                for url, status, html, errors in not_found_pages:
                    with st.expander(f"🔗 {url}"):
                        if errors:
                            st.error(f"🚫 Validation Error(s):\n{errors}")
                        else:
                            st.info("ℹ️ No validation error messages found.")
                        components_html(html, height=500, scrolling=True)

            # Allow download
            st.download_button(
                label="💾 Download Results CSV",
                data=df_results.to_csv(index=False).encode("utf-8"),
                file_name="fdms_results.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
