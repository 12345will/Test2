import streamlit as st
import requests
import pandas as pd
from textblob import TextBlob
import en_core_web_sm

# Load spaCy model
nlp = en_core_web_sm.load()

# ESG keyword dictionary (light)
risk_keywords = {
    "labor": ["child labor", "forced labor", "unsafe working", "wage theft"],
    "environment": ["pollution", "deforestation", "carbon emissions", "toxic"],
    "governance": ["corruption", "fraud", "lawsuit", "sanctions"]
}
keyword_weights = {"labor": 3, "environment": 2, "governance": 3}

# Extract company names using spaCy
def extract_companies(text):
    doc = nlp(text)
    return list({ent.text for ent in doc.ents if ent.label_ == "ORG"})

# ESG scoring
def score_text(text):
    scores = {"labor": 0, "environment": 0, "governance": 0}
    for cat, keywords in risk_keywords.items():
        for kw in keywords:
            if kw in text:
                scores[cat] += keyword_weights[cat]
    total = sum(scores.values())
    sentiment = TextBlob(text).sentiment.polarity
    return total, scores, sentiment

# Google Programmable Search
def search_articles(query):
    api_key = "AIzaSyCEWC7rZUu8EDPFeVtNsWrsdBv0HVcJ_dg"
    cse_id = "57a79da21c554499f"
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cse_id, "q": query, "num": 5}
    try:
        res = requests.get(url, params=params, timeout=5)
        res.raise_for_status()
        return res.json().get("items", [])
    except Exception as e:
        st.error(f"Search failed: {e}")
        return []

# Streamlit App
st.set_page_config("Light ESG Supplier Finder", layout="wide")
st.title("🔍 Light ESG Supplier Finder")

material = st.text_input("Enter a material (e.g., cobalt, lithium):")

if st.button("Find Suppliers") and material:
    with st.spinner("Searching and analyzing..."):
        results = search_articles(f"{material} ESG supplier human rights environment")

        supplier_data = {}
        for result in results:
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            combined_text = f"{title} {snippet}".lower()

            companies = extract_companies(combined_text)
            if not companies:
                continue

            total_score, cat_scores, sentiment = score_text(combined_text)
            for supplier in companies:
                supplier_data.setdefault(supplier, []).append({
                    "Title": title,
                    "Snippet": snippet,
                    "Risk Score": total_score,
                    "Sentiment": round(sentiment, 2),
                    **cat_scores
                })

        if not supplier_data:
            st.warning("No suppliers found.")
        else:
            summary = []
            for supplier, articles in supplier_data.items():
                avg_score = sum(a["Risk Score"] for a in articles) / len(articles)
                summary.append({
                    "Supplier": supplier,
                    "Avg Risk Score": round(avg_score, 2),
                    "Mentions": len(articles)
                })

            df = pd.DataFrame(summary).sort_values("Avg Risk Score")
            st.subheader("📊 Supplier Risk Summary")
            st.dataframe(df)

            top = df.iloc[0]
            st.success(f"""
### ✅ Recommended Supplier: {top['Supplier']}
- Avg Risk Score: {top['Avg Risk Score']}  
- Mentions: {top['Mentions']}
""")
