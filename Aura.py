import requests
import json
import threading
import math
from SQLiteDB import SQLiteDB
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import signal
import config

# Configure logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format=config.LOG_FORMAT)
logger = logging.getLogger(__name__)

# Configuration
DB_FILE = config.DATABASE_FILE
SITEURL = config.API_BASE_URL
MAX_WORKERS = config.MAX_WORKERS  # Limit concurrent threads
REFRESH_INTERVAL = config.REFRESH_INTERVAL  # Seconds between game updates
API_TIMEOUT = config.API_TIMEOUT  # API request timeout

# Global variables
CheckedMatches = set()  # Use set for faster lookups
active_threads = {}  # Track active threads
shutdown_event = threading.Event()
db_instance = None

# Session for connection pooling
session = requests.Session()
session.timeout = API_TIMEOUT


def signal_handler(signum, frame):
    """Handle shutdown gracefully"""
    logger.info("Shutting down gracefully...")
    shutdown_event.set()
    if db_instance:
        db_instance.close()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def TrueArray(arr):
    """Check if all elements in array are truthy - optimized"""
    return all(arr) if arr else False


@lru_cache(maxsize=128)
def should_process_league(league):
    """Cached check for league filtering"""
    return not any(term in league for term in config.EXCLUDED_LEAGUE_TERMS)


def should_monitor_game(status, time_all):
    """Check if game should be monitored based on status and start time"""
    if status in ["Pre-match bets", "Pre-game betting"]:
        # If game hasn't started and starts in more than configured minutes, skip it
        max_seconds = config.MAX_START_TIME_MINUTES * 60
        if time_all > max_seconds:
            return False
    return True


def make_api_request(url, max_retries=None):
    """Make API request with retry logic and better error handling"""
    if max_retries is None:
        max_retries = config.MAX_RETRIES

    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=API_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.warning(f"API request timeout (attempt {attempt + 1})")
        except requests.exceptions.RequestException as e:
            logger.warning(f"API request failed (attempt {attempt + 1}): {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")

        if attempt < max_retries - 1:
            time.sleep(1)  # Brief delay before retry

    logger.error(f"Failed to fetch data from {url} after {max_retries} attempts")
    return None


def GetGamesList():
    """Optimized games list fetching"""
    api_url = f"{SITEURL}/service-api/LiveFeed/Get1x2_VZip?sports={config.SPORTS_ID}&count={config.GAMES_COUNT}&lng=en&gr=666&mode=4&country={config.COUNTRY_ID}&partner={config.PARTNER_ID}&getEmpty=true&virtualSports=true&noFilterBlockEvent=true"

    sport_data = make_api_request(api_url)
    if not sport_data or 'Value' not in sport_data:
        logger.error("Failed to fetch games list")
        return []

    return_data = []
    for match in sport_data['Value']:
        try:
            match_id = match['I']
            league = match['L']

            # Get status with better error handling
            status = 0
            if 'SC' in match:
                status = match['SC'].get('CPS', match['SC'].get('I', 0))

            # Use cached league filtering
            if should_process_league(league):
                return_data.append({
                    'MatchID': match_id,
                    'League': league,
                    'Status': status
                })
        except KeyError as e:
            logger.warning(f"Incomplete match data: {e}")
            continue

    logger.info(f"Found {len(return_data)} valid matches")
    return return_data


