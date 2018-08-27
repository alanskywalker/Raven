from flask import (Flask,
                   render_template,
                   redirect,
                   url_for)
from flask import request as rq
from flask_admin import Admin
from urllib import parse
from urllib import request
from bs4 import BeautifulSoup
import jinja2
import pandas as pd
from datetime import datetime
import json
import datetime as dt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
import numpy as np


env=jinja2.Environment()
env.filters['type'] = type

app = Flask(__name__)
long =0
si=0
bun=0

import sqlite3

conn = sqlite3.connect('db/Chopin.db')
cur = conn.cursor()
cur.execute("SELECT time, long, Wait, cool, type24,Day FROM Mus")
# rows = cur.fetchall()
# haha1 = []
# haha2 = []
# haha3 = []
# haha4 = []
# for row in rows:
#     haha1.append([row[0], row[1], row[2]])
#     haha2.append(row[3])
#
#     temp = int(row[5] / 7)
#     if temp > 1:
#         temp = 1
#     else:
#         temp = 0
#     haha3.append([row[4], temp])  # 시간대
#     haha4.append(row[2])  # 대기인원
#
# y = np.array(haha2)
# X = np.array(haha1)
#
# y1 = np.array(haha4)
# X1 = np.array(haha3)

conn.close()


# X_train, X_test, y_train, y_test = train_test_split(X,y, random_state=3)
# gbrt = GradientBoostingRegressor(max_depth=10, learning_rate=0.2, n_estimators=200, random_state=0)
# gbrt.fit(X_train, y_train)
#
# X_train, X_test, y_train, y_test = train_test_split(X1,y1, random_state=3)
# gbrt2 = GradientBoostingRegressor(max_depth=10, learning_rate=0.2, n_estimators=200, random_state=0)
# gbrt2.fit(X_train, y_train)
#
# def Oracle(a,b): # a는 현재 시간대, b long 거리, Wait 대기인원
#     k1=[[a,1]]
#     c=gbrt2.predict(k1)[0]
#     k=[[a,b,c]]
#     k=np.array(k)
#     return gbrt.predict(k)[0]



def zeroplus(a):
    if a<10:
        return "0"+str(a)
    else:
        return str(a)


clock=[45,52107,52626,53454,53810,54127,54636,60342,61647,61754,63627,64730,64758,65611,70452,71025,71649,72850,72915,73846,74206,74823,75723,75800,80045,81020,82248,82340,83557,90126,93253,94317,95143,95613,100718,101728,103246,103334,104256,105827,111104,112930,114732,115411,120237,121408,122913,123536,124724,125942,130843,131732,133047,133906,134459,135034,142408,142737,143738,150226,150834,150926,151832,153725,154351,155234,155326,160557,161519,163334,163417,164311,165310,170514,170550,171621,172220,174245,174912,180011,181853,181959,182330,183905,184933,185851,191532,193413,194645,195742,200945,202252,202819,203505,204438,205343,210642,211359,212325,212418,213506,214659,220451,221709,224644,225309,231242,232417,234106]
def bust(hr, mn):
        for c in clock:
            if dt.time(hr,mn)<dt.time(int(c/10000), int((c/100)%100)):
                a, b=int(c/10000), int((c/100)%100)
                # print(a,b)
                bustime= zeroplus(a)+":"+zeroplus(b)
                return [(a*60+b)-(hr*60+mn), bustime]





conn = sqlite3.connect('db/Address.db')
address = pd.read_sql_query("SELECT * FROM Address", conn)


conn = sqlite3.connect('db/BusStation2.db')
cur = conn.cursor()
cur.execute("SELECT DISTINCT(busID) FROM BusStation2")
low_bus = []

for lb in cur.fetchall():
    low_bus.append(int(lb[0]))

conn = sqlite3.connect('db/subway_inner_path.db')

df1 = pd.read_sql_query("SELECT * FROM subway_inner_path", conn)
df2 = pd.read_excel('db/subway_transfer.xlsx')

