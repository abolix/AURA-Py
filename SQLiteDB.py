import sqlite3
import sys
import json
import os
import threading
import time
from contextlib import contextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SQLiteDB:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path="aura.db"):
        """Singleton pattern to reuse database connection"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SQLiteDB, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path="aura.db"):
        """Initialize SQLite database connection"""
        if self._initialized:
            return

        self.db_path = db_path
        self._initialized = True
        
        # Try to connect with recovery mechanism
        self._connect_with_recovery()

    def _connect_with_recovery(self):
        """Connect to database with automatic recovery on corruption"""
        try:
            self._establish_connection()
            
        except Exception as e:
            logger.error(f'Error connecting to SQLite database: {e}')
            
            # Try recovery strategies
            if "disk I/O error" in str(e) or "database is locked" in str(e) or "database disk image is malformed" in str(e):
                logger.info("Attempting database recovery...")
                
                if self._attempt_recovery():
                    logger.info("Database recovery successful, retrying connection...")
                    try:
                        self._establish_connection()
                        return
                    except Exception as recovery_error:
                        logger.error(f"Recovery failed: {recovery_error}")
                
            logger.error("Unable to recover database, exiting...")
            sys.exit(1)

    def _establish_connection(self):
        """Establish the actual database connection"""
        # Try with WAL mode first
        try:
            self.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0,
                isolation_level=None
            )
            self.conn.row_factory = sqlite3.Row
            
            # Test the connection
            self.conn.execute("PRAGMA integrity_check").fetchone()
            
            # Configure WAL mode and other optimizations
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.execute("PRAGMA cache_size=10000")
            self.conn.execute("PRAGMA temp_store=MEMORY")
            
            self._create_tables()
            logger.info(f"Connected to SQLite database: {self.db_path}")
            
        except Exception as e:
            # If WAL mode fails, try without it
            logger.warning(f"WAL mode failed ({e}), trying DELETE mode...")
            self._connect_fallback_mode()

    def _connect_fallback_mode(self):
        """Connect without WAL mode as fallback"""
        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0
        )
        self.conn.row_factory = sqlite3.Row
        
        # Use DELETE journal mode instead of WAL
        self.conn.execute("PRAGMA journal_mode=DELETE")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        
        self._create_tables()
        logger.info(f"Connected to SQLite database in fallback mode: {self.db_path}")

    def _attempt_recovery(self):
        """Attempt to recover corrupted database"""
        import os
        import shutil
        
        try:
            # Remove WAL and SHM files that might be causing issues
            wal_file = f"{self.db_path}-wal"
            shm_file = f"{self.db_path}-shm"
            
            if os.path.exists(wal_file):
                os.remove(wal_file)
                logger.info("Removed WAL file")
                
            if os.path.exists(shm_file):
                os.remove(shm_file)
                logger.info("Removed SHM file")
            
            # If database file exists, try to repair it
            if os.path.exists(self.db_path):
                backup_path = f"{self.db_path}.corrupted_{int(time.time())}"
                shutil.copy2(self.db_path, backup_path)
                logger.info(f"Backed up potentially corrupted database to {backup_path}")
                
                # Try to dump and restore the database
                try:
                    temp_conn = sqlite3.connect(self.db_path)
                    temp_conn.execute("PRAGMA integrity_check").fetchone()
                    temp_conn.close()
                    logger.info("Database integrity check passed")
                    return True
                except:
                    # Database is corrupted, create new one
                    logger.warning("Database is corrupted, creating new database...")
                    os.remove(self.db_path)
                    return True
            else:
                logger.info("Database file doesn't exist, will create new one")
                return True
                
        except Exception as recovery_error:
            logger.error(f"Recovery attempt failed: {recovery_error}")
            return False

    def _create_tables(self):
        """Create/update the matches table with proper migration"""
        try:
            # Check if table exists and get its schema
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(matches)")
            columns = {row[1] for row in cursor.fetchall()}

            if not columns:
                # Table doesn't exist, create it with full schema
                create_table_query = """
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
                )
                """
                cursor.execute(create_table_query)
                logger.info("Created new matches table")
            else:
                # Table exists, check for missing columns and add them
                if 'last_updated' not in columns:
                    cursor.execute("ALTER TABLE matches ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    logger.info("Added last_updated column to existing table")

                if 'created_at' not in columns:
                    cursor.execute("ALTER TABLE matches ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    logger.info("Added created_at column to existing table")

            # Create indexes for better performance
            create_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_match_status ON matches(status)",
                "CREATE INDEX IF NOT EXISTS idx_match_league ON matches(League)"
            ]

            for index_query in create_indexes:
                cursor.execute(index_query)

            # Create trigger to automatically update last_updated column
            if 'last_updated' in columns or not columns:  # If we added the column or it's a new table
                trigger_query = """
                CREATE TRIGGER IF NOT EXISTS update_last_modified
                AFTER UPDATE ON matches
                BEGIN
                    UPDATE matches SET last_updated = datetime('now') WHERE id = NEW.id;
                END
                """
                cursor.execute(trigger_query)

            self.conn.commit()
            cursor.close()
            logger.info("Database schema updated successfully")

        except Exception as e:
            logger.error(f"Error creating/updating tables: {e}")
            raise

    @contextmanager
    def get_cursor(self):
        """Context manager for database operations"""
        cursor = self.conn.cursor()
        try:
            yield cursor
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()

    def GetMatch(self, match_id):
        """Get match data by ID with improved error handling"""
        try:
            with self.get_cursor() as cur:
                query = "SELECT * FROM matches WHERE id = ?"
                cur.execute(query, (match_id,))
                result = cur.fetchone()

                return dict(result) if result else False

        except Exception as e:
            logger.error(f"Error getting match {match_id}: {e}")
            return False

    def CreateMatch(self, match_data):
        """Create a new match record with improved error handling"""
        try:
            with self.get_cursor() as cur:
                query = """
                INSERT OR REPLACE INTO matches
                (id, Team1Name, Team2Name, Team1Score, Team2Score, League, GoalData)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                data = (
                    match_data['id'],
                    match_data['Team1Name'],
                    match_data['Team2Name'],
                    match_data['Team1Score'],
                    match_data['Team2Score'],
                    match_data['League'],
                    '[]'
                )
                cur.execute(query, data)
                self.conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error creating match: {e}")
            return False

    def FinishMatch(self, match_id):
        """Mark a match as finished with validation"""
        try:
            match_data = self.GetMatch(match_id)
            if not match_data:
                return False

            goal_data = json.loads(match_data['GoalData'])
            total_goals = int(match_data['Team1Score']) + int(match_data['Team2Score'])

            if total_goals == len(goal_data):
                with self.get_cursor() as cur:
                    query = "UPDATE matches SET status = 1 WHERE id = ?"
                    cur.execute(query, (match_id,))
                    self.conn.commit()
                    logger.info(f"Match {match_id} marked as finished")
                    return True
            return False

        except Exception as e:
            logger.error(f"Error finishing match {match_id}: {e}")
            return False

    def AddToGoalData(self, match_id, goal_details):
        """Add goal data and update score atomically"""
        try:
            match_data = self.GetMatch(match_id)
            if not match_data:
                return False

            # Determine which team scored
            if goal_details['T'] == 1:
                team_column = 'Team1Score'
            elif goal_details['T'] == 2:
                team_column = 'Team2Score'
            else:
                return False

            # Use transaction for atomic update
            with self.get_cursor() as cur:
                # Update goal data
                goal_data = json.loads(match_data['GoalData'])
                goal_data.append(goal_details)
                goal_data_json = json.dumps(goal_data)

                # Update both goal data and team score in one transaction
                query = f"""
                UPDATE matches
                SET GoalData = ?, {team_column} = {team_column} + 1
                WHERE id = ?
                """
                cur.execute(query, (goal_data_json, match_id))
                self.conn.commit()
                logger.info(f"Goal added for match {match_id}, team {goal_details['T']}")
                return True

        except Exception as e:
            logger.error(f"Error adding goal data for match {match_id}: {e}")
            return False

    def GetActiveMatches(self):
        """Get all active (unfinished) matches"""
        try:
            with self.get_cursor() as cur:
                query = "SELECT id FROM matches WHERE status = 0"
                cur.execute(query)
                results = cur.fetchall()
                return [dict(row)['id'] for row in results]
        except Exception as e:
            logger.error(f"Error getting active matches: {e}")
            return []

    def close(self):
        """Close database connection"""
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
                logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")

    def __del__(self):
        """Ensure connection is closed when object is destroyed"""
        self.close()
