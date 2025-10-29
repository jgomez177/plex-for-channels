from gevent.pywsgi import WSGIServer
from flask import Flask, redirect, request, Response, send_file
from threading import Thread, Event
import os, importlib, schedule, time
from gevent import monkey
monkey.patch_all()

version = "5.0.0"
updated_date = "Oct. 29, 2025"
base_list = ['plex']

# Retrieve the port number from env variables
# Fallback to default if invalid or unspecified
try:
    port = int(os.environ.get("PORT", 7777))
except:
    port = 7777


# instance of flask application
app = Flask(__name__)

try:
    p_list = [item.lower() for item in (os.environ.get("PLIST")).split(',')]
except:
    p_list = base_list

if len(p_list) == 0:
    p_list = base_list


provider_list = p_list

print(f'[INFO - MAIN] Using the following modules: {", ".join(p.upper() for p in provider_list)}')

providers = {}
for provider in provider_list:
    providers.update({
        provider: importlib.import_module(provider).Client(),
    })

url_main = f'<!DOCTYPE html>\
        <html>\
          <head>\
            <meta charset="utf-8">\
            <meta name="viewport" content="width=device-width, initial-scale=1">\
            <title>Playlist</title>\
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.1/css/bulma.min.css">\
          </head>\
          <body>\
          <section class="section py-2">\
              <h1 class="title is-2">\
                Playlist\
                <span class="tag">v{version}</span>\
                <span class="tag">Last Updated: {updated_date}</span>\
              </h1>'

# Dictionary to store trigger events for each provider
trigger_events = {}
def trigger_epg_build(provider):
    if provider in trigger_events:
        trigger_events[provider].set()
    else:
        print(f"[ERROR - {provider}] No scheduler thread found for provider: {provider}")    


@app.route("/")
def index():
    host = request.host

    body = ''
    for provider in providers:
        geo_code_name = f"{provider.upper()}_CODE"
        geo_code_list = os.environ.get(geo_code_name)

        body += '<div>'
        body_text = providers[provider].body_text(provider, host, geo_code_list)
        body += body_text
        body += "</dev>"
    return f"{url_main}{body}</section></body></html>"

@app.route("/<provider>/token")
def token(provider):
    # host = request.host
    args = request.args

    token_keychain, error = providers[provider].token(args)
    if error:
        return error
    else:
        return token_keychain

@app.get("/<provider>/playlist.m3u")
def playlist(provider):
    args = request.args
    host = request.host

    m3u, error = providers[provider].generate_playlist(provider, args, host)
    if error: return error, 500
    response = Response(m3u, content_type='audio/x-mpegurl')
    # response = Response(m3u)
    return (response)

@app.get("/<provider>/channels.json")
def channels_json(provider):
        args = request.args

        stations, err = providers[provider].channels(args)
        if err: return (err)
        return (stations)

@app.get("/<provider>/rebuild_epg")
def rebuild_epg(provider):
        providers[provider].rebuild_epg()
        trigger_epg_build(provider)
        return "Rebuilding EPG"

@app.get("/<provider>/build_epg")
def build_epg(provider):
        trigger_epg_build(provider)
        return "Manually Triggering EPG"

@app.route("/<provider>/watch/<id>")
def watch(provider, id):
    video_url, err = providers[provider].generate_video_url(id)
    if err: return f"Error {err}", 500, {'X-Tuner-Error': err}
    if not video_url:return "Error - No Video Stream", 500, {'X-Tuner-Error': 'No Video Stream Detected'}
    # print(f'[INFO] {video_url}')
    return (redirect(video_url))

@app.get("/<provider>/<filename>")
def epg_xml(provider, filename):
    file_path = f'data/{provider}/{filename}'

    try:
        suffix = filename.split('.')[-1] if '.' in filename else ''
        # Return the file without explicitly opening it
        if suffix.lower() == 'xml':
            return send_file(file_path, as_attachment=False, download_name=file_path, mimetype='text/plain')
        elif suffix.lower() == 'gz':
            return send_file(file_path, as_attachment=True, download_name=file_path)
        else:
            return f"{file_path} file not found", 404
    except FileNotFoundError:
        return "XML Being Generated Please Standby", 404

# Define the function you want to execute with scheduler
def epg_scheduler(provider):
    print(f"[INFO - {provider.upper()}] Running EPG Scheduler for {provider}")

    try:
        error = providers[provider].epg()
        if error:
            print(f"[ERROR - {provider.upper()}] EPG: {error}")
    except Exception as e:
        print(f"[ERROR - {provider.upper()}] Exception in EPG Scheduler : {e}")
    print(f"[INFO - {provider.upper()}] EPG Scheduler Complete")

# Define a function to run the scheduler in a separate thread
def scheduler_thread(provider):

    if provider not in trigger_events:
        trigger_events[provider] = Event()

    event = trigger_events[provider]  # Get the event for this provider

    # Define Scheduler
    match provider.lower():
        case 'plex':
            schedule.every(10).minutes.do(lambda: epg_scheduler(provider))
        case _:
            schedule.every(1).hours.do(lambda: epg_scheduler(provider))

    # Run the task immediately when the thread starts
    while True:
        try:
            epg_scheduler(provider)

        except Exception as e:
            print(f"[ERROR - {provider.upper()}] Error in running scheduler, retrying: {e}")
            continue  # Immediately retry

        # Continue as Scheduled
        while True:
            try:
                # Scheduled event
                schedule.run_pending()

                # Check if the event is set (manual trigger)
                if event.is_set():
                    print(f"[MANUAL TRIGGER - {provider.upper()}] Running epg_scheduler manually...")
                    epg_scheduler(provider)
                    event.clear()  # Reset event after execution

                time.sleep(1)
            except Exception as e:
                 print(f"[ERROR - {provider.upper()}] Error in scheduler thread: {e}")
                 break # Restart the loop and rerun epg_scheduler

# Function to monitor and restart the thread if needed
def monitor_thread(provider):
    def thread_wrapper(provider):
        print(f"[INFO - {provider.upper()}] Starting Scheduler thread for {provider}")
        scheduler_thread(provider)

    thread = Thread(target=thread_wrapper, args=(provider,), daemon=True)
    thread.start()

    while True:
        if not thread.is_alive():
            print(f"[ERROR - {provider.upper()}] Scheduler thread stopped. Restarting...")
            thread = Thread(target=thread_wrapper, args=(provider,),daemon=True)
            thread.start()
        time.sleep(15 * 60)  # Check every 15 minutes
        print(f"[INFO - {provider.upper()}] Checking scheduler thread")

if __name__ == '__main__':
    trigger_event = Event()

    for provider in provider_list:
        # pass
        Thread(target=monitor_thread, args=(provider,), daemon=True).start()

    try:
        print(f"[INFO - MAIN] ⇨ http server started on [::]:{port}")
        WSGIServer(('', port), app, log=None).serve_forever()
    except OSError as e:
        print(str(e))