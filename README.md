# Fact-Checking Agent

An automated web application that reads uploaded PDFs, extracts specific claims (stats, dates, financial figures), and cross-references them against live web data to flag inaccuracies.

## How it Works
1. **Extract**: Uses `PyPDF2` to read the PDF and Google Gemini API to identify checkable claims.
2. **Verify**: Uses `duckduckgo-search` to fetch live web data for each claim, and Gemini to analyze the context.
3. **Report**: Classifies each claim as `Verified`, `Inaccurate`, or `False` and provides the real facts.

## Local Setup

1. **Clone the repository**
```bash
git clone <your-repo-url>
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

4. **API Key**: When the app opens in your browser, enter your Google Gemini API key in the sidebar to begin fact-checking.

## Deployment (Streamlit Community Cloud)
1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Connect your GitHub account and select this repository.
4. Set the Main file path to `app.py`.
5. Click **Deploy**. Your app will be live within minutes!
