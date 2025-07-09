import streamlit as st
import requests
from textblob import TextBlob
import pandas as pd
import en_core_web_sm

# Load spaCy model as a Python package (streamlit cloud-safe)
nlp = en_core_web_sm.load()

# --- ESG Risk Keywords ---
risk_keywords = {
    "labor": {
        "child labor": 3, "forced labor": 3, "modern slavery": 3,
        "unsafe working conditions": 2, "low wages": 1, "wage theft": 2,
        "long working hours": 1, "union suppression": 2, "worker abuse": 2,
        "discrimination": 1, "gender-based violence": 2, "sexual harassment": 2,
        "exploitation": 2, "labor violations": 2, "migrant worker abuse": 2,
        "hazardous working conditions": 2, "worker deaths": 3, "unpaid overtime": 2
    },
    "environment": {
        "pollution": 2, "deforestation": 3, "biodiversity loss": 3,
        "habitat destruction": 3, "toxic waste": 3, "chemical spill": 2,
        "oil spill": 3, "greenhouse gas emissions": 2, "carbon emissions": 2,
        "illegal dumping": 2, "tailings dam": 3, "mining disaster": 3,
        "climate impact": 2, "resource depletion": 2
    },
    "governance": {
        "sanctions": 2, "fraud": 3, "corruption": 3, "bribery": 3,
        "money laundering": 3, "non-compliance": 2, "whistleblower retaliation": 2,
        "anti-competitive behavior": 2, "data breach": 2, "lawsuit": 2,
        "criminal charges": 3, "governance failure": 2
    }
}

# --- Article Text Extraction ---
def get_full_text(url):
    try:
        token = "070489d54ba6e1dbb01ff6c8ca766530"
        api_url = f"https://api.diffbot.com/v3/article?token={token}&url={url}"
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if "objects" in data and len(data["objects"]) > 0:
            return data["objects"][0].get("text", "")
        return ""
    except Exception:
        return ""

# --- Risk Assessment ---
def assess_article(title, snippet, url, full_text, weights):
    combined = f"{title} {snippet} {full_text}".lower()
    sentiment = TextBlob(combined).sentiment.polarity
    risk_scores = {k: 0 for k in risk_keywords}
    for category, terms in risk_keywords.items():
        for kw, severity in terms.items():
            if kw in combined:
                risk_scores[category] += severity
    weighted_score = (
        risk_scores["labor"] * weights["labor"] +
        risk_scores["environment"] * weights["environment"] +
        risk_scores["governance"] * weights["governance"]
    ) / 100
    return {
        "Labor Risk": risk_scores["labor"],
        "Environmental Risk": risk_scores["environment"],
        "Governance Risk": risk_scores["governance"],
        "Sentiment": sentiment,
        "Weighted Risk Score": round(weighted_score, 2),
        "URL": url,
        "Title": title
    }

# --- Extract Companies from Article Text ---
def extract_suppliers(text):
    doc = nlp(text)
    return list(set(ent.text.strip() for ent in doc.ents if ent.label_ == "ORG"))

# --- Google Custom Search ---
def search_articles(query):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": "AIzaSyCEWC7rZUu8EDPFeVtNsWrsdBv0HVcJ_dg",
        "cx": "57a79da21c554499f",
        "q": query,
        "num": 5
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return [{
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet", "")
        } for item in data.get("items", [])]
    except Exception:
        return []

# --- Streamlit UI ---
st.set_page_config(page_title="Supplier Risk Finder", layout="wide")
st.title("🔎 Supplier Risk Finder by Material")

material = st.text_input("Enter a material (e.g., cobalt, lithium):")

col1, col2, col3 = st.columns(3)
with col1:
    labor_weight = st.slider("Labor Risk %", 0, 100, 40, step=5)
with col2:
    env_weight = st.slider("Environmental Risk %", 0, 100, 30, step=5)
with col3:
    gov_weight = st.slider("Governance Risk %", 0, 100, 30, step=5)

if labor_weight + env_weight + gov_weight != 100:
    st.warning("Total weightings must equal 100%.")
elif st.button("Find Best Supplier"):
    if not material:
        st.error("Please enter a material.")
    else:
        with st.spinner("🔍 Searching and analyzing articles..."):
            weights = {"labor": labor_weight, "environment": env_weight, "governance": gov_weight}
            query = f"{material} ESG supplier mining ethics human rights environment"
            results = search_articles(query)

            supplier_data = {}

            for result in results:
                title = result["title"]
                url = result["link"]
                snippet = result["snippet"]
                full_text = get_full_text(url)
                if not full_text.strip():
                    continue
                orgs = extract_suppliers(full_text)
                if not orgs:
                    continue
                assessment = assess_article(title, snippet, url, full_text, weights)
                for org in orgs:
                    supplier_data.setdefault(org, []).append(assessment)

            if not supplier_data:
                st.warning("No suppliers identified in articles.")
            else:
                summary = []
                for supplier, entries in supplier_data.items():
                    avg_score = sum(e["Weighted Risk Score"] for e in entries) / len(entries)
                    summary.append({
                        "Supplier": supplier,
                        "Average Risk Score": round(avg_score, 2),
                        "Articles Found": len(entries)
                    })
                df_summary = pd.DataFrame(summary).sort_values("Average Risk Score")
                st.markdown("### 🧾 Supplier Risk Summary")
                st.dataframe(df_summary)

                top = df_summary.iloc[0]
                st.success(f"""
🥇 **Recommended Supplier**: {top['Supplier']}  
- **Avg Risk Score:** {top['Average Risk Score']} / 10  
- **Articles Analyzed:** {top['Articles Found']}
""")
