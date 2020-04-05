import datetime
import sass
import re
import yaml
from flask import Flask
from flask import Flask, render_template
from flask import jsonify
from cal_setup import get_calendar_service
from html.parser import HTMLParser
from flask_fontawesome import FontAwesome

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

# get datas
def get_datas(idCal,vTags):
    service = get_calendar_service()
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    # get 100 value
    events_result = service.events().list(
        calendarId= idCal, timeMin=now,
        maxResults=100, singleEvents=True,
        orderBy='startTime').execute()
    events = events_result.get('items', [])
    for event in events:
       # update date format start/end
       start = event['start'].get('dateTime', event['start'].get('date'))
       event['datestart'] = datetime.datetime.fromisoformat(start).strftime("%d/%m/%y %H:%M")
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
           webinarparse = (searhwebinar for searhwebinar in event['desc'].split() if re.match(r"^webinar:.*", searhwebinar))
           for i in webinarparse:
             event['webinar'] = i.replace("webinar:", "").split(",")
             event['desc'] = event['desc'].replace(i , "")
           # tags
           event['desc'] = event['desc'].replace("tags:", " tags:")
           tagsparse = (searhtags for searhtags in event['desc'].split() if re.match(r"^tags:.*", searhtags))
           for i in tagsparse:
             fullTags = i.replace("tags:", "").split(",")
             event['tags'] = list( d for d in fullTags if d in vTags )
             event['desc'] = event['desc'].replace(i , "")
           # city
           event['desc'] = event['desc'].replace("city:", " city:")
           cityparse = (searhcity for searhcity in event['desc'].split() if re.match(r"^city:.*", searhcity))
           for i in cityparse:
             event['city'] = i.replace("city:", "").split(",")
             event['desc'] = event['desc'].replace(i , "")
           # url
           event['desc'] = event['desc'].replace("url:", " url:")
           urlparse = (searhurl for searhurl in event['desc'].split() if re.match(r"^url:.*", searhurl))
           for i in urlparse:
             event['url'] = i.replace("url:", "").split(",")
             event['desc'] = event['desc'].replace(i , "")
    return events

@app.route('/')
def accueil():
    compile_sass_to_css(sass_map)
    file = open_yaml()
    events = get_datas(file['idCalendar'],file['valideTags'])
    return render_template('index.html', events=events, file=file)

@app.errorhandler(404)
def page_not_found(e):
    compile_sass_to_css(sass_map)
    file = open_yaml()
    return render_template('404.html',file=file), 404

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)