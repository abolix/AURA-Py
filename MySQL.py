import mysql.connector
import sys
import json


class MySQL:
    def __init__(self, DatabaseHost, DatabaseName, DatabaseUser, DatabasePass):
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
            print(f"Connected To {DatabaseName} .")
            self.cur = cur
            self.conn = conn
        except:
            print('Error in Connecting to Database .')
            sys.exit(1)

    def GetMatch(self, Id):
        SQLQuery = "SELECT * FROM matches WHERE id=%s"
        SQLData = (Id,)
        self.cur.execute(SQLQuery, SQLData)
        Result = self.cur.fetchone()
        if Result == None:
            # It Means Match is not in database
            return False
        return Result

    def CreateMatch(self, MatchData):
        SQLQuery = "INSERT INTO matches (id, Team1Name, Team2Name, Team1Score, Team2Score, League, GoalData) VALUES(%s,%s,%s,%s,%s,%s,%s)"
        SQLData = (MatchData['id'], MatchData['Team1Name'], MatchData['Team2Name'],
                   MatchData['Team1Score'], MatchData['Team2Score'], MatchData['League'], '[]')
        self.cur.execute(SQLQuery, SQLData)

    def FinishMatch(self, Id):
        MatchData = self.GetMatch(Id)
        if MatchData == False:
            return False
        GoalData = json.loads(MatchData['GoalData'])
        if int(MatchData['Team1Score']) + int(MatchData['Team2Score']) == len(GoalData):
            SQLQuery = "UPDATE matches SET status = 1 WHERE id = %s"
            SQLData = (Id,)
            self.cur.execute(SQLQuery, SQLData)
            return True

    def AddToGoalData(self, Id, GoalDetails):
        MatchData = self.GetMatch(Id)
        if MatchData == False:
            return False

        if GoalDetails['T'] == 1:
            TeamName = 'Team1Score'
        elif GoalDetails['T'] == 2:
            TeamName = 'Team2Score'
        GoalData = json.loads(MatchData['GoalData'])
        GoalData.append(GoalDetails)
        GoalData = json.dumps(GoalData)
        SQLQuery = "UPDATE matches SET GoalData = %s , " + \
            TeamName + " = " + TeamName + " + 1 WHERE id = %s"
        SQLData = (GoalData, Id)
        self.cur.execute(SQLQuery, SQLData)
        return True
