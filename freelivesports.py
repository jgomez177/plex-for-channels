import time, threading, requests, csv, os, json, gzip, gc
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET


class Client:
    def __init__(self):
        self.lock = threading.Lock()
        self.sessionAt = 0
        self.session_expires_in = 86400
        self.freelivesports_resp = []
        self.client_name = 'freelivesports'
        self.package_url = 'https://raw.githubusercontent.com/jgomez177/plex-for-channels/main'
        self.data_path = f'data/{self.client_name}'
        self.tmsid_path = f'data/tmsid'
        self.custom_tmsid = f'{self.tmsid_path}/freelivesports_tmsid.csv'
        return

    def isTimeExpired(self, sessionAt, age):
        # print ((time.time() - sessionAt), age)
        return ((time.time() - sessionAt) >= age)

    def url_encode(self, base_url, params):
        query_string = urlencode(params)
        full_url = f"{base_url}?{query_string}" if query_string else base_url
        return full_url

    def generate_url(self, url, params_to_keep = []):
        parsed_url = urlparse(url)  # Parse the URL
        query_params = parse_qs(parsed_url.query)  # Convert query string to dictionary

        # Keep only the specified parameters
        new_query = urlencode({k: v for k, v in query_params.items() if k in params_to_keep}, doseq=True)

        # Reconstruct the URL
        return urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, 
                           parsed_url.params, new_query, parsed_url.fragment))



    def body_text(self, provider, host, geo_code_list):

        base_url = f"http://{host}/{provider}/playlist.m3u"

        body_text = f'<p class="title is-4">{provider.capitalize()} Playlist</p>'

        options = '<div class="columns is-multiline is-variable is-5">'
        options += ''
        options += '<div class="column is-third mb-0"><div class="button is-info is-dark">'
        params = {}
        full_url = self.url_encode(base_url, params)
        options += f'<a href="{full_url}" class="has-text-white">Playlist Default</a>'
        options += '</div></div>'
        options += '<div class="column is-third mb-0"><div class="button is-info is-dark">'
        params.update({'gracenote': 'include'})
        full_url = self.url_encode(base_url, params)
        options += f'<a href="{full_url}" class="has-text-white">Gracenote Playlist</a>'
        options += '</div></div>'
        options += '<div class="column is-third mb-0"><div class="button is-info is-dark">'
        params.update({'gracenote': 'exclude'})
        full_url = self.url_encode(base_url, params)
        options += f'<a href="{full_url}" class="has-text-white">Playlist No Gracenote</a>'
        options += '</div></div>'
        options += '</div>'

        tools = '<div class="columns is-multiline is-variable is-5">'
        tools += '<div class="column is-third mb-0"><div class="button is-danger is-dark">'
        tools += f'<a href="http://{host}/{provider}/rebuild_epg" class="has-text-white">Rebuild EPG</a>'
        tools += '</div></div>'
        tools += '<div class="column is-third mb-0"><div class="button is-primary is-dark">'
        tools += f'<a href="http://{host}/{provider}/epg.xml" class="has-text-white">EPG</a>'
        tools += '</div></div>'
        tools += '<div class="column is-third mb-0"><div class="button is-primary is-dark">'
        tools += f'<a href="http://{host}/{provider}/epg.xml.gz" class="has-text-white">EPG GZ</a>'
        tools += '</div></div>'
        tools += '</div>'

        return(f'{body_text}{tools}{options}')

    def update_gracenote_tmsids(self, listing):
        tmsid_url = f"{self.package_url}/{self.custom_tmsid}"

        tmsid_dict = {}

        if os.path.exists(self.custom_tmsid):
            # File exists, open it
            print(f"[INFO - - {self.client_name.upper()}] Opening Custom TMSID File")
            with open(self.custom_tmsid, mode='r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    tmsid_dict[row['id']] = row
        else:
            print(f"[INFO - - {self.client_name.upper()}] Opening TMSID via URL")
            session = requests.Session()
            try:
                # print(f'[INFO - {self.client_name.upper()}] Call {local_client_name} Genre API')
                response = session.get(tmsid_url, timeout=300)
            except requests.ConnectionError as e:
                error = f"Connection Error. {str(e)}"
                print(f'[ERROR - {self.client_name.upper()}] {error}')
                print(f'[ERROR - {self.client_name.upper()}] Unable to access TMSID via {tmsid_url}') 
            finally:
                # print(f'[INFO - {self.client_name.upper()}] Close {local_client_name} Genre API session')
                session.close()
                del session
                gc.collect()

            # Check if request was successful
            if response.status_code == 200:
                # Read in the CSV data
                reader = csv.DictReader(response.text.splitlines())
                for row in reader:
                    tmsid_dict[row['id']] = row
            else:
                print(f'[ERROR - {self.client_name.upper()}] {response.status_code}: Unable to access TMSID Data.') 

        filtered_tmsid = {k: v for k, v in tmsid_dict.items() if v.get("tmsid")}
        print(f'[INFO - {self.client_name.upper()}] Updating TMSID for {len(filtered_tmsid)} items')

        # print(json.dumps(listing, indent=2))

        for elem in listing:
            key = elem.get('id')
            #print(key)
            #print(json.dumps(elem, indent=2))

            if (tmsid_data := filtered_tmsid.get(key)):
                update_data = {'tmsid': tmsid_data['tmsid']}

                if tmsid_data.get('time_shift'):  
                    update_data['time_shift'] = tmsid_data['time_shift']

                elem.update(update_data)
            else:
                if 'tmsid' in elem:
                    elem.pop('tmsid')

        return listing

    def channels(self):
        error = None
        sessionAt = self.sessionAt
        session_expires_in = self.session_expires_in

        if not(self.isTimeExpired(sessionAt, session_expires_in)) and self.freelivesports_resp:
            print(f'[INFO - {self.client_name.upper()}] Reading channel id list cache')
            resp = self.freelivesports_resp
            resp = self.update_gracenote_tmsids(resp)
            # print(json.dumps(resp[0], indent=2))
            with self.lock:
                self.freelivesports_resp = resp
            return resp, None

        url = 'https://ga-prod-api.powr.tv/v2/sites/freelivesports/live-channels/'
        params = {}
        local_headers = {}

        try:
            session = requests.Session()
            epgResponse = session.get(url, params=params, headers=local_headers)
        except requests.ConnectionError as e:
            error = f"Connection Error. {str(e)}"
        finally:
            print(f'[INFO - {self.client_name.upper()}] Close the EPG API session')
            session.close()

        if error:
            print (f'[ERROR - {self.client_name.upper()}] {error}')
            return None, error
        
        if epgResponse.status_code != 200:
            print(f"[ERROR - {self.client_name.upper()}] HTTP: {epgResponse.status_code}: {epgResponse.text}")
            return None, epgResponse.text
        else:
            resp = epgResponse.json()

        if len(resp) > 0:
            # print(json.dumps(resp[0]['url'], indent=2))
            pass
        else:
            error = 'No Data found'
            print (f'[ERROR - {self.client_name.upper()}] {error}')
            return None, error
        
        resp = self.update_gracenote_tmsids(resp)
        # print(json.dumps(resp[0], indent=2))
        ch_listing = set()

        for elem in resp:
            chno = elem.get('channelNumber')
            orignum = chno
            name = elem.get('name')
            while chno in ch_listing:
                chno += 1
            if orignum != chno:
                print(f'[INFO - {self.client_name.upper()}] Changing {name} from Channel {orignum} to {chno}')
                elem.update({'channelNumber': chno})
            ch_listing.add(chno)

        sessionAt = time.time()
        with self.lock:
            self.sessionAt = sessionAt
            self.freelivesports_resp = resp

        return resp, error

    def generate_playlist(self, provider, args, host):
        error = None
        stations, error = self.channels()
        gracenote = args.get('gracenote')

        tmsid_stations = list(filter(lambda d: d.get('tmsid'), stations))
        no_tmsid_stations = list(filter(lambda d: d.get('tmsid', "") == "" or d.get('tmsid') is None, stations))

        if gracenote == 'include':
            data_group = tmsid_stations
        elif  gracenote == 'exclude':
            data_group = no_tmsid_stations
        else:
            data_group = stations

        m3u = "#EXTM3U\r\n\r\n"
        for s in data_group:
            url = s.get('url')
            if "ott-studio" in url:
                base_url = self.generate_url(url, ['m','aid'])
            else:
                base_url = self.generate_url(url)

            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            group = query_params.get('content_genre', [''])[0].split(',')

            m3u += f"#EXTINF:-1 channel-id=\"{provider}-{s.get('id')}\""
            m3u += f" tvg-id=\"{s.get('id')}\""
            m3u += f" tvg-chno=\"{s.get('channelNumber')}\"" if s.get('channelNumber') else ""
            m3u += f" group-title=\"{';'.join(map(str, group))}\"" if group else ""
            m3u += f" tvg-logo=\"{''.join(map(str, s.get('thumbnail', [])))}\"" if s.get('thumbnail') else ""
            m3u += f" tvg-name=\"{s.get('call_sign')}\"" if s.get('call_sign') else ""
            if gracenote == 'include':
                m3u += f" tvg-shift=\"{s.get('time_shift')}\"" if s.get('time_shift') else ""
                m3u += f" tvc-guide-stationid=\"{s.get('tmsid')}\"" if s.get('tmsid') else ""
            m3u += f",{s.get('name') or s.get('call_sign')}\n"
            # m3u += f"{s.get('url')}\n\n"
            m3u += f"{base_url}\n\n"
        return m3u, error                        


    def generate_xml(self):
        error = None
        xml_file_path        = f"{self.data_path}/epg.xml"
        compressed_file_path = f"{xml_file_path}.gz"

        local_epg_data = self.freelivesports_resp.copy()
        # Set your desired timezone, for example, 'UTC'
        # desired_timezone = pytz.timezone('UTC')

        # print(json.dumps(local_epg_data[0], indent = 2))
        root = ET.Element("tv", attrib={"generator-info-name": self.client_name})

        # stations = sorted(local_epg_data, key = lambda i: i.get('title', ''))

        for station in local_epg_data:
            channel = ET.SubElement(root, "channel", attrib={"id": str(station["id"])})
            display_name = ET.SubElement(channel, "display-name")
            display_name.text = station["name"]
            icon = ET.SubElement(channel, "icon", attrib={"src": station['thumbnail']})

        for station in local_epg_data:
            epg_entries = station['epg'].get('entries')
            station_id = station["id"]
            for entry in epg_entries:
                programme = ET.SubElement(root, "programme", attrib={"channel": station_id,
                                                "start": datetime.fromisoformat(entry["start"].replace('Z', '+00:00')).strftime("%Y%m%d%H%M%S %z"),
                                                "stop": datetime.fromisoformat(entry["stop"].replace('Z', '+00:00')).strftime("%Y%m%d%H%M%S %z")})


                if entry.get('title'):
                    title = ET.SubElement(programme, "title")
                    titleText = entry.get('title','')
                    title.text = titleText            

                if entry.get("description"):
                    desc = ET.SubElement(programme, "desc")
                    desc.text = entry.get('description','')


        # Create an ElementTree object
        tree = ET.ElementTree(root)
        ET.indent(tree, '  ')

        # Create a DOCTYPE declaration
        doctype = '<!DOCTYPE tv SYSTEM "xmltv.dtd">'

        # Concatenate the XML and DOCTYPE declarations in the desired order
        xml_declaration = '<?xml version=\'1.0\' encoding=\'utf-8\'?>'

        output_content = xml_declaration + '\n' + doctype + '\n' + ET.tostring(root, encoding='utf-8').decode('utf-8')

        print(f"[INFO - {self.client_name.upper()}] Writing XML to {xml_file_path}")

        # Write the concatenated content to the output file
        if not os.path.exists(self.data_path):
            print(f"[INFO - {self.client_name.upper()}] Creating folder {self.data_path}")
            os.makedirs(self.data_path) 

        try:
            with open(xml_file_path, "w", encoding='utf-8') as f:
                f.write(output_content)
        except Exception as e:
            error = f"[ERROR - {self.client_name.upper()}] Error writing XML: {e}"
            print(error)

        with open(xml_file_path, 'r') as file:
            xml_data = file.read()

        # Compress the XML file
        try:
            with open(xml_file_path, 'rb') as file:
                with gzip.open(compressed_file_path, 'wb') as compressed_file:
                    compressed_file.writelines(file)
        except Exception as e:
            error = f"[ERROR - {self.client_name.upper()}] Error writing XML: {e}"
            print (error)

        return error


    def epg(self, args=None):
        self.channels()
        self.generate_xml()
        return

    def rebuild_epg(self):
        folder_path = Path(f'{self.data_path}')
        file_types = ["epg.xml", "epg.xml.gz"]

        for type in file_types:
            for file in folder_path.glob(type):
                if file.is_file():
                    try:
                        file.unlink()
                    except:
                        print(f"[ERROR - {self.client_name.upper()}] Unable to delete {file}")
                    else:
                        print(f"[ERROR - {self.client_name.upper()}] {file} Deleted")

        self.epg()

        return
