import requests
import json
import math

SiteURL = "https://1xirspiwj.com/"


def TrueArray(Arr):
    for ArrItem in Arr:
        if ArrItem == False:
            return False
        return True


def GetGamesList():
    SportData = requests.get(
        SiteURL + "LiveFeed/Get1x2_VZip?sports=85&count=10&lng=en&mode=4&cyberFlag=1&country=75&partner=36&getEmpty=true").text

    SportData = json.loads(SportData)
    SportData = SportData['Value']
    ReturnData = []
    for Match in SportData:
        MatchID = Match['I']
        League = Match['L']
        try:
            Status = Match['SC']['CPS']
        except KeyError:
            try:
                Status = Match['SC']['I']
            except KeyError:
                Status = 0  # Null

        if(League.find("Penalty") == -1 and League.find("3x3") == -1 and League.find("4x4") == -1):
            ReturnData.append(
                {'MatchID': MatchID, 'League': League, 'Status': Status})

    return ReturnData


def GetGame(ID):
    GameData = requests.get(
        SiteURL + f"LiveFeed/GetGameZip?id={ID}&lng=en&cfview=0&isSubGames=true&GroupEvents=true&allEventsGroupSubGames=true&countevents=250&partner=36").text
    GameData = json.loads(GameData)
    GameData = GameData['Value']
    try:
        TimeAll = GameData['SC']['TS']
    except KeyError:
        TimeAll = 0
    TimeMinute = math.floor(TimeAll / 60)
    TimeSecond = TimeAll - (TimeMinute * 60)
    TimeMinute = "{0:0=2d}".format(TimeMinute)
    TimeSecond = "{0:0=2d}".format(TimeSecond)
    Team1Name = GameData['O1']
    Team2Name = GameData['O2']

    OddLockArr = []
    LockData = GameData['GE']
    for LockGE in LockData:
        ArrayData = LockGE['E']
        for LockGF in ArrayData:
            for LockGG in LockGF:
                try:
                    OddLock = LockGG['B']
                    OddLockArr.append(OddLock)
                except KeyError:
                    OddLock = False

    if TrueArray(OddLockArr) and len(OddLockArr) >= 5:
        print('Odd Lock :/')

    try:
        Team1Score = GameData['SC']['FS']['S1']
    except KeyError:
        Team1Score = 0

    try:
        Team2Score = GameData['SC']['FS']['S2']
    except KeyError:
        Team2Score = 0

    # League = GameData['L']
    try:
        Status = GameData['SC']['I']
    except KeyError:
        Status = "Game in Progress"
        # Half time | Game in Progress | Match finished | Pre-match bets

    if Status == "Pre-match bets" or Status == "Pre-game betting":
        Status = "Game is not started yet"
        print(f"{Team1Name} vs {Team2Name}")
        print(f"Remaining time to start : {TimeMinute}:{TimeSecond}")
    else:
        print(f"{Team1Name} vs {Team2Name} , {TimeMinute}:{TimeSecond} , {Team1Score}:{Team2Score} , {Status}")

    print('---------------')


AllData = GetGamesList()

for Game in AllData:
    MatchID = Game['MatchID']
    # print(Game['Status'])
    GetGame(MatchID)
