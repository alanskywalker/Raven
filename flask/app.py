from flask import (Flask,
                   render_template,
                   redirect,)
from flask import request as rq
from flask_admin import Admin
from urllib import parse
from urllib import request
from bs4 import BeautifulSoup
import jinja2
import pandas as pd
from datetime import datetime
import json

env=jinja2.Environment()
env.filters['type'] = type

app = Flask(__name__)


import sqlite3
cnx = sqlite3.connect('db/Address.db')
address = pd.read_sql_query("SELECT * FROM Address", cnx)


conn = sqlite3.connect('db/BusStation2.db')
cur = conn.cursor()
cur.execute("SELECT DISTINCT(busID) FROM BusStation2")
low_bus = []

for lb in cur.fetchall():
    low_bus.append(int(lb[0]))

conn.close()


class Pedestrian:
    # TMap API 호출 결과 반환
    def __init__(self, sx, sy, ex, ey):
        self.pos = [sx, sy, ex, ey]

        tmapURL = "https://api2.sktelecom.com/tmap/routes/pedestrian?version=1&format=xml"
        data = {
            'searchOption': 30,
            'startX': sx,
            'startY': sy,
            'endX': ex,
            'endY': ey,
            'reqCoordType': "WGS84GEO",
            'resCoordType': "EPSG3857",
            'angle': "172",
            'startName': "출발지",
            'endName': "도착지",
        }

        paramUrl = parse.urlencode(data)
        paramBytes = paramUrl.encode("utf-8")

        self.req = request.Request(tmapURL, data=paramBytes, headers={'appKey': "b9e1fdd0-0495-4f88-8b28-3e1ae2e84b19",
                                                                      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'})
        request.get_method = lambda: 'GET'
        res = request.urlopen(self.req)
        self.result = res.read().decode("utf-8")
        self.xml = BeautifulSoup(self.result, "html.parser")
        try:
            self.totaltime = int(self.xml.find("tmap:totaltime").text) // 60 + 1
            self.totaldistance = int(self.xml.find("tmap:totaldistance").text)
        except:
            print(self.xml.find("message"))


class Subway:
    def __init__(self, on, way, code, num, off, tm, desc):
        self.start = on
        self.way = way
        self.code = code
        self.num_station = num
        self.end = off
        self.sectionTm = tm
        self.desc = desc


class Bus:
    def __init__(self, on, code, num, off, tm, desc):
        self.start = on
        self.code = code
        self.num_station = num
        self.end = off
        self.sectionTm = tm
        self.desc = desc



def fullroute(sx, sy, ex, ey, wkDay, departTm):  # 이용자가 입력한 출발, 목적지
    url = "https://api.odsay.com/v1/api/searchPubTransPath"
    params = {
        'SX': sx,
        'SY': sy,
        'EX': ex,
        'EY': ey,
        'OPT': 2,
        'apiKey': "ttfS2WdLF4rG/hfj+d20/Lcxp6TIyVHnnW/IgBBHh60"
    }

    paramUrl = parse.urlencode(params)
    paramBytes = paramUrl.encode("utf-8")

    req = request.Request(url, data=paramBytes, headers={'user-agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'})
    request.get_method = lambda: 'GET'
    res = request.urlopen(req)
    result = res.read().decode("utf-8")
    resultObj = json.loads(result)

    # 경로가 존재
    try:
        pathList = resultObj['result']['path']

        # 보행약자 전용 경로로 수정
        better_path = []
        #         low_bus = [1244]   #lowbus List

        for path in pathList:
            for sub in path['subPath']:
                better = True

                if sub['trafficType'] == 1:  # 지하철
                    # print(sub['startName'])
                    if 'startExitNo' in sub.keys():
                        pass
                        # print(sub['startExitNo'] + "번출구")
                        # 승강기 DB와 비교해서 해당 출구에 승강기가 없으면(or 사용불가능) 다른 출구로 update
                        # 승강기와 연결된 출구가 없다면 better=False, break
                    # print(sub['endName'])
                    if 'endExitNo' in sub.keys():
                        pass
                        # print(sub['endExitNo'] + "번출구")
                        # 승강기 DB와 비교해서 해당 출구에 승강기가 없으면 다른 출구로 update
                        # 승강기와 연결된 출구가 없다면 better=False, break
                    # print()

                elif sub['trafficType'] == 2:  # 버스
                    temp_lane = []
                    for l in sub['lane']:
                        if l['busID'] in low_bus:
                            # print(l['busID'])
                            temp_lane.append(l)
                    # sub['lane'] = temp_lane
                    if not temp_lane:
                        better = False
                        break

            if better:
                better_path.append(path)

        return [better_path, (sx, sy, ex, ey)]

    except:
        if resultObj['error'][0]['code'] == -98:
            print("출, 도착지가 700m이내입니다.")
            return (sx, sy, ex, ey)
        else:
            print(resultObj['error'])


def eachroute(better_path):
    if type(better_path) == list:
        XY = better_path[1]
        better_path = better_path[0]

        splitpath = []

        for path in better_path:
            onepath = {'totaltime': 0, 'score': 30, 'pathType': 0, 'trans': 0, 'desc': "", 'totalwalk': 0}

            subPath = path['subPath']

            idx = 0

            for index in range(len(subPath)):
                idx += 1

                if subPath[index]['trafficType'] == 1:
                    on = subPath[index]['startName']
                    way = subPath[index]['way']
                    code = subPath[index]['lane'][0]['subwayCode']
                    num = subPath[index]['stationCount']
                    off = subPath[index]['endName']
                    tm = subPath[index]['sectionTime']
                    desc = "{}역에서 {}방향 {}호선 승차, {}정거장 후 {}역에서 하차 - 약 {}분 이동".format(on, way, code, num, off, tm)
                    onepath['desc'] += "{}역에서 {}호선 승차.  ".format(on, code)
                    onepath[idx] = Subway(on, way, code, num, off, tm, desc)
                    onepath['totaltime'] += tm
                    onepath['pathType'] = 1 if onepath['pathType'] in [0, 1] else 3

                elif subPath[index]['trafficType'] == 2:
                    on = subPath[index]['startName']
                    code = ""
                    for i in range(len(subPath[index]['lane'])):
                        if i == (len(subPath[index]['lane']) - 1):
                            code += str(subPath[index]['lane'][i]['busNo'])
                        else:
                            code += str(subPath[index]['lane'][i]['busNo']) + ", "
                    num = subPath[index]['stationCount']
                    off = subPath[index]['endName']
                    tm = subPath[index]['sectionTime']
                    desc = "<{}>에서 {}번 버스 승차, {}정거장 후 <{}>에서 하차 - 약 {}분 이동".format(on, code, num, off, tm)
                    onepath['desc'] += "<{}>에서 {}번 버스 승차.  ".format(on, code)
                    onepath[idx] = Bus(on, code, num, off, tm, desc)
                    onepath['totaltime'] += tm
                    onepath['pathType'] = 2 if onepath['pathType'] in [0, 2] else 3

                elif subPath[index]['trafficType'] == 3:
                    if index == 0:
                        # TMap에서 출발지부터 최초 정류장or지하철역 출구까지의 보행 경로 안내
                        if subPath[1]['trafficType'] == 1:
                            startX = subPath[1]['startExitX']
                            startY = subPath[1]['startExitY']
                        elif subPath[1]['trafficType'] == 2:
                            startX = subPath[1]['startX']
                            startY = subPath[1]['startY']
                        onepath[idx] = Pedestrian(XY[0], XY[1], startX, startY)
                        onepath['totaltime'] += onepath[idx].totaltime
                        onepath['totalwalk'] += onepath[idx].totaltime

                    elif index == len(subPath) - 1:
                        # TMap에서 마지막 정류장 or 지하철역 출구부터의 도착지까지의 보행 경로 안내
                        if subPath[index - 1]['trafficType'] == 1:
                            endX = subPath[index - 1]['endExitX']
                            endY = subPath[index - 1]['endExitY']
                        elif subPath[index - 1]['trafficType'] == 2:
                            endX = subPath[index - 1]['endX']
                            endY = subPath[index - 1]['endY']
                        onepath[idx] = Pedestrian(endX, endY, XY[2], XY[3])
                        onepath['totaltime'] += onepath[idx].totaltime
                        onepath['totalwalk'] += onepath[idx].totaltime

                    else:
                        #                         onepath['pass'] = []

                        if subPath[index - 1]['trafficType'] == 1 and subPath[index + 1][
                            'trafficType'] == 1:  # 지하철 - 지하철 환승
                            station = subPath[index - 1]['endName']
                            fromlane = subPath[index - 1]['lane'][0]['subwayCode']
                            tolane = subPath[index + 1]['lane'][0]['subwayCode']
                            # print(station+"역의 " +str(fromlane)+"호선에서 "+str(tolane)+"호선으로 환승")
                            # 해당 지하철역의 from호선 -> to호선까지 환승시에 걸리는 시간만큼 subPath[index]['sectionTime'] 증가
                            #                             onepath[idx] = "{}역의 {}호선에서 {}호선으로 환승".format(station, fromlane, tolane)
                            sectionTm = subPath[index]['sectionTime'] + 0
                            onepath[idx] = {'station': station, 'fromlane': fromlane, 'tolane': tolane,
                                            'sectionTm': sectionTm}
                            onepath['totaltime'] += sectionTm
                            onepath['totalwalk'] += sectionTm




                        elif subPath[index - 1]['trafficType'] == 2 and subPath[index + 1][
                            'trafficType'] == 2:  # 버스 - 버스 환승
                            startX = subPath[index - 1]['endX']
                            startY = subPath[index - 1]['endY']
                            endX = subPath[index + 1]['startX']
                            endY = subPath[index + 1]['startY']

                            onepath[idx] = Pedestrian(startX, startY, endX, endY)
                            onepath['totaltime'] += onepath[idx].totaltime
                            onepath['totalwalk'] += onepath[idx].totaltime

                        elif subPath[index - 1]['trafficType'] == 1 and subPath[index + 1][
                            'trafficType'] == 2:  # 지하철 - 버스 환승
                            startX = subPath[index - 1]['endExitX']
                            startY = subPath[index - 1]['endExitY']
                            endX = subPath[index + 1]['startX']
                            endY = subPath[index + 1]['startY']
                            onepath[idx] = Pedestrian(startX, startY, endX, endY)
                            onepath['totaltime'] += onepath[idx].totaltime
                            onepath['totalwalk'] += onepath[idx].totaltime

                        elif subPath[index - 1]['trafficType'] == 1 and subPath[index + 1][
                            'trafficType'] == 2:  # 버스 - 지하철 환승
                            startX = subPath[index - 1]['endX']
                            startY = subPath[index - 1]['endY']
                            endX = subPath[index + 1]['startExitX']
                            endY = subPath[index + 1]['startExitY']
                            onepath[idx] = Pedestrian(startX, startY, endX, endY)
                            onepath['totaltime'] += onepath[idx].totaltime
                            onepath['totalwalk'] += onepath[idx].totaltime

                        onepath['score'] -= 5  # 환승시 편의 지수 하락
                        onepath['trans'] += 1

            splitpath.append(onepath)

    elif type(better_path) == tuple:
        splitpath = [Pedestrian(*better_path)]

    return splitpath






@app.route('/')
def index():
    dt = datetime.now()
    month = dt.month
    day = dt.day
    gudong = {}
    for gu in address.GU.unique():
        for dong in address[address.GU==gu].DONG.unique():
            if gu in gudong.keys() and dong not in gudong[gu]:
                gudong[gu].append(dong)
            elif gu not in gudong.keys():
                gudong[gu] = [dong]

    gudongXY = {}
    for gu in address.GU.unique():
        gudongXY[gu] = {}
        dong = address[address.GU == gu]
        for i in dong.DONG.unique():
            gudongXY[gu][i] = [dong[address.DONG == i].PosX.iloc[0], dong[address.DONG == i].PosY.iloc[0]]

        # return render_template('index.html', address=gudong, month=month, day=day)

    return render_template('index.html', XY = gudongXY, address=gudong, month=month, day=day)



#
# @app.route('/getpath', methods=['POST'])
# def get_path():
#     if rq.method=="POST":
#         XY = rq.get_json()
#         sx = XY[0]
#         print(sx)
#
# 	return '', 200



# @app.route('/fullpath', methods=['POST'])
# def full():   #출발, 목적지 좌표를 입력받아 경로를 객체로 반환
#     if rq.method=="POST":
#         XY = rq.get_json()
#
#         for a in XY:
#             print(a)
#
#         stX = XY[0]
#         stY = XY[1]
#         eX = XY[2]
#         eY = XY[3]
#         wkDay = XY[4]
#         departTm = XY[5]
#
#     return render_template('fullpath.html')

stX = 126.977022
stY = 37.569758
eX = 126.997589
eY = 37.570594
wkDay = 6
departTm = "08:00"

# global g_pathList

@app.route('/getpath')
def getpath():
    # 이용자가 입력하는 출발, 목적지 좌표 및 시간
    full = fullroute(126.9027279,37.5349277,126.922725,37.547914, wkDay, departTm)
    print(len(full[0]))
    if len(full[0]) > 7:
        full[0] = full[0][:7]
    pathList = eachroute(full) # subPath + 메타데이터를 dict으로 담고있는 경로들의 list
    # 각 경로마다의 subPath를 객체로 저장 -> Pedestrian() , Subway(), Bus()
    # 웹 구현 시 각 subPath의 객체타입에 따라 보여지는 형식이 다름
    # g_pathList = pathList

    return render_template("fullpath.html", pathList=pathList)  # 모든 경로를 대중교통 타입에 따라 구분하여 화면에 보여주는 html

full = fullroute(126.9027279,37.5349277,126.922725,37.547914, wkDay, departTm)
if len(full[0]) > 7:
    full[0] = full[0][:7]
g_pathList = eachroute(full)

@app.route('/subpath<onepath>', methods=["GET"])
def subpath(onepath):  # 하나의 경로를 구성하는 subpath들을 보여줌
    path = g_pathList[int(onepath)]
    print(path)

    return render_template("subpath.html", path=path)  # subpath들의 대중교통 타입에 따라 다른 형식으로 화면에 보여주는 html


@app.route('/temp')
def temp():
    path = g_pathList[1]
    subpaths = []
    for p in path:
        # print(type(path[p]))
        # print(path[p])
        if type(p)==int:
            subpaths.append(path[p])
    print(subpaths)
    return render_template("subpath.html", path=subpaths)

@app.route('/sub')
def route_p():
    startX = 126.977022
    startY = 37.569758
    endX = 126.997589
    endY = 37.570594
    # passList = "126.983072,37.573028_126.987319,37.565778"
    p = Pedestrian(126.9027279 , 37.5349277, 126.922725, 37.547914)
    pathList = [(126.9027279 , 37.5349277, 126.922725, 37.547914),(startX , startY, endX, endY)]
    return render_template('templates/subpath.html', pathList=pathList,  p = p)


if __name__ == '__main__':
    app.run()

