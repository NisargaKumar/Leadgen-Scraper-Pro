import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from time import sleep
import random
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")


# --- Streamlit Page Setup ---
st.set_page_config(page_title="🚀 LeadGen Scraper Pro", layout="centered")
st.markdown("<h1 style='text-align: center;'>🚀 LeadGen Scraper Pro</h1>", unsafe_allow_html=True)
st.caption("🔒 Only publicly available data is extracted. This tool respects privacy.")

# --- Helper Functions ---
def extract_domain(url):
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    return domain.split(":")[0]

def find_emails(text):
    email_regex = r"\b[A-Za-z0-9._%+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"
    return [e.lower() for e in re.findall(email_regex, text) if not e.endswith((".png", ".jpg", ".jpeg"))]

def find_social_links(text):
    patterns = {
        "LinkedIn": r"https?://(?:www\.)?linkedin\.com/(?:company/|in/)?[a-zA-Z0-9\-]+",
        "Twitter": r"https?://(?:www\.)?twitter\.com/[a-zA-Z0-9_]+",
        "Facebook": r"https?://(?:www\.)?facebook\.com/[a-zA-Z0-9.]+"
    }
    results = {}
    for platform, pattern in patterns.items():
        match = re.search(pattern, text)
        results[platform] = match.group(0) if match else "Not Found"
    return results

def google_search(query, api_key, cx, num_results=10):
    results = []
    start = 1
    while len(results) < num_results:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "start": start,
            "num": min(10, num_results - len(results))
        }
        response = requests.get(url, params=params)
        data = response.json()
        if "items" not in data:
            st.error("❌ Error fetching from Google CSE API")
            break
        for item in data["items"]:
            results.append({
                "title": item.get("title"),
                "link": item.get("link")
            })
        if "nextPage" in data.get("queries", {}):
            start = data["queries"]["nextPage"][0]["startIndex"]
        else:
            break
    return results[:num_results]

def scrape_leads(query, max_results=10):
    leads = []
    results = google_search(query, API_KEY, SEARCH_ENGINE_ID, max_results)
    progress_bar = st.progress(0)

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }

    for i, result in enumerate(results):
        try:
            sleep(random.uniform(1, 2))
            link = result["link"]
            title = result["title"]
            domain = extract_domain(link)

            lead = {
                "Company": title,
                "Website": link,
                "Domain": domain,
                "Email": "Not Found",
                "LinkedIn": "Not Found",
                "Twitter": "Not Found",
                "Facebook": "Not Found"
            }

            try:
                page = requests.get(link, headers=headers, timeout=10)
                text = page.text
                emails = find_emails(text)
                if emails:
                    lead["Email"] = emails[0]
                socials = find_social_links(text)
                lead.update(socials)
                leads.append(lead)
            except:
                continue

            progress_bar.progress((i + 1) / max_results)

        except Exception as e:
            st.error(f"❌ Error on result {i+1}: {str(e)}")
            continue

    return leads

# --- Streamlit UI ---
with st.form("scrape_form"):
    query = st.text_input("🔎 Enter your search query", placeholder="e.g., SaaS companies in California")
    max_results = st.slider("Number of results", 5, 30, 10)
    submitted = st.form_submit_button("🚀 Start Scraping")

if submitted and query:
    with st.spinner(f"🔍 Scraping leads for: {query}..."):
        leads = scrape_leads(query, max_results)

        if leads:
            df = pd.DataFrame(leads)

            st.success(f"✅ Found {len(df)} leads")

            st.subheader("🔍 Filter Results")
            col1, col2 = st.columns(2)
            with col1:
                company_filter = st.text_input("Filter by company name")
            with col2:
                domain_filter = st.text_input("Filter by domain")

            if company_filter:
                df = df[df["Company"].str.contains(company_filter, case=False, na=False)]
            if domain_filter:
                df = df[df["Domain"].str.contains(domain_filter, case=False, na=False)]

            # Reset index and add clean S.No
            df = df.reset_index(drop=True)
            df.insert(0, "S.No", range(1, len(df) + 1))

            # Highlight social links
            def highlight_links(val):
                if val == "Not Found":
                    return "color: red;"
                elif isinstance(val, str) and val.startswith("http"):
                    return "color: green;"
                return ""

            # Display styled DataFrame (with clean index, no double S.No)
            styled_df = df.style.applymap(highlight_links, subset=["LinkedIn", "Twitter", "Facebook"])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

            # Download button
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Results as CSV", csv, f"leads_{query.replace(' ', '_')}.csv", "text/csv")
        else:
            st.warning("⚠️ No results found. Try a broader query.")

# --- Footer ---
st.markdown("---")
st.caption("🧠 Tip: Use niche search queries like `email marketing SaaS startups in Berlin` for better results.")
