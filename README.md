# AURA-Py Sports Monitor 🏈

A real-time sports match monitoring system that tracks live FIFA games, scores, and goal events using SQLite database (no external database installation required).

## Features ✨

- **Real-time monitoring**: Live tracking of FIFA matches and scores
- **Goal detection**: Automatic detection and logging of goals with timestamps
- **SQLite database**: Local database storage (no MySQL installation needed)
- **Thread management**: Optimized concurrent monitoring of multiple matches
- **Graceful shutdown**: Proper resource cleanup and signal handling
- **Comprehensive logging**: Detailed logging for debugging and monitoring
- **Error resilience**: Robust error handling and retry mechanisms

## Requirements 📋

- Python 3.7+
- `requests` library
- SQLite (included with Python)

## Installation 🚀

1. Clone the repository:
```bash
git clone <repository-url>
cd AURA-Py
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the test suite (optional):
```bash
python3 test_system.py
```

4. Start monitoring:
```bash
python3 Aura.py
```

## Optimizations 🚀

This version includes several optimizations over the original:

- **Database**: Switched from MySQL to SQLite (no installation required)
- **Connection pooling**: Singleton pattern for database connections
- **Caching**: LRU cache for league filtering
- **Better threading**: Improved thread management and cleanup
- **Error handling**: Comprehensive error handling with logging
- **Performance**: Reduced redundant database queries and API calls
- **Resource management**: Proper cleanup and graceful shutdown

## Database Schema 📊

The SQLite database automatically creates a `matches` table with the following structure:

```sql
CREATE TABLE matches (
    id INTEGER PRIMARY KEY,
    Team1Name TEXT NOT NULL,
    Team2Name TEXT NOT NULL,
    Team1Score INTEGER DEFAULT 0,
    Team2Score INTEGER DEFAULT 0,
    League TEXT,
    GoalData TEXT DEFAULT '[]',
    status INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Configuration ⚙️

Modify `config.py` to customize:
- API endpoints and timeouts
- Database file location
- Threading parameters
- Logging settings

## Usage 📖

The system automatically:
1. Fetches live match data from the API
2. Stores match information in SQLite database
3. Monitors for goal events and score changes
4. Logs all activities with timestamps
5. Handles match completion and cleanup

Press `Ctrl+C` to stop the monitoring gracefully.

## File Structure 📁

- `Aura.py` - Main monitoring application
- `SQLiteDB.py` - Optimized SQLite database handler
- `config.py` - Configuration settings
- `test_system.py` - Test suite for validation
- `requirements.txt` - Python dependencies
- `aura.db` - SQLite database file (auto-created)

## License 📄

See LICENSE file for details.
