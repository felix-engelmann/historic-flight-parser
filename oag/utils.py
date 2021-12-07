import re
from lxml import etree as ET
from pytz import timezone
from datetime import datetime

parser = ET.XMLParser(recover=True)
linkreg = re.compile('<a.*?</a>')

def parse_year(intro):
    apr = {}
    with open("scrape/"+intro) as fd:
        file = fd.read()
        sols = linkreg.findall(file)
        for sol in sols:
            try:
                parser = ET.XMLParser(recover=True)
                d = ET.fromstring(sol, parser)
                link = d.attrib["href"]
                link = link.split("/")[-1]
                if any([link.endswith(x) for x in ["itineraries.html","index.html"]]):
                    continue
                arr = d.find("u/font/span")
                if arr is None:
                    arr = d.find("font/span")
                arr = arr.text
                if link not in apr:
                    apr[link]=""
                apr[link]+=arr
            except Exception as e:
                print(sol, e)
    return apr

def parse_caplink(file, text="FLIGHT SCHEDULES"):
    link = None
    with open("scrape/"+file) as fd:
        cont = fd.read()
        sols = re.findall(linkreg, cont)
        for sol in sols:
            if text == "FLIGHT SCHEDULES" and file in ["AKL89intro.html","FRA89intro.html","FCO89intro.html"]:
                text = "SCHEDULES"
            if text == "FLIGHT SCHEDULES" and file in ["CDG96intro.html"]:
                text = "NEXT PAGE"
            if text in sol:
                parser = ET.XMLParser(recover=True)
                d = ET.fromstring(sol, parser)
                link = d.attrib["href"]
                link = link.split("/")[-1]
    # fix datasource error
    if text == "NEXT PAGE" and file in ["NCE83p3.html","POM83p3.html","SYD83p3.html"]:
        link = None

    return link

def parse_flights(file):
    dcol = re.compile('<div id="e.*?</div>')

    flights = []
    with open("scrape/"+file) as fd:
        cont= fd.read().replace("\n", "")
        sols = dcol.findall(cont)
        cols = {}
        tkeys = ['Arriving From', 'Airline', 'Flight', 'Departs', 'Arrives', 'Stops', 'Equipment', 'Frequency']
        for sol in sols:
            col = []
            parts = sol.split("<br")
            #print(parts)
            for p in parts:
                remain = re.sub(r'\<[^>]*\>', "", p)
                name = remain.split(">")[-1].replace("&nbsp;","").strip()
                if name in ['.',',','/','..',',.',';']:
                    continue
                col.append(name)
            cols[col[0]] = col[1:]
            #print(col)

        # fix errors in datasource
        if file == "LHR83p6.html":
            cols["Airline"].insert(len(cols["Airline"])-4,'Ethiopian')
        if file in ["NBO83p1.html","LHR89p4.html","ORY89p7.html"]:
            cols["Stops"] = cols["Meals"]
        if file == "NUE83p1.html":
            cols["Stops"] = cols["Stop"]
        if file in ["ORY89p7.html","SJJ89p1.html"]:
            cols["Departs"] = cols["Depart"]
        if file == "POM89p1.html":
            cols["Arriving From"] = cols["Arriving from:"]
        if file == "MEL89p1.html":
            cols["Equipment"] = cols["Equipment72S"]
        if file == "SIN89p4.html":
            cols["Equipment"] = cols["Daily"]
        if file == "BKK89p2.html":
            cols["Frequency"][98] = ''
        if file == "OOL89p1.html":
            cols["Frequency"][61] = ''
        if file == "CDG96p8.html":
            cols["Frequency"][68] = ''
        if file == "LHR96p5.html":
            cols["Equipment"] = cols["quipment"]
        
            
            
        allheads = list(cols.keys())
        for k in allheads:
            if k not in tkeys:
                del cols[k]
        
        assert set(cols.keys()) == set(tkeys), f"keys fail in {file}: miss {set(tkeys)-set(cols.keys())} is: {cols.keys()}, original: {allheads}"
            
        for header, col in cols.items():
            assert len(col) == len(cols['Flight']), f"{file}, {header}, {col}"

        for line, dep in enumerate(cols['Arriving From']):
            if dep == '':
                for k,col in cols.items():
                    assert col[line].strip() == '', f"broken table in {file}, line: {line}: {[(i,a) for i,a in enumerate(col)]}"
            else:
                fli = {}
                for hdr, col in cols.items():
                    fli[hdr] = col[line]
                flights.append(fli)
    return flights

def get_tztime(t,tz, scheddate):
    dayo = t.split("+")
    addday=0
    if len(dayo) > 1:
        addday = int(dayo[1])
    timeo = dayo[0].split(":")
    minute = 0
    if len(timeo) == 2:
        hour = int(timeo[0])
        minute = int(timeo[1][:-2])
    else:
        hour = int(timeo[0][-4:-2])
        minute = int(timeo[0][:-4])

    if dayo[0][-2:].lower() == "am" and hour == 12:
        hour = 0
    elif dayo[0][-2:].lower() == "pm" and hour < 12:
        hour += 12
    localtz = timezone(tz)
    deptime = datetime(scheddate.year,scheddate.month,scheddate.day+addday, hour, minute)
    deptime = localtz.localize(deptime)
    return deptime