import streamlit as st
from groq import Groq
import pandas as pd
import sqlite3
from io import BytesIO
from fpdf import FPDF
import json

# --- CONFIGURATION ---
LANGUAGES = ["English", "Arabic"]
INDUSTRIES = {
    "Real Estate": ["GRI", "IFRS S1", "IFRS S2", "CDP", "CSRD", "SFDR"],
    "Financial Services": ["GRI", "IFRS S1", "SFDR", "CSDDD", "CDP"],
    "Manufacturing": ["GRI", "CDP", "IFRS S2", "CSRD", "CSDDD"]
}
REGIONS = ["Global", "EU", "US", "Saudi Arabia"]
WEIGHTS = {"GRI": 1.0, "IFRS S2": 1.5, "CDP": 1.2, "SFDR": 1.3}

VISION_2030_PRIORITIES = [
    "Net-zero emissions by 2060 via Saudi Green Initiative",
    "Afforestation and water reuse",
    "Saudization and local talent development",
    "Tadawul ESG Disclosure Alignment"
]

HINTS = {
    "Describe your carbon reduction strategy.": "Include Scope 1, 2, 3 targets with timelines."
}

QUESTIONS = {
    "English": {
        "GRI": ["Describe your materiality assessment process.", "What are your community engagement initiatives?"],
        "IFRS S2": ["Describe your climate transition plans."],
        "CDP": ["What is your carbon footprint baseline?"]
    },
    "Arabic": {
        "GRI": ["اشرح عملية تقييم الأهمية النسبية.", "ما هي مبادراتك في المشاركة المجتمعية؟"],
        "IFRS S2": ["اشرح خطط التحول المناخي الخاصة بك."],
        "CDP": ["ما هو خط الأساس لبصمتك الكربونية؟"]
    }
}

# --- GROQ Setup ---
client = Groq(api_key="your-groq-api-key")

# --- DB Setup ---
conn = sqlite3.connect("esg.db")
conn.execute('''CREATE TABLE IF NOT EXISTS responses (user TEXT, industry TEXT, region TEXT, framework TEXT, question TEXT, response TEXT, score REAL)''')

# --- App ---
st.set_page_config(page_title="ESG Compliance App", layout="wide")
st.title("🌍 ESG Questionnaire & Scoring App")

language = st.radio("Choose Language", LANGUAGES)
industry = st.selectbox("Select Industry", list(INDUSTRIES.keys()))
region = st.selectbox("Select Region", REGIONS)
user = st.text_input("Enter Your Name/Team", key="user")

if region == "Saudi Arabia":
    st.markdown("### Vision 2030 ESG Priorities")
    for p in VISION_2030_PRIORITIES:
        st.markdown(f"- {p}")

questions = QUESTIONS[language]
frameworks = INDUSTRIES[industry]
responses = []

for fw in frameworks:
    with st.expander(fw):
        for q in questions.get(fw, []):
            hint = HINTS.get(q)
            if hint:
                st.info(f"Hint: {hint}")
            ans = st.text_area(f"{q}", key=f"{fw}_{q}")
            responses.append({"framework": fw, "question": q, "response": ans})

if st.button("🔍 Calculate Score & Save"):
    df = pd.DataFrame(responses)
    df['score'] = df.apply(lambda row: min(len(row['response']), 100) * WEIGHTS.get(row['framework'], 1.0), axis=1)

    for _, row in df.iterrows():
        conn.execute("INSERT INTO responses VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (user, industry, region, row['framework'], row['question'], row['response'], row['score']))
    conn.commit()

    total_score = df['score'].sum()
    st.success(f"✅ Total ESG Score: {total_score}")

    # PDF Export
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"ESG Report – {industry} ({region})", ln=1)
    pdf.set_font("Arial", size=10)
    for _, row in df.iterrows():
        pdf.multi_cell(0, 10, f"{row['framework']} – Q: {row['question']}\nA: {row['response']}\nScore: {row['score']}\n")
    pdf_output = pdf.output(dest='S').encode('latin-1')
    st.download_button("Download PDF Report", pdf_output, file_name="esg_report.pdf", mime="application/pdf")

    # Excel Export
    xlsx = BytesIO()
    df.to_excel(xlsx, index=False)
    xlsx.seek(0)
    st.download_button("Download Excel", xlsx, file_name="esg_report.xlsx")

# --- AI Feedback ---
st.markdown("### 🤖 Ask ESG AI Advisor")
ai_q = st.text_area("Your ESG-related query")
if st.button("Ask Advisor"):
    ai_prompt = f"Act as ESG advisor for {industry} in {region}. Use frameworks {frameworks}. Answer: {ai_q}"
    ai_resp = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "user", "content": ai_prompt}],
        temperature=0.3
    )
    st.write(ai_resp.choices[0].message.content)
