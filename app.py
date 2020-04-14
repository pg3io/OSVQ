import datetime
import sass
import re
import yaml
from flask import Flask, render_template, send_from_directory, jsonify
from cal_setup import get_calendar_service
from html.parser import HTMLParser
from flask_fontawesome import FontAwesome

app = Flask(__name__)
fa = FontAwesome(app)


filesource = "./config.yaml"
sass_map = {"static/scss/style.scss": "static/style.css"}
labelList = ["webinar","url","tags","city"]
events = list()

class HTMLFilter(HTMLParser):
    text = ""
    def handle_data(self, data):
        self.text += data

# gen css
def compile_sass_to_css(sass_map):
    for source, dest in sass_map.items():
        with open(dest, "w") as outfile:
            outfile.write(sass.compile(filename=source))

# read yaml file
def read_yaml():
    with open(filesource, 'r') as stream:
        try:
            file = yaml.load(stream, Loader=yaml.FullLoader)
        except yaml.YAMLError as exc:
            print(exc)
    return file

# resplit label after html to text
def split_label(event,label):
    event['desc'] = event['desc'].replace(label+":", " "+label+":")
    return event

# search label to description
def search_label(event,label,vTags):
    parse = (searh for searh in event['desc'].split() if re.match(r"^"+label+":.*", searh))
    for i in parse:
        if label == "tags":
            fullTags = i.replace(label+":", "").split(",")
            event[label] = list( d for d in fullTags if d in vTags )
        else:
            event[label] = i.replace(label+":", "").split(",")
        event['desc'] = event['desc'].replace(i , "")
    return event

# get event to Google Calendar
def get_gcalendar(idCal):
    service = get_calendar_service()
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(calendarId= idCal, timeMin=now,maxResults=100, singleEvents=True,orderBy='startTime').execute()
    events = events_result.get('items', [])
    return events

# format champs for timeline
def parse_data(events,vTags):
    for event in events:
       if 'start' in event:
           start = event['start'].get('dateTime', event['start'].get('date'))
           event['datestart'] = datetime.datetime.fromisoformat(start).strftime("%d/%m/%y %H:%M")
       if 'end' in event:
           end = event['end'].get('dateTime', event['end'].get('date'))
           event['dateend'] = datetime.datetime.fromisoformat(end).strftime("%d/%m/%y %H:%M")
       if 'description' in event:
           # description :  to txt
           desc = HTMLFilter()
           desc.feed(event['description'])
           event['desc'] = desc.text
           # split, search and clean label
           for i in labelList:
             event = split_label(event,i)
           for i in labelList:
             event = search_label(event,i,vTags)
    return events

# route
@app.route('/')
def accueil():
    compile_sass_to_css(sass_map)
    file = read_yaml()
    events = get_gcalendar(file['idCalendar'])
    events = parse_data(events,file['valideTags'])
    return render_template('index.html', events=events, file=file)

@app.errorhandler(404)
def page_not_found(e):
    compile_sass_to_css(sass_map)
    file = read_yaml()
    return render_template('404.html',file=file), 404

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),'favicon.ico', mimetype='image/png')

@app.route('/ping')
def ping():
    return "pong"

if __name__ == '__main__':
    app.run(debug=True)