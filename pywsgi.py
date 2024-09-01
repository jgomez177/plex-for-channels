from gevent.pywsgi import WSGIServer
from flask import Flask, redirect, request, Response, send_file
from threading import Thread
import subprocess, os, sys, importlib, schedule, time
# import flask module
from gevent import monkey
monkey.patch_all()

version = "1.10a"
updated_date = "May 23, 2024"

# Retrieve the port number from env variables
# Fallback to default if invalid or unspecified
try:
    port = int(os.environ.get("PLEX_PORT", 7777))
except:
    port = 7777

# Retrieve the country codes from env variables
plex_country_code = os.environ.get("PLEX_CODE")
if plex_country_code:
   plex_country_list = [item.strip().lower() for item in plex_country_code.split(',')]
else:
   plex_country_list = ['local']

ALLOWED_COUNTRY_CODES = ['us_east', 'us_west', 'local', 'ca', 'uk', 'nz', 'au', 'mx', 'es']
# instance of flask application
app = Flask(__name__)
provider = "plex"
providers = {
    provider: importlib.import_module(provider).Client(),
}

url = f'<!DOCTYPE html>\
        <html>\
          <head>\
            <meta charset="utf-8">\
            <meta name="viewport" content="width=device-width, initial-scale=1">\
            <title>{provider.capitalize()} Playlist</title>\
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.1/css/bulma.min.css">\
            <style>\
              ul{{\
                margin-bottom: 10px;\
              }}\
            </style>\
          </head>\
          <body>\
          <section class="section">\
            <div class="container">\
              <h1 class="title">\
                {provider.capitalize()} Playlist\
                <span class="tag">v{version}</span>\
              </h1>\
              <p class="subtitle">\
                Last Updated: {updated_date}\
              '

@app.route("/")
def index():
    host = request.host
    ul = ""
    if all(item in ALLOWED_COUNTRY_CODES for item in plex_country_list):
        pl = f"http://{host}/mjh_compatible"
        # ul = f'<p class="subtitle">channel-id by "provider"-"id" (i.mjh.nz compatibility): <a href="{pl}">{pl}</a><br></p><ul>'
        for code in plex_country_list:
            pl = f"http://{host}/{provider}/{code}/playlist.m3u"
            ul += f"<li>{provider.upper()} {code.upper()}: <a href='{pl}'>{pl}</a></li>\n"
            pl = f"http://{host}/mjh_compatible/{provider}/{code}/playlist.m3u"
            ul += f"<li>{provider.upper()} {code.upper()} MJH Compatible: <a href='{pl}'>{pl}</a></li>\n"
            if code in ['local', 'us_east', 'us_west']:
                pl = f"http://{host}/{provider}/{code}/playlist.m3u?gracenote=include"
                ul += f"<li>{provider.upper()} {code.upper()} Gracenote Playlist: <a href='{pl}'>{pl}</a></li>\n"
                pl = f"http://{host}/{provider}/{code}/playlist.m3u?gracenote=exclude"
                ul += f"<li>{provider.upper()} {code.upper()} EPG Only Playlist: <a href='{pl}'>{pl}</a></li>\n"
            ul += f"<br>\n"
            pl = f"http://{host}/{provider}/epg/{code}/epg-{code}.xml"
            ul += f"<li>{provider.upper()} {code.upper()} EPG: <a href='{pl}'>{pl}</a></li>\n"
            pl = f"http://{host}/{provider}/epg/{code}/epg-{code}.xml.gz"
            ul += f"<li>{provider.upper()} {code.upper()} EPG GZ: <a href='{pl}'>{pl}</a></li>\n"
            ul += f"<br>\n"
    else:
        ul += f"<li>INVALID COUNTRY CODE in \"{', '.join(plex_country_list).upper()}\"</li>\n"
    return f"{url}<ul>{ul}</ul></div></section></body></html>"

@app.route("/token/<country_code>")
def token(country_code):
    # host = request.host
    token = providers[provider].token(country_code)
    return(token)

