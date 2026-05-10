# 🔍 Fact-Checking Agent (The "Truth Layer")

An automated web application designed to act as a **Truth Layer** against hallucinated or outdated marketing statistics. This application reads uploaded PDFs, extracts specific claims (stats, dates, financial figures), cross-references them against live web data, and flags inaccuracies in real-time.

---

## 🚀 Features

*   **Intelligent Claim Extraction:** Uses `PyPDF2` to read raw text and the **Google Gemini API** to dynamically identify checkable claims (ignoring fluff and focusing on hard stats).
*   **Live Web Verification:** Integrates with `duckduckgo-search` to fetch real-time search context for every extracted claim, bypassing the standard knowledge cutoff limitations of LLMs.
*   **Automated Reporting:** Categorizes each claim into clear statuses:
    *   ✅ **Verified**: Matches live data.
    *   ⚠️ **Inaccurate**: Partially matches, but outdated or slightly wrong.
    *   ❌ **False**: Contradicts live data or no evidence exists.
*   **Live Metrics Dashboard:** A dynamic Streamlit UI that updates fact-check statistics in real-time as the AI processes the document.
*   **Dynamic Model Fetching:** Automatically queries the user's API key for the fastest available Gemini model to ensure stability across all accounts.

## 🛠️ Technical Stack

*   **Frontend & Framework:** Streamlit
*   **AI / LLM Engine:** Google Generative AI (Gemini)
*   **Search Engine:** DuckDuckGo Web Search API
*   **PDF Parsing:** PyPDF2
*   **Environment Management:** python-dotenv

## 💻 Local Setup

1. **Clone the repository**
```bash
git clone https://github.com/Kritarthpandey2003/factcheck-app.git
cd factcheck-app
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
streamlit run app.py
```

4. **API Key**: When the app opens in your browser, enter your free Google Gemini API key in the sidebar to begin fact-checking.

## 🌐 Live Deployment
This project is fully compatible with Streamlit Community Cloud for 1-click deployment. Simply link this repository to your Streamlit dashboard and deploy `app.py`.
