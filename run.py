from oag.utils import *
import csv, json, os
from pytz import timezone
from datetime import datetime, date
from geopy import distance
import logging

LOGLEVEL = os.environ.get('LOGLEVEL', 'WARNING').upper()
logging.basicConfig(level=LOGLEVEL)

#scheddate = date(1983,7,1)
#scheddate = date(1989,1,15)
scheddate = date(1996, 10, 1)

aprs = parse_year(f"{scheddate.year%100}Iintro.html")

destinations = {}
for file,name in aprs.items():
    p1 = parse_caplink(file)
    pages = [p1]
    np = parse_caplink(p1,"NEXT PAGE")
    while np is not None:
        pages.append(np)
        np = parse_caplink(np,"NEXT PAGE")
    destinations[pages[0][:3]] = []
    for page in pages:
        destinations[pages[0][:3]] += parse_flights(page)

logging.info(f"parsed {len(destinations)} destinations")


flight_no = 0
for arr,fl in destinations.items():
    for f in fl:
        flight_no += 1

logging.info(f"parsed {flight_no} flights")

airports = {}
with open("airports.dat") as csvfile:
    reader = csv.DictReader(csvfile, fieldnames=["ID","Name","City","Country","IATA","ICAO","Latitude","Longitude","Altitude","Timezone","DST","Tz","Type","Source"])
    for row in reader:
        if row["Tz"] != "\\N":
            airports[row["IATA"]] = row
        else:
            logging.debug(f"ignore {row} because of missing time zone")

logging.info(f"loaded {len(airports)} airports")

histrename = {"BAK": "GYD",
              "SDA": "BGW",
              "BUH": "OTP",
              "MMA": "MMX",
              "MLH": "BSL",
              "OSA": "ITM",
              "SEL": "GMP"}

mapping = {}
if os.path.isfile("assign.json"):
    with open("assign.json") as f:
        mapping = json.load(f)

logging.info(f"loaded {len(mapping)} airport mappings")

flights = []
for dest,fl in destinations.items():
    for n in fl:
        if n["Arriving From"] in mapping and mapping[n["Arriving From"]] in airports.keys():
            n["departure"] = mapping[n["Arriving From"]]
            ndest = dest
            if dest in histrename.keys():
                #print("dest is renamens", dest)
                ndest = histrename[dest]
            if ndest not in airports.keys():
                continue
            n["destination"] = ndest

            # fix time typos:
            if n["Flight"] == 'EC 703':
                n['Arrives'] = '5:40pm'
            if n["Flight"] == 'SU 417':
                n['Departs'] = '4:50am'
            if n["Flight"] in ["OA 601",'TH 109','KL 801']:
                continue

            flights.append(n)

logging.info(f"extracted {len(flights)} flights with departure airports")

with open(f"parsedflights-{scheddate.year%100}.csv","w") as csvfile:
    fieldnames = list(sorted(list(flights[0].keys()) + ["Duration","Distance"]))
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for fl in flights:
        dep = airports[fl["departure"]]
        dst = airports[fl["destination"]]
        
        try:
            tzdep = get_tztime(fl["Departs"], dep["Tz"], scheddate)
            tzarr = get_tztime(fl["Arrives"], dst["Tz"], scheddate)
        except Exception as e:
            print(e)
            continue
        
        tzarr = tzarr.astimezone(timezone(dep["Tz"]))

        diff = (tzarr-tzdep)
        dur = diff.seconds//60+diff.days*24*60
        if dur <= 5:
            logging.debug(f"ignore negative time: {fl}")
            
        depcoor= (dep["Latitude"],dep["Longitude"])
        dstcoor= (dst["Latitude"],dst["Longitude"])
        dist = distance.distance(depcoor, dstcoor).km

        writer.writerow({**fl, "Duration":dur,"Distance":dist})
        
        
            