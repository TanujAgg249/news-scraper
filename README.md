# 📰 Russia-Ukraine War News Scraper

An automated Python tool that scrapes the latest Russia-Ukraine war news, analyzes each article's impact on oil markets using **Google Gemini AI**, and outputs a professionally styled Excel file with a **live Brent Crude oil price dashboard**.

---

## ✨ Features

- 🌐 **Automated news fetching** — Pulls articles from 7,000+ sources via [NewsAPI](https://newsapi.org/)
- 🧠 **AI-powered oil market analysis** — Google Gemini classifies each article as Bullish 🟢, Bearish 🔴, or Neutral 🟠 for oil markets
- 🛢️ **Live Brent Crude dashboard** — Dark-themed Excel dashboard with real-time oil price, daily change, and trend indicators
- 🎨 **Color-coded Excel output** — Rows are colored green/red/yellow based on oil market impact
- 🔗 **Clickable article links** — URLs in Excel are proper hyperlinks
- 🗑️ **Auto-cleanup** — Articles older than 24 hours are automatically removed
- 🔄 **Hourly scheduling** — Runs continuously, fetching fresh data every hour
- 📁 **CSV backup** — Automatic backup in universal CSV format

---

## 📁 Project Structure

```
news-scraper/
├── main.py                    # Entry point — run this to start the scraper
├── scraper/
│   ├── __init__.py            # Package marker
│   ├── config.py              # All settings & constants (single source of truth)
│   ├── fetcher.py             # Talks to NewsAPI, parses responses, tags keywords
│   ├── analyzer.py            # Gemini AI oil market impact classifier
│   ├── oil_price.py           # Fetches live Brent Crude price from Yahoo Finance
│   └── storage.py             # Excel/CSV output, styling, dashboard, cleanup
├── .env                       # Your API keys (never committed to git)
├── .gitignore                 # Keeps secrets & data files out of Git
├── requirements.txt           # Pip dependencies
├── pyproject.toml             # Project metadata (uv/pip)
└── README.md                  # This file
```

**Generated at runtime:**
- `news.xlsx` — The main output: styled Excel with Dashboard + Articles sheets
- `news_backup.csv` — Automatic CSV backup of article data

---

## 🚀 Setup & Installation

### Prerequisites

- **Python 3.11+** installed
- **[uv](https://docs.astral.sh/uv/)** package manager (recommended) or pip

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/news-scraper.git
cd news-scraper
```

### Step 2: Get Your API Keys (Free)

You need **two** API keys:

| Key | Where to Get It | Free Tier |
|-----|----------------|-----------|
| **NewsAPI** | [newsapi.org/register](https://newsapi.org/register) | 100 requests/day |
| **Google Gemini** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | 15 requests/min |

### Step 3: Create Your `.env` File

Create a file called `.env` in the project root:

```env
# Get your free API key from: https://newsapi.org/register
NEWSAPI_KEY=paste_your_newsapi_key_here

# Google Gemini API key for oil market impact analysis
# Get yours from: https://aistudio.google.com/apikey
GEMINI_API_KEY=paste_your_gemini_key_here
```

### Step 4: Install Dependencies

Using **uv** (recommended):
```bash
uv sync
```

Or using **pip**:
```bash
pip install -r requirements.txt
```

### Step 5: Run the Scraper

```bash
uv run python main.py
```

Or with pip:
```bash
python main.py
```

Press **Ctrl+C** to stop.

---

## ⚙️ How It Works

### The Pipeline (every cycle)

```
Fetch Articles → AI Impact Analysis → Fetch Oil Price → Save to Excel → Export CSV → Wait 60 min → Repeat
```

1. **`main.py`** loads API keys from `.env` and starts the scheduler
2. **`fetcher.py`** sends a request to NewsAPI for "Russia Ukraine war" articles
3. Articles are parsed — extracting headline, description, source, timestamp, URL
4. Each article is tagged with matching keywords (oil, sanctions, NATO, etc.)
5. **`analyzer.py`** sends each article to Google Gemini to classify its oil market impact as Bullish, Bearish, or Neutral
6. **`oil_price.py`** fetches the live Brent Crude price from Yahoo Finance
7. **`storage.py`** loads existing data, removes articles older than 24h, deduplicates, and saves everything to a styled Excel file with a dark-themed dashboard
8. A CSV backup is automatically created
9. The scheduler waits 60 minutes, then repeats from step 2

### Duplicate Prevention

Every article has a **headline** and a **URL**. Before saving:
- The scraper loads all existing headlines and URLs from `news.xlsx`
- If a new article's headline OR URL already exists → **it's skipped**
- This means even if the same article appears across multiple API calls, it only gets saved **once**

### Keyword Tagging

Articles are checked against these keywords: `oil`, `sanctions`, `NATO`, `Zelensky`, `Putin`, `Drones`. Matches are saved in the `matched_keywords` column so you can filter in Excel. **Note:** this does NOT filter articles out — all articles are kept regardless of keyword matches.

### AI Oil Market Impact Analysis

Each article is sent to Google Gemini with a prompt that asks it to classify the article's likely impact on crude oil prices:

| Classification | Meaning | Row Color |
|---------------|---------|-----------|
| 🟢 **Bullish** | Likely to push oil prices **UP** (e.g., supply disruptions, sanctions) | Green |
| 🔴 **Bearish** | Likely to push oil prices **DOWN** (e.g., ceasefire, demand reduction) | Red |
| 🟠 **Neutral** | No significant direct impact on oil prices | Yellow |

The analyzer includes automatic retry logic with exponential backoff for rate limits.

---

## 📊 Output Columns in `news.xlsx`

| Column | Description |
|--------|-------------|
| `headline` | Article title |
| `description` | Article summary/snippet |
| `source` | Publisher name (BBC, Reuters, Al Jazeera, etc.) |
| `published_at` | When the article was published |
| `url` | Clickable link to the full article |
| `fetched_at` | When our scraper grabbed it |
| `matched_keywords` | Which keywords matched (e.g., "NATO, Putin") |
| `oil_impact` | AI classification: Bullish, Bearish, or Neutral |
| `impact_reason` | AI's one-sentence explanation for the classification |

---

## 🔧 Customization

All settings are in **`scraper/config.py`**:

| Setting | Default | Description |
|---------|---------|-------------|
| `SEARCH_QUERY` | `"Russia Ukraine war"` | The search term sent to NewsAPI |
| `KEYWORD_FILTERS` | `["oil", "sanctions", ...]` | Keywords to tag articles with |
| `FETCH_INTERVAL_MINUTES` | `60` | How often to fetch (minutes) |
| `MAX_ARTICLE_AGE_HOURS` | `24` | Auto-delete articles older than this |
| `PAGE_SIZE` | `50` | Articles per API call (max 100) |
| `GEMINI_MODEL` | `"gemini-2.0-flash"` | Which Gemini model to use |

---

## 🛡️ Error Handling

| Scenario | What Happens |
|----------|-------------|
| No internet | Logs error, skips cycle, retries next hour |
| Invalid API key | Clear error message pointing to `.env` |
| NewsAPI rate limit | Logs the API error, retries next cycle |
| Gemini rate limit | Retries 3x with backoff (15s, 30s, 45s) |
| Excel file open | Tells you to close it, retries next cycle |
| Yahoo Finance down | Dashboard shows "Price unavailable" |

---

## 📦 Dependencies

| Library | Purpose |
|---------|---------|
| `requests` | HTTP calls to NewsAPI |
| `pandas` | DataFrame manipulation & Excel I/O |
| `openpyxl` | Excel file styling, hyperlinks, formatting |
| `schedule` | Lightweight job scheduling |
| `python-dotenv` | Loads `.env` file into environment variables |
| `google-genai` | Google Gemini AI for oil impact analysis |
| `yfinance` | Live Brent Crude oil price from Yahoo Finance |

---

## 📝 Notes

- **NewsAPI free tier** is limited to 100 requests/day and does not support commercial use
- **Gemini free tier** allows ~15 requests/minute — the analyzer includes 5-second delays between requests to stay within this limit
- The `.env` file containing your API keys is **never committed** to git (protected by `.gitignore`)
- Output files (`news.xlsx`, `news_backup.csv`) are also excluded from git

---

## 📄 License

This project is for educational and personal use.