def GetGame(match_id):
    """Optimized game monitoring function"""
    global db_instance

    if shutdown_event.is_set():
        return

    # Check for duplicate threads more efficiently
    thread_count = sum(1 for thread in threading.enumerate()
                      if hasattr(thread, 'name') and str(thread.name) == str(match_id))

    if thread_count >= 2:
        logger.info(f"Eliminating duplicate thread for match {match_id}")
        return

    # Initialize database connection if not exists
    if not db_instance:
        db_instance = SQLiteDB(DB_FILE)

    CheckedMatches.add(match_id)

    # Fetch game data
    api_url = f"{SITEURL}/service-api/LiveFeed/GetGameZip?id={match_id}&lng=en&cfview=0&isSubGames=true&GroupEvents=true&allEventsGroupSubGames=true&countevents=250&partner=36"

    game_data = make_api_request(api_url)
    if not game_data or 'Value' not in game_data:
        logger.error(f"Failed to fetch game data for match {match_id}")
        return

    game_info = game_data['Value']

    try:
        # Extract game information with better defaults
        time_all = game_info.get('SC', {}).get('TS', 0)
        league = game_info.get('L', 'Unknown League')
        team1_name = game_info.get('O1', 'Team 1')
        team2_name = game_info.get('O2', 'Team 2')
        the_half = game_info.get('SC', {}).get('CP', 0)

        # Calculate time
        time_minute = math.floor(time_all / 60) if time_all else 0
        time_second = time_all - (time_minute * 60) if time_all else 0
        time_minute = f"{time_minute:02d}"
        time_second = f"{time_second:02d}"

        # Get scores with defaults
        team1_score = game_info.get('SC', {}).get('FS', {}).get('S1', 0)
        team2_score = game_info.get('SC', {}).get('FS', {}).get('S2', 0)

        # Get status
        status = game_info.get('SC', {}).get('I', "Game in Progress")

        # Check if we should monitor this game based on status and start time
        if not should_monitor_game(status, time_all):
            logger.info(f"Skipping match {match_id}: {team1_name} vs {team2_name} - starts in {math.floor(time_all/60)} minutes")
            if match_id in active_threads:
                del active_threads[match_id]
            return

        # Check for odd locks (optimized)
        odd_lock_count = 0
        if 'GE' in game_info:
            for lock_ge in game_info['GE']:
                if 'E' in lock_ge:
                    for lock_gf in lock_ge['E']:
                        for lock_gg in lock_gf:
                            if lock_gg.get('B', False):
                                odd_lock_count += 1

        if odd_lock_count >= 5:
            logger.warning(f"Odd lock detected for match {match_id}")

        # Check for goals and update database
        stored_match = db_instance.GetMatch(match_id)
        if stored_match:
            # Check for new goals
            if stored_match['Team1Score'] != team1_score:
                logger.info(f"🥅 GOAL! Team 1 scored in match {match_id}")
                goal_details = {'H': the_half, 'M': int(time_minute), 'T': 1}
                db_instance.AddToGoalData(match_id, goal_details)

            if stored_match['Team2Score'] != team2_score:
                logger.info(f"🥅 GOAL! Team 2 scored in match {match_id}")
                goal_details = {'H': the_half, 'M': int(time_minute), 'T': 2}
                db_instance.AddToGoalData(match_id, goal_details)
        else:
            # Create new match record
            match_object = {
                'id': match_id,
                'Team1Name': team1_name,
                'Team2Name': team2_name,
                'Team1Score': team1_score,
                'Team2Score': team2_score,
                'League': league
            }
            db_instance.CreateMatch(match_object)
            logger.info(f"Created new match record: {team1_name} vs {team2_name}")

        # Handle match finish
        if status == "Match finished":
            db_instance.FinishMatch(match_id)
            logger.info(f"Match {match_id} finished: {team1_name} {team1_score}-{team2_score} {team2_name}")
            if match_id in active_threads:
                del active_threads[match_id]
            return

        # Log match status
        logger.info(f"Match {match_id}: {team1_name} vs {team2_name}")
        if status in ["Pre-match bets", "Pre-game betting"]:
            logger.info(f"  ⏱️ Starts in: {time_minute}:{time_second}")
        else:
            logger.info(f"  ⚽ {team1_score}:{team2_score} | {time_minute}:{time_second} | {status}")
            logger.info(f"  🏆 League: {league}")

        # Schedule next update if not shutting down
        if not shutdown_event.is_set():
            timer = threading.Timer(REFRESH_INTERVAL, GetGame, args=(match_id,))
            timer.name = str(match_id)
            timer.daemon = True
            active_threads[match_id] = timer
            timer.start()

    except Exception as e:
        logger.error(f"Error processing match {match_id}: {e}")

    finally:
        # Clean up thread tracking
        if match_id in active_threads and active_threads[match_id] != threading.current_thread():
            pass  # Keep the reference for active timer


def StartProject():
    """Optimized project startup with better resource management"""
    global db_instance

    logger.info("🚀 Starting AURA Sports Monitor...")

    # Initialize database
    db_instance = SQLiteDB(DB_FILE)

    while not shutdown_event.is_set():
        try:
            # Get active games
            all_games = GetGamesList()

            if not all_games:
                logger.warning(f"No games found, retrying in {config.MAIN_LOOP_INTERVAL} seconds...")
                time.sleep(config.MAIN_LOOP_INTERVAL)
                continue

            # Start monitoring new games
            new_matches = 0
            for game in all_games:
                match_id = game['MatchID']

                # Skip if already being monitored
                if match_id in active_threads:
                    continue

                # Check if match is finished in database
                stored_match = db_instance.GetMatch(match_id)
                if stored_match and stored_match.get('status') == 1:
                    continue

                # Quick pre-check: Don't even start monitoring games that start too far in future
                # We need to fetch basic game info to check start time
                api_url = f"{SITEURL}/service-api/LiveFeed/GetGameZip?id={match_id}&lng=en&cfview=0&isSubGames=true&GroupEvents=true&allEventsGroupSubGames=true&countevents=250&partner=36"
                quick_check_data = make_api_request(api_url)

                if quick_check_data and 'Value' in quick_check_data:
                    game_info = quick_check_data['Value']
                    time_all = game_info.get('SC', {}).get('TS', 0)
                    status = game_info.get('SC', {}).get('I', "Game in Progress")

                    # Skip if game starts too far in the future
                    if not should_monitor_game(status, time_all):
                        logger.info(f"Skipping match {match_id} - starts in {math.floor(time_all/60) if time_all else 0} minutes")
                        continue

                # Start monitoring this match
                timer = threading.Timer(REFRESH_INTERVAL, GetGame, args=(match_id,))
                timer.name = str(match_id)
                timer.daemon = True
                active_threads[match_id] = timer
                timer.start()
                new_matches += 1

            logger.info(f"Monitoring {len(active_threads)} matches ({new_matches} new)")

            # Clean up finished threads
            finished_threads = []
            for match_id, thread in active_threads.items():
                if not thread.is_alive():
                    finished_threads.append(match_id)

            for match_id in finished_threads:
                del active_threads[match_id]

            # Wait before next iteration
            time.sleep(config.MAIN_LOOP_INTERVAL)

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(10)  # Wait before retrying


if __name__ == "__main__":
    try:
        StartProject()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        shutdown_event.set()
        if db_instance:
            db_instance.close()
        logger.info("Application shutdown complete")
