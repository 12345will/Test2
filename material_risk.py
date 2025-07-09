import streamlit as st
import requests
import pandas as pd
from textblob import TextBlob
import en_core_web_sm

# Load spaCy model (installed as a package)
nlp = en_core_web_sm.load()

# --- ESG Keyword Dictionary ---
risk_keywords = {
    "labor": ["child labor", "forced labor", "unsafe working", "low wages", "wage theft"],
    "environment": ["pollution", "deforestation", "toxic waste", "mining disaster", "carbon emissions"],
    "governance": ["corruption", "fraud", "sanctions", "lawsuit", "money laundering"]
}
keyword_weights = {"labor": 3, "environment": 2, "governance": 3}

# --- Google Custom Search ---
def search_articles(material):
    query = f"{material} ESG mining ethics"
    api_key = "AIzaSyCEWC7rZUu8EDPFeVtNsWrsdBv0HVcJ_dg"
    cse_id = "57a79da21c554499f"
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cse_id, "q": query, "num": 5}
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        return res.json().get("items", [])
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

# --- Simple Full-Text Extractor (fallback if no Diffbot) ---
def get_full_text_fallback(url):
    try:
        res = requests.get(url, timeout=5)
        return res.text.lower()
    except:
        return ""

# --- Extract Company Names using spaCy ---
def extract_companies(text):
    doc = nlp(text)
    return list({ent.text.strip() for ent in doc.ents if ent.label_ == "ORG"})

# --- ESG Scoring ---
def score_article(text):
    scores = {"labor": 0, "environment": 0, "governance": 0}
    for category, keywords in risk_keywords.items():
        for kw in keywords:
            if kw in text:
                scores[category] += keyword_weights[category]
    sentiment = TextBlob(text).sentiment.polarity
    total_score = sum(scores.values())
    return total_score, scores, sentiment

# --- App UI ---
st.set_page_config("Safest Supplier Finder", layout="wide")
st.title("🔍 Safest Supplier Finder")
material = st.text_input("Enter a material (e.g., cobalt, lithium):")

if st.button("Find Safest Supplier") and material:
    with st.spinner("Searching and scoring..."):
        articles = search_articles(material)
        supplier_data = {}

        for article in articles:
            title = article.get("title", "")
            link = article.get("link", "")
            snippet = article.get("snippet", "")
            full_text = get_full_text_fallback(link)
            combined_text = f"{title} {snippet} {full_text}".lower()

            companies = extract_companies(combined_text)
            if not companies:
                continue

            score, cat_scores, sentiment = score_article(combined_text)
            for company in companies:
                supplier_data.setdefault(company, []).append({
                    "Title": title,
                    "URL": link,
                    "Risk Score": score,
                    "Sentiment": round(sentiment, 2),
                    **cat_scores
                })

        if not supplier_data:
            st.warning("No suppliers found in articles.")
        else:
            summary = []
            for company, records in supplier_data.items():
                avg_score = sum(r["Risk Score"] for r in records) / len(records)
                summary.append({
                    "Supplier": company,
                    "Avg Risk Score": round(avg_score, 2),
                    "Articles Found": len(records)
                })

            df = pd.DataFrame(summary).sort_values("Avg Risk Score")
            st.subheader("📊 Supplier Summary")
            st.dataframe(df)

            top = df.iloc[0]
            st.success(f"""
### ✅ Recommended Supplier: {top['Supplier']}
- Avg Risk Score: {top['Avg Risk Score']} / 10
- Articles Found: {top['Articles Found']}
""")
