import datetime
import sass
import re
import json
import yaml
import caldav
from flask import Flask, render_template, send_from_directory, jsonify
from cal_setup import get_calendar_service
from html.parser import HTMLParser
from flask_fontawesome import FontAwesome
from icalendar import Calendar, Event
from caldav.elements import dav, cdav

app = Flask(__name__)
fa = FontAwesome(app)

filesource = "./config.yaml"

# Vars
sass_map = {"static/scss/style.scss": "static/style.css"}
events = list()

# class
class HTMLFilter(HTMLParser):
    text = ""
    def handle_data(self, data):
        self.text += data

def compile_sass_to_css(sass_map):
    for source, dest in sass_map.items():
        with open(dest, "w") as outfile:
            outfile.write(sass.compile(filename=source))

def open_yaml():
    with open(filesource, 'r') as stream:
        try:
            file = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return file

def gcalendar_get(idCal):
    service = get_calendar_service()
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId= idCal, timeMin=now,
        maxResults=100, singleEvents=True,
        orderBy='startTime').execute()
    events = events_result.get('items', [])
    return events

def caldav_get(calUrl,calUser,calPass):
    client = caldav.DAVClient(url=calUrl, username=calUser, password=calPass)
    principal = client.principal()
    calendars = principal.calendars()
    events = []
    if len(calendars) > 0:
        calendar = calendars[0]
        results = calendar.date_search(datetime.datetime.now())
        for eventraw in results:
            event = Calendar.from_ical(eventraw._data)
            for component in event.walk():
                if component.name == "VEVENT":
                    eventSummary = list()
                    eventDescription = list()
                    eventDateStart = list()
                    eventdateEnd = list()
                    eventSummary.append(component.get('summary'))
                    eventDescription.append(component.get('description'))
                    startDate = component.get('dtstart')
                    eventDateStart.append(startDate.dt.strftime('%d/%m/%Y %H:%M'))
                    endDate = component.get('dtend')
                    eventdateEnd.append(endDate.dt.strftime('%d/%m/%Y %H:%M'))
                    dateStamp = component.get('dtstamp')
            data = [{ 'summary':eventSummary[0],'description':eventDescription[0],'datestart':eventDateStart[0],'dateend':eventdateEnd[0]}]
            events.append(data[0])
    return events

def update_datas(events,vTags):
    for event in events:
       if 'start' in event:
           start = event['start'].get('dateTime', event['start'].get('date'))
           event['datestart'] = datetime.datetime.fromisoformat(start).strftime("%d/%m/%y %H:%M")
       if 'end' in event:
           end = event['end'].get('dateTime', event['end'].get('date'))
           event['dateend'] = datetime.datetime.fromisoformat(end).strftime("%d/%m/%y %H:%M")
       if 'description' in event:
           # description => HTML to text
           desc = HTMLFilter()
           desc.feed(event['description'])
           event['desc'] = desc.text
           # search and clean label
           # webinar
           event['desc'] = event['desc'].replace("webinar:", " webinar:")
           event['desc'] = event['desc'].replace("url:", " url:")
           event['desc'] = event['desc'].replace("tags:", " tags:")
           event['desc'] = event['desc'].replace("city:", " city:")
           webinarparse = (searhwebinar for searhwebinar in event['desc'].split() if re.match(r"^webinar:.*", searhwebinar))
           for i in webinarparse:
             event['webinar'] = i.replace("webinar:", "").split(",")
             event['desc'] = event['desc'].replace(i , "")
           # url
           urlparse = (searhurl for searhurl in event['desc'].split() if re.match(r"^url:.*", searhurl))
           for i in urlparse:
             event['url'] = i.replace("url:", "").split(",")
             event['desc'] = event['desc'].replace(i , "")
           # tags
           tagsparse = (searhtags for searhtags in event['desc'].split() if re.match(r"^tags:.*", searhtags))
           for i in tagsparse:
             fullTags = i.replace("tags:", "").split(",")
             event['tags'] = list( d for d in fullTags if d in vTags )
             event['desc'] = event['desc'].replace(i , "")
           # city
           cityparse = (searhcity for searhcity in event['desc'].split() if re.match(r"^city:.*", searhcity))
           for i in cityparse:
             event['city'] = i.replace("city:", "").split(",")
             event['desc'] = event['desc'].replace(i , "")
    return events

@app.route('/')
def accueil():
    compile_sass_to_css(sass_map)
    file = open_yaml()
    if file['mode'] == "caldav":
      events = caldav_get(file['calUrl'],file['calUser'],file['calPass'])
      events2 = update_datas(events,file['valideTags'])
    elif file['mode'] == "googlecalendar":
      events = gcalendar_get(file['idGCalendar'])
      events2 = update_datas(events,file['valideTags'])
    else:
        print("undefine mode in yaml")
    return render_template('index.html', events=events2, file=file)

@app.errorhandler(404)
def page_not_found(e):
    compile_sass_to_css(sass_map)
    file = open_yaml()
    return render_template('404.html',file=file), 404

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/png')
@app.route('/ping')
def ping():
    return "pong"

if __name__ == '__main__':
    app.run(debug=True)