con1 = sqlite3.connect('db/subway_timetable.db')
con2 = sqlite3.connect('db/subway_inner_path.db')
data1 = pd.read_sql_query("SELECT * FROM subway_timetable", con1)
data2 = pd.read_sql_query("SELECT * FROM subway_inner_path", con2)

conn.close()
con1.close()
con2.close()


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

        self.req = request.Request(tmapURL, data=paramBytes, headers={'appKey': "7c99ebb1-938e-4f91-a2d0-0b1db917839d",
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
    def __init__(self, on, way, code, num, off, tm, swtime,  exit, desc, walkdesc,  output_path):
        self.start = on
        self.way = way
        self.code = code
        self.num_station = num
        self.end = off
        self.sectionTm = tm
        self.swtime = swtime
        self.exit = exit
        self.desc = desc
        self.walkdesc = walkdesc
        self.output_path = output_path


class Bus:
    def __init__(self, on, code, num, off, tm, bustime, desc):
        self.start = on
        self.code = code
        self.num_station = num
        self.end = off
        self.sectionTm = tm
        self.bustime = bustime
        self.desc = desc


def subway_departure_time(line_code, current_station, next_station, for_hour, for_minute, exit):
    # line과 current_station에 승강기 이용 가능한지 탐색
    line_dic = {'1': '1호선', '2': '2호선', '3': '3호선', '4': '4호선', '5': '5호선', '6': '6호선',
                '7': '7호선', '8': '8호선', '9': '9호선', 'K': '경의선/중앙선', 'B': '분당선/수인선',
                'G': '경춘선', 'S': '신분당선', 'A': '공항철도', 'SU': '분당선/수인선'}

    ele = 0
    if (line_dic[line_code] in data2.line.unique()) and (current_station in data2.station.unique()):
        for i in data2[data2.line == line_dic[line_code]][data2.station == current_station].inner_path:
            if exit in i.split(' ↔ ')[-1]:
                for_exit = i.split(' ↔ ')[-1]
                ele = 1
                break

        # 만약 해당 출구에 승강기가 없는 경우, 승강기가 있는 출구로 반환
        if ele == 0:
            for_exit = i.split(' ↔ ')[-1]

        # 승강장에 도착한 시간 = 도착시간 + 이동시간
        moving_time = int(
            data2[data2.line == line_dic[line_code]][data2.station == current_station][data2.inner_path == i].time)
        if exit==0:
            moving_time = 0

        for_time = for_minute + moving_time

        _hour = int(for_time / 60) + for_hour
        _minute = for_time % 60

        # 승강장에 도착한 시간에서 가장 빨리오는 지하철 시간 반환
        temp = data1[data1.line == line_dic[line_code]][data1.station == current_station][
            data1.next_station == next_station]
        hour_list = list(temp.iloc[:, 7])
        minute_list = list(temp.iloc[:, 8])

        for k in range(len(hour_list)):
            if hour_list[k] >= _hour:
                if minute_list[k] >= _minute:
                    break

        if minute_list[k] < _minute:
            waiting_time = 60 + minute_list[k] - _minute
        else:
            waiting_time = minute_list[k] - _minute

        for_way_ = data2[data2.line == line_dic[line_code]][data2.station == current_station][
            data2.inner_path == i].facilities
        for l in for_way_:
            for_way = str(l).split(' ↔ ')
        for_inner_ = i.split(' ↔ ')

        output_path = []
        for cnt in range(len(for_inner_) - 1):
            output = ""
            output += (for_inner_[cnt] + "부터 " + for_inner_[cnt + 1] + "까지 " + for_way[cnt] + "로 이동")
            output_path.append(output)

        swtime = zeroplus(hour_list[k]) + ":" + zeroplus(minute_list[k])
        return for_exit, moving_time, waiting_time, swtime, output_path
    else:
        return False



def fullroute(sx, sy, ex, ey):  # 이용자가 입력한 출발, 목적지

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

    req = request.Request(url, data=paramBytes, headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'})
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
                    print(sub['startName'])
                    if 'startExitNo' in sub.keys():
                        print(sub['startExitNo'] + "번출구", sub['startExitX'], sub['startExitY'])
                        # 승강기 DB와 비교해서 해당 출구에 승강기가 없으면(or 사용불가능) 다른 출구로 update
                        # 승강기와 연결된 출구가 없다면 better=False, break
                        # check = 0
                        # if sub['startName'] in list(df1.station.unique()):
                        #     for k in list(df1[df1.station == sub['startName']]).inner_path:
                        #         temp = k.split('↔')
                        #         if sub['startExitNo'] == temp[-1][0:-4]:
                        #             check = 1
                        #     if check == 0:  # 해당 출구 없음, 다른 출구로 update
                        #         sub['startExitNo'] = \
                        #         list(df1[df1.station == sub['startName']].inner_path)[0].split('↔')[-1][1:-4]
                        # else:
                        #     better = False
                        #     break
                        # 좌표 수정해야함

                    #                     print(sub['endName'])
                    if 'endExitNo' in sub.keys():
                        print(sub['endExitNo']+"번출구!")
                        # 승강기 DB와 비교해서 해당 출구에 승강기가 없으면 다른 출구로 update
                        # 승강기와 연결된 출구가 없다면 better=False, break
                        # check = 0
                        # if sub['endName'] in list(df1.station.unique()):
                        #     for k in list(df1[df1.station == sub['endName']]).inner_path:
                        #         temp = k.split('↔')
                        #         if sub['endExitNo'] == temp[-1][0:-4]:
                        #             check = 1
                        #     if check == 0:  # 해당 출구 없음, 다른 출구로 update
                        #         sub['endExitNo'] = list(df1[df1.station == sub['endName']].inner_path)[0].split('↔')[
                        #                                -1][1:-4]
                        # else:
                        #     better = False
                        #     break
                        # 좌표 수정해야함
                #                     print()
                elif sub['trafficType'] == 2:  # 버스
                    temp_lane = []
                    for l in sub['lane']:
                        if l['busID'] in low_bus:
                            print(l['busID'])
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


def eachroute(better_path, si, bun):
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

                    arvlhour=(onepath['totaltime']+bun)//60
                    arvlmin=(onepath['totaltime']+bun)%60
                    arvlhour2=arvlhour+si

                    exit = '0'
                    if 'startExitNo' in subPath[index].keys():
                        exit = subPath[index]['startExitNo']
                        for_exit, moving_time, waiting_time, swtime, output_path = subway_departure_time(str(code), on, way,
                                                                                                         arvlhour2,
                                                                                                         arvlmin, exit)

                        walkdesc = "승강장까지 약 {}분 이동, 지하철 도착까지 {}분 대기".format(moving_time, waiting_time)

                    else:
                        for_exit, moving_time, waiting_time, swtime, output_path = subway_departure_time(str(code), on, way,
                                                                                                         arvlhour2,
                                                                                                         arvlmin, exit)
                        walkdesc = "지하철 도착까지 {}분 대기".format(waiting_time)
                        output_path = []



                    onepath['totaltime'] += (moving_time+waiting_time)

                    onepath[idx] = Subway(on, way, code, num, off, tm, swtime, exit, desc, walkdesc, output_path)

                    # onepath[idx] = Subway(on, way, code, num, off, tm, "10:00", "4", desc, "temp")


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

                    arvlhour=(onepath['totaltime']+bun)//60
                    arvlmin=(onepath['totaltime']+bun)%60
                    arvlhour2=arvlhour+si
                    onepath['totaltime'] += bust(arvlhour2,arvlmin)[0]

                    bustime = bust(arvlhour2,arvlmin)[1]
                    onepath[idx] = Bus(on, code, num, off, tm, bustime, desc)

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

                            # 환승 시간 플러스
                            for i in list(df2[df2.station == station].from_to):
                                if str(fromlane) in i.split(' ↔ ') and str(tolane) in i.split(' ↔ '):
                                    sectionTm = int(list(df2[df2.station == station][df2.from_to == i].time)[0][:-1])
                                    break

                            #                             sectionTm = subPath[index]['sectionTime'] + 0
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
            # gudongXY[gu][i] = [dong[address.DONG == i].PosX.iloc[0], dong[address.DONG == i].PosY.iloc[0]]
            gudongXY[gu][i] = [dong[dong.DONG == i].PosX.iloc[0], dong[dong.DONG == i].PosY.iloc[0]]

        # return render_template('index.html', address=gudong, month=month, day=day)
    xy = json.dumps(gudongXY)
    return render_template('index.html', XY = xy, address=gudong, month=month, day=day)



#
# @app.route('/getpath', methods=['POST'])
# def get_path():
#     if rq.method=="POST":
#         XY = rq.get_json()
#         sx = XY[0]
#         print(sx)
#
# 	return '', 200


stX = 126.977022
stY = 37.569758
eX = 126.997589
eY = 37.570594
wkDay = "8월27일"
departTm = "08:00"


g_pathList=[]




@app.route('/fullpath', methods=['POST'])
def full():   #출발, 목적지 좌표를 입력받아 경로를 객체로 반환

    # global stX
    # global stY
    # global eX
    # global eY
    # global wkDay
    # global departTm
    # global long
    # global si
    # global bun

    stX = float(rq.form.get("startX"))
    stY = float(rq.form.get("startY"))
    eX = float(rq.form.get("endX"))
    eY = float(rq.form.get("endY"))
    wkDay = rq.form.get("datesl")
    departTm = rq.form.get("timesl")


    print(stX, stY, eX, eY, wkDay, departTm)

    long = ((stX - eX) ** 2 + (stY - eY) ** 2) ** 0.5
    si = int(departTm[0:2])
    bun = int(departTm[3:])


    full = fullroute(stX, stY, eX, eY)
    print(len(full))
    if len(full[0]) > 7:
        full[0] = full[0][:7]

    print("1111111")

    retry = 5
    while retry > 0:
        try:
            pathList = eachroute(full, si, bun) # subPath + 메타데이터를 dict으로 담고있는 경로들의 list
            break
        except:
            retry -= 1

    print("222222")
    # 각 경로마다의 subPath를 객체로 저장 -> Pedestrian() , Subway(), Bus()
    # 웹 구현 시 각 subPath의 객체타입에 따라 보여지는 형식이 다름
    global g_pathList
    g_pathList = pathList


    taxi_wait = 20
    # taxi_wait = Oracle(si, long)

    print("OK")
    return redirect(url_for('getfull', pathList=pathList, taxi_wait=taxi_wait))  # 모든 경로를 대중교통 타입에 따라 구분하여 화면에 보여주는 html


@app.route('/getfull')
def getfull(pathList, taxi_wait):
    return render_template("fullpath.html", pathList=pathList, taxi_wait = taxi_wait)


@app.route('/subpath<onepath>', methods=["GET"])
def subpath(onepath):  # 하나의 경로를 구성하는 subpath들을 보여줌
    path = g_pathList[int(onepath)]
    # print(path)
    subpaths = []

    for p in path:
        if type(p) == int:
            subpaths.append(path[p])
    # print(subpaths)

    si = int(departTm[0:2])
    bun = int(departTm[3:])

    return render_template("subpath.html", path=subpaths, si = si, bun = bun)  # subpath들의 대중교통 타입에 따라 다른 형식으로 화면에 보여주는 html





@app.route('/get')
def gettemp():
    stX = 126.98236124865412
    stY = 37.56599776469799
    eX = 126.99458258473369
    eY = 37.56143935848331
    wkDay = "8월27일"
    departTm = "08:00"

    long = ((stX - eX) ** 2 + (stY - eY) ** 2) ** 0.5
    si = int(departTm[0:2])
    bun = int(departTm[3:])


    full = fullroute(stX, stY, eX, eY)
    print(len(full))
    if len(full[0]) > 7:
        full[0] = full[0][:7]

    pathList = eachroute(full, si, bun)
    print(2222)

    global g_pathList
    g_pathList = pathList

    taxi_wait = 20
    # taxi_wait = Oracle(si, long)

    print("OK")
    return render_template("fullpath.html", pathList=pathList, taxi_wait = taxi_wait)



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

    return render_template("subpath.html", path=subpaths, departTm = departTm)


if __name__ == '__main__':
    app.run()