@app.get("/<provider>/<country_code>/playlist.m3u")
def playlist(provider, country_code):
    gracenote = request.args.get('gracenote')
    filter_stations = request.args.get('filtered')

    if country_code not in ALLOWED_COUNTRY_CODES:
        return "Invalid county code", 400

    host = request.host

    stations, token, err = providers[provider].channels(country_code)
    if err is not None: return err, 500

    # Filter out Hidden items or items without Hidden Attribute
    tmsid_stations = []
    no_tmsid_stations = []
    if stations:
        tmsid_stations = list(filter(lambda d: d.get('tmsid'), stations))
        no_tmsid_stations = list(filter(lambda d: d.get('tmsid', None) is None, stations))

    if 'unfiltered' not in request.args and gracenote == 'include':
        data_group = tmsid_stations
    elif  'unfiltered' not in request.args and gracenote == 'exclude':
        data_group = no_tmsid_stations
    else:
        data_group = stations


    stations = sorted(stations, key = lambda i: i.get('name', ''))

    if err is not None:
        return err, 500
    m3u = "#EXTM3U\r\n\r\n"
    for s in data_group:
        m3u += f"#EXTINF:-1 channel-id=\"{provider}-{s.get('slug')}\""
        m3u += f" tvg-id=\"{s.get('id')}\""
        m3u += f" tvg-chno=\"{''.join(map(str, s.get('number', [])))}\"" if s.get('number') else ""
        m3u += f" group-title=\"{''.join(map(str, s.get('group', [])))}\"" if s.get('group') else ""
        m3u += f" tvg-logo=\"{''.join(map(str, s.get('logo', [])))}\"" if s.get('logo') else ""
        m3u += f" tvg-name=\"{s.get('call_sign')}\"" if s.get('call_sign') else ""
        if gracenote == 'include':
            m3u += f" tvg-shift=\"{s.get('time_shift')}\"" if s.get('time_shift') else ""
            m3u += f" tvc-guide-stationid=\"{s.get('tmsid')}\"" if s.get('tmsid') else ""
        m3u += f",{s.get('name') or s.get('call_sign')}\n"
        m3u += f"https://epg.provider.plex.tv{s.get('key')}?X-Plex-Token={token}\n\n"

    response = Response(m3u, content_type='audio/x-mpegurl')
    return (response)

@app.get("/<provider>/<country_code>/channels.json")
def channels_json(provider, country_code):
        stations, token, err = providers[provider].channels(country_code)
        return (stations)

@app.get("/<provider>/<country_code>/epg.json")
def epg_json(provider, country_code):
        epg, err = providers[provider].epg_json(country_code)
        if err: return err
        return epg


@app.get("/mjh_compatible/<provider>/<country_code>/playlist.m3u")
def playlist_mjh_compatible(provider, country_code):
    gracenote = request.args.get('gracenote')
    filter_stations = request.args.get('filtered')

    if country_code not in ALLOWED_COUNTRY_CODES:
        return "Invalid county code", 400

    host = request.host

    stations, token, err = providers[provider].channels(country_code)
    # Filter out Hidden items or items without Hidden Attribute
    tmsid_stations = list(filter(lambda d: d.get('tmsid'), stations))
    no_tmsid_stations = list(filter(lambda d: d.get('tmsid', None) is None, stations))

    if 'unfiltered' not in request.args and gracenote == 'include':
        data_group = tmsid_stations
    elif  'unfiltered' not in request.args and gracenote == 'exclude':
        data_group = no_tmsid_stations
    else:
        data_group = stations

    if err is not None:
        return err, 500
    
    stations = sorted(stations, key = lambda i: i.get('name', ''))

    m3u = "#EXTM3U\r\n\r\n"
    for s in data_group:
        m3u += f"#EXTINF:-1 channel-id=\"{provider}-{s.get('id')}\""
        m3u += f" tvg-id=\"{s.get('id')}\""
        m3u += f" tvg-chno=\"{s.get('number')}\"" if s.get('number') else ""
        # m3u += f" group-title=\"{''.join(map(str, s.get('group', [])))}\"" if s.get('group') else ""
        m3u += f" tvg-logo=\"{''.join(map(str, s.get('logo', [])))}\"" if s.get('logo') else ""
        m3u += f" tvg-name=\"{s.get('call_sign')}\"" if s.get('call_sign') else ""
        if gracenote == 'include':
            m3u += f" tvg-shift=\"{s.get('time_shift')}\"" if s.get('time_shift') else ""
            m3u += f" tvc-guide-stationid=\"{s.get('tmsid')}\"" if s.get('tmsid') else ""
        m3u += f",{s.get('name') or s.get('call_sign')}\n"
        m3u += f"https://epg.provider.plex.tv{s.get('key')}?X-Plex-Token={token}\n\n"

    response = Response(m3u, content_type='audio/x-mpegurl')
    return (response)




