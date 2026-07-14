"""
Default RSS feed URLs and seed topic definitions for EnergyPulse.
"""

# ---------------------------------------------------------------------------
# Static RSS feeds (always checked regardless of topic)
# ---------------------------------------------------------------------------
DEFAULT_RSS_FEEDS: list[str] = [
    "https://oilprice.com/rss/main",
    "https://news.google.com/rss/search?q=energy+oil+site:reuters.com",
    "https://news.google.com/rss/search?q=energy+oil+site:bloomberg.com",
]

# ---------------------------------------------------------------------------
# Seed topics — inserted on first startup if the topics table is empty
# ---------------------------------------------------------------------------
DEFAULT_TOPICS: list[dict] = [
    {
        "name": "Russia-Ukraine Energy Impact",
        "query": "Russia Ukraine oil gas energy sanctions",
        "rss_feeds": [],
        "keywords": [
            "Russia", "Ukraine", "Gazprom", "Nord Stream", "sanctions",
            "pipeline", "energy war", "gas supply", "LNG",
        ],
    },
    {
        "name": "OPEC+ & Oil Production",
        "query": "OPEC oil production crude output",
        "rss_feeds": [],
        "keywords": [
            "OPEC", "OPEC+", "production cut", "output", "quota",
            "barrel", "Saudi Arabia", "crude production",
        ],
    },
    {
        "name": "Freight & Shipping",
        "query": "oil tanker freight shipping crude cargo",
        "rss_feeds": [],
        "keywords": [
            "tanker", "freight", "shipping", "VLCC", "Suezmax",
            "cargo", "charter", "vessel", "maritime",
        ],
    },
    {
        "name": "Refinery Operations",
        "query": "refinery output capacity maintenance operations",
        "rss_feeds": [],
        "keywords": [
            "refinery", "refining", "maintenance", "turnaround",
            "capacity", "throughput", "distillation", "crack spread",
        ],
    },
    {
        "name": "Energy Sanctions",
        "query": "energy sanctions crude oil embargo",
        "rss_feeds": [],
        "keywords": [
            "sanctions", "embargo", "ban", "restriction",
            "Iran", "Venezuela", "price cap", "compliance",
        ],
    },
]
