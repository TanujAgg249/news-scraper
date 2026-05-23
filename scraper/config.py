"""
config.py - Central Configuration
==================================

All settings and constants live here so they're easy to find and change.
Nothing is hardcoded inside the other modules.
"""

# --- Search Settings ---
# The main query sent to NewsAPI
SEARCH_QUERY = "Russia Ukraine war"

# Optional keyword filters — articles matching ANY of these get a tag
KEYWORD_FILTERS = ["oil", "sanctions", "NATO", "Zelensky", "Putin", "Drones"]

# --- Scheduling ---
# How often to fetch news (in minutes). 60 = every 1 hour.
FETCH_INTERVAL_MINUTES = 60

# --- Article Freshness ---
# Maximum age of articles to keep (in hours). Older articles are deleted.
MAX_ARTICLE_AGE_HOURS = 24

# --- File Paths ---
# Excel output file
EXCEL_FILE = "news.xlsx"

# Backup CSV file
CSV_BACKUP_FILE = "news_backup.csv"

# --- NewsAPI Settings ---
# Base URL for the NewsAPI "everything" endpoint
NEWSAPI_BASE_URL = "https://newsapi.org/v2/everything"

# Number of articles to request per call (max 100 for free tier)
PAGE_SIZE = 50

# Sort order: "publishedAt" gives newest first
SORT_BY = "publishedAt"

# Language filter
LANGUAGE = "en"

# --- Gemini AI Settings ---
# Model to use for oil market impact analysis
GEMINI_MODEL = "gemini-2.0-flash"

# Prompt template for oil market impact analysis
# {headline} and {description} will be replaced with article data
ANALYSIS_PROMPT_TEMPLATE = """You are an expert oil market analyst. Analyze this news article's 
potential impact on crude oil prices.

Headline: {headline}
Description: {description}

Classify the impact as exactly one of:
- "Bullish" if this news is likely to push oil prices UP (e.g., supply disruptions, 
  sanctions on oil producers, geopolitical escalation in oil-producing regions, OPEC cuts)
- "Bearish" if this news is likely to push oil prices DOWN (e.g., peace talks progress, 
  sanctions relief, demand reduction, increased production, ceasefire)
- "Neutral" if this news has no significant direct impact on oil prices

Respond in EXACTLY this format (no extra text):
IMPACT | One-sentence reason

Examples:
Bullish | New sanctions on Russian oil exports could reduce global supply by 1M barrels/day
Bearish | Ceasefire agreement would ease supply concerns and stabilize shipping routes
Neutral | Diplomatic meeting scheduled with no immediate policy implications for energy"""

