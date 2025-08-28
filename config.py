# Configuration file for AURA Sports Monitor

# Database settings
DATABASE_FILE = "aura.db"

# API settings
API_BASE_URL = "https://9wjrwctd2j.com/"
API_TIMEOUT = 10  # seconds
MAX_RETRIES = 3

# Threading settings
MAX_WORKERS = 50
REFRESH_INTERVAL = 5.0  # seconds between game updates
MAIN_LOOP_INTERVAL = 30  # seconds between checking for new games

# Filtering settings
EXCLUDED_LEAGUE_TERMS = ["Penalty", "3x3", "4x4", "5x5"]
MAX_START_TIME_MINUTES = 5  # Skip games that start more than this many minutes in the future

# Logging settings
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Game data settings
GAMES_COUNT = 40  # number of games to fetch from API
SPORTS_ID = 85
COUNTRY_ID = 169
PARTNER_ID = 36
