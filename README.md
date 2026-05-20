# 📰 Russia-Ukraine War News Scraper

An automated Python tool that fetches the latest news articles about the Russia-Ukraine war from [NewsAPI](https://newsapi.org/) and stores them in an Excel spreadsheet — continuously, every hour.

---

## 📁 Project Structure

```
news-scraper/
├── main.py                # Entry point — run this to start the scraper
├── scraper/
│   ├── __init__.py        # Package marker
│   ├── config.py          # All settings & constants (edit here to customize)
│   ├── fetcher.py         # Talks to NewsAPI, parses responses
│   └── storage.py         # Saves to Excel, handles deduplication, CSV backup
├── .env                   # Your API key (never commit this!)
├── .gitignore             # Keeps secrets & data files out of Git
├── requirements.txt       # Pip dependencies
├── pyproject.toml         # Project metadata (uv/pip)
└── README.md              # You're reading this
```

**Generated at runtime:**
- `news.xlsx` — The main output file with all articles
- `news_backup.csv` — Automatic CSV backup

---

## 🚀 Setup & Installation

### Step 1: Get a NewsAPI Key (Free)

1. Go to [https://newsapi.org/register](https://newsapi.org/register)
2. Sign up for a free account
3. Copy your API key from the dashboard

### Step 2: Add Your API Key

Open the `.env` file and replace the placeholder:

```env
NEWSAPI_KEY=paste_your_actual_key_here
```

### Step 3: Install Dependencies

If you're using `uv` (recommended):
```bash
uv sync
```

Or with pip:
```bash
pip install -r requirements.txt
```

### Step 4: Run the Scraper

```bash
python main.py
```

That's it! The scraper will:
1. Fetch articles **immediately**
2. Then repeat **every 60 minutes**
3. Press `Ctrl+C` to stop

---

## ⚙️ How It Works

### The Automation Loop

```
START → Fetch from NewsAPI → Deduplicate → Save to Excel → Export CSV → WAIT 60 min → REPEAT
```

1. **`main.py`** loads your API key from `.env` and starts the scheduler
2. Every cycle, **`fetcher.py`** sends a request to NewsAPI searching for "Russia Ukraine war"
3. The response is parsed — extracting headline, source, timestamp, URL
4. Articles are tagged with matching keywords (oil, sanctions, NATO, etc.)
5. **`storage.py`** loads the existing Excel file, removes duplicates, and saves
6. A CSV backup is automatically created
7. The scheduler (`schedule` library) waits 60 minutes, then repeats

### Duplicate Prevention

Every article has a **headline** and a **URL**. Before saving:
- The scraper loads all existing headlines and URLs from `news.xlsx`
- If a new article's headline OR URL already exists → **it's skipped**
- This means even if the same article appears across multiple API calls, it only gets saved **once**

### Keyword Filtering

Articles are checked against these keywords: `oil`, `sanctions`, `NATO`, `Zelensky`, `Putin`. Matches are saved in the `matched_keywords` column so you can filter in Excel.

---

## 📊 Output Columns in `news.xlsx`

| Column | Description |
|--------|-------------|
| `headline` | Article title |
| `source` | Publisher name (BBC, Reuters, etc.) |
| `published_at` | When the article was published |
| `url` | Direct link to the full article |
| `fetched_at` | When our scraper grabbed it |
| `matched_keywords` | Which filter keywords matched (e.g. "NATO, Putin") |

---

## 🔧 Customization

All settings are in **`scraper/config.py`**:

| Setting | Default | Description |
|---------|---------|-------------|
| `SEARCH_QUERY` | `"Russia Ukraine war"` | The search term |
| `KEYWORD_FILTERS` | `["oil", "sanctions", ...]` | Keywords to tag |
| `FETCH_INTERVAL_MINUTES` | `60` | How often to fetch |
| `PAGE_SIZE` | `50` | Articles per API call |

---

## 🛡️ Error Handling

The scraper handles these gracefully:
- **No internet** → Logs error, skips cycle, tries again next hour
- **API key invalid** → Clear error message telling you to check `.env`
- **API rate limit** → Logs the API error message
- **Empty responses** → Logs info, skips saving
- **Excel file locked** → Tells you to close it and retries next cycle

---

## 🧪 Required Libraries

| Library | Purpose |
|---------|---------|
| `requests` | HTTP calls to NewsAPI |
| `pandas` | DataFrame manipulation & Excel handling |
| `openpyxl` | Excel file read/write engine |
| `schedule` | Simple job scheduling (every N minutes) |
| `python-dotenv` | Load `.env` file into environment variables |

---

## 🚀 Extending Into an AI News Intelligence System

This scraper is the **data collection layer**. Here's how to build on top of it:

### Phase 2: Sentiment Analysis
- Use `TextBlob` or `transformers` to analyze headline sentiment
- Add a `sentiment_score` column (-1 to +1)
- Track how media tone changes over time

### Phase 3: Summarization
- Use OpenAI API or Hugging Face models to auto-summarize articles
- Generate daily briefings from collected articles

### Phase 4: Trend Detection
- Use `matplotlib` or `plotly` to chart article volume over time
- Detect spikes in coverage → major events happening

### Phase 5: Dashboard
- Build a Streamlit or Flask dashboard
- Show real-time article counts, keyword trends, sentiment graphs
- Add search and filter capabilities

### Phase 6: Alerts
- Send Telegram/email alerts when a spike or specific keyword is detected
- Useful for analysts tracking geopolitical developments

---

## 📝 License

This project is for educational and personal use. NewsAPI free tier is limited to 100 requests/day and does not support commercial use.