@app.get("/<provider>/epg/<country_code>/<filename>")
def epg_xml(provider, country_code, filename):

    # Generate ALLOWED_FILENAMES and ALLOWED_GZ_FILENAMES based on ALLOWED_COUNTRY_CODES
    ALLOWED_EPG_FILENAMES = {f'epg-{code}.xml' for code in ALLOWED_COUNTRY_CODES}
    ALLOWED_GZ_FILENAMES = {f'epg-{code}.xml.gz' for code in ALLOWED_COUNTRY_CODES}

    # Specify the file path
    # file_path = 'epg.xml'
    try:
        if country_code not in ALLOWED_COUNTRY_CODES:
            return "Invalid county code", 400

        # Check if the provided filename is allowed in either format
        if filename not in ALLOWED_EPG_FILENAMES and filename not in ALLOWED_GZ_FILENAMES:
        # Check if the provided filename is allowed
        # if filename not in ALLOWED_EPG_FILENAMES:
            return "Invalid filename", 400
        
        # Specify the file path based on the provider and filename
        file_path = f'{filename}'

        # Return the file without explicitly opening it
        if filename in ALLOWED_EPG_FILENAMES: 
            return send_file(file_path, as_attachment=False, download_name=file_path, mimetype='text/plain')
        elif filename in ALLOWED_GZ_FILENAMES:
            return send_file(file_path, as_attachment=True, download_name=file_path)
    except FileNotFoundError:
        # Handle the case where the file is not found
        return "XML file not found", 404
    except Exception as e:
        # Handle other unexpected errors
        return f"An error occurred: {str(e)}", 500


# Define the function you want to execute with scheduler
def epg_scheduler():
    if all(item in ALLOWED_COUNTRY_CODES for item in plex_country_list):
        for code in plex_country_list:
            # print("Scheduled EPG Data Update")
            error = providers[provider].create_xml_file(code)
            if error: print(f"{error}")


# Define a function to run the scheduler in a separate thread
def scheduler_thread():
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            print(f"Scheduler crashed: {e}. Restarting...")
            # Restart scheduler
            schedule.clear()
            # Schedule the function to run every thirty minutes
            schedule.every(30).minutes.do(epg_scheduler)


if __name__ == '__main__':
    # Schedule the function to run every thirty minutes
    schedule.every(30).minutes.do(epg_scheduler)

    if all(item.lower() in ALLOWED_COUNTRY_CODES for item in plex_country_list):
        for code in plex_country_list:
            print("Initialize XML File")
            error = providers[provider].create_xml_file(code)
            if error: 
                print(f"{error}")
    else:
        print(f"Invalid PLEX_CODE: {plex_country_list}")
    sys.stdout.write(f"⇨ http server started on [::]:{port}\n")
    try:
        # Start the scheduler thread
        thread = Thread(target=scheduler_thread)
        thread.start()
        WSGIServer(('', port), app, log=None).serve_forever()
    except OSError as e:
        print(str(e))
