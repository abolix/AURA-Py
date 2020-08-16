import mysql.connector
import sys

DB_NAME = "aura"
DB_USER = "root"
DB_PASS = "VC430ndwt8"
DB_HOST = "localhost"



def DBConnect(DatabaseHost,DatabaseName,DatabaseUser,DatabasePass):
    try:
        conn = mysql.connector.connect(
        host=DatabaseHost,
        database=DatabaseName,
        user=DatabaseUser,
        password=DatabasePass
        )
        conn.autocommit = True
        # conn.autocommit(True)
        cur = conn.cursor(dictionary=True)
        print(f"Connected To {DB_NAME} .")
        return conn , cur
    except:
        print('Error in Connecting to Database .')
        sys.exit(1)

conn, cur = DBConnect(DB_HOST,DB_NAME, DB_USER,DB_PASS)

def GetMatch(Id):
    SQLQuery = "SELECT * FROM matches WHERE id=%s"
    SQLData = (Id,)
    cur.execute(SQLQuery, SQLData)
    Result = cur.fetchone()
    if Result == None:
        # It Means Match is not in database
        return False
    return Result


def CreateMatch(MatchData):
    SQLQuery = "INSERT INTO matches (id, Team1Name, Team2Name, Team1Score, Team2Score, GoalData) VALUES(%s,%s,%s,%s,%s,%s,%s)"
    SQLData = (MatchData['id'],MatchData['Team1Name'], MatchData['Team2Name'], MatchData['Team1Score'],MatchData['Team2Score'],'[]')
    cur.execute(SQLQuery,SQLData)