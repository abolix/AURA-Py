import mysql.connector
import sys
import json

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
    SQLQuery = "INSERT INTO matches (id, Team1Name, Team2Name, Team1Score, Team2Score, GoalData) VALUES(%s,%s,%s,%s,%s,%s)"
    SQLData = (MatchData['id'],MatchData['Team1Name'], MatchData['Team2Name'], MatchData['Team1Score'],MatchData['Team2Score'],'[]')
    cur.execute(SQLQuery,SQLData)

def FinishMatch(Id):
    MatchData = GetMatch(Id)
    if MatchData == False:
        return False
    GoalData = json.loads(MatchData['GoalData'])
    if int(MatchData['Team1Score']) + int(MatchData['Team2Score']) == len(GoalData):
        SQLQuery = "UPDATE matches SET status = 1 WHERE id = %s"
        SQLData = (Id,)
        cur.execute(SQLQuery,SQLData)
        return True


def AddToGoalData(Id,GoalDetails):
    MatchData = GetMatch(Id)
    if MatchData == False:
        return False

    if GoalDetails['T'] == 1:
        TeamName = 'Team1Score'
    elif GoalDetails['T'] == 2:
        TeamName = 'Team2Score'
    GoalData = json.loads(MatchData['GoalData'])
    GoalData.append(GoalDetails)
    GoalData = json.dumps(GoalData)
    SQLQuery = "UPDATE matches SET GoalData = %s , " + TeamName + " = " + TeamName + " + 1 WHERE id = %s"
    SQLData = (GoalData,Id)
    cur.execute(SQLQuery,SQLData)
    return True
