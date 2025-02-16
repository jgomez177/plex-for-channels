import threading, json, random, string, time, requests, csv, os, gzip, pytz, shutil, gc, itertools
from urllib.parse import urlencode
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import xml.dom.minidom
import concurrent.futures
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class Client:
    def __init__(self):
        self.lock = threading.Lock()
        self.client_name = 'plex'
        self.data_path = f'data/{self.client_name}'
        self.channels_by_geo_file = Path(f'{self.data_path}/channels_by_geo.json')
        self.device_id = None
        self.load_device()
        self.sessionAt = 0
        self.session_expires_in = (6 * 60 * 60)
        # self.channels_by_geo = {}
        self.tokenResponse = None
        self.token_expires_in = (6 * 60 * 60)
        self.token_sessionAt = 0
        self.tokenResponses = {}
        self.token_keychain = {}
        self.update_today_epg = 0

        self.x_forward = {"local": "",
                          "clt": "108.82.206.181",
                          "sea": "159.148.218.183",
                          "dfw": "76.203.9.148",
                          "nyc": "85.254.181.50",
                          "la": "76.81.9.69",
                          "uk": "178.238.11.6",
                          "ca": "192.206.151.131", 
                          "mx":  "200.68.128.83",
                          "es":  "88.26.241.248",
                          "au":  "110.33.122.75",
                          "nz":  "203.86.207.83",
                        }

        self.headers = {
                        'Accept': 'application/json, text/plain, */*',
                        'Accept-Language': 'en',
                        'Connection': 'keep-alive',
                        'Origin': 'https://app.plex.tv',
                        'Referer': 'https://app.plex.tv/',
                        'Sec-Fetch-Dest': 'empty',
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'same-site',
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
                        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
                        'sec-ch-ua-mobile': '?0',
                        'sec-ch-ua-platform': '"macOS"',
                        }

        self.params = {
                        'X-Plex-Product': 'Plex Web',
                        'X-Plex-Version': '4.145.0',
                        'X-Plex-Client-Identifier': self.device_id,
                        'X-Plex-Platform': 'Chrome',
                        'X-Plex-Platform-Version': '132.0',
                        'X-Plex-Features': 'external-media,indirect-media,hub-style-list',
                        'X-Plex-Model': 'standalone',
                        'X-Plex-Device': 'OSX',
                        'X-Plex-Device-Screen-Resolution': '1758x627,1920x1080',
                        'X-Plex-Provider-Version': '7.2',
                        'X-Plex-Text-Format': 'plain',
                        'X-Plex-Drm': 'widevine',
                        'X-Plex-Language': 'en',
                        }

    def parse_newregion(self, newregion):
        parsed_data = {}
        try:
            # Remove curly braces `{}` and split by comma
            values = newregion.strip("{}").split(",")

            # Ensure we have exactly 2 elements
            if len(values) == 2:
                region, ip_address = values  # Extract key-value pair
                parsed_data = {region.strip(): ip_address.strip()}  # Convert to dictionary
        except Exception:
            print('[ERROR - {self.client_name.upper()}] Invalid format for newregion')

        if parsed_data:
            local_x_forward = self.x_forward.copy()
            for geo_code in parsed_data:
                if geo_code in local_x_forward:
                    print(f'[WARNING - {self.client_name.upper()}] Updating geo location bata to {parsed_data}')
                else:
                    print(f'[INFO - {self.client_name.upper()}] ADDING {parsed_data} to geo location data')

            local_x_forward.update(parsed_data)
            with self.lock:
                self.x_forward = local_x_forward
        return parsed_data

    def isTimeExpired(self, sessionAt, age):
        # print ((time.time() - sessionAt) >= age)
        return ((time.time() - sessionAt) >= age)

    def load_device(self):
        client_name = self.client_name.lower()
        device_file = f"{client_name}-device.json"
        folder_path = Path(self.data_path)
        file_path = folder_path / device_file

        device_id = self.device_id
        length = 24

        try:
            # Read and parse JSON file
            device_id = json.loads(file_path.read_text())
        except:
            print(f"[INFO - {self.client_name.upper()}] {client_name.upper()} Generating Device ID")
            characters = string.ascii_lowercase + string.digits
            device_id = ''.join(random.choice(characters) for _ in range(length))
            # Create folder if it doesn't exist
            folder_path.mkdir(parents=True, exist_ok=True)
            file_path.write_text(json.dumps(device_id, indent=4))
        else:
            print(f"[INFO - {self.client_name.upper()}] {client_name.upper()} Using Existing Device ID")

        with self.lock:
            self.device_id = device_id


    def url_encode(self, base_url, params):
        query_string = urlencode(params)
        full_url = f"{base_url}?{query_string}" if query_string else base_url
        return full_url

    def body_text(self, provider, host, geo_code_list):

        local_x_forward = self.x_forward.copy()
        local = ['local']
        base_url = f"http://{host}/{provider}/playlist.m3u"

        body_text = f'<p class="title is-4">{provider.capitalize()} Playlist</p>'

        options = '<span class="tag is-link is-light is-medium is-rounded mb-5">Multiple Region parameters can be used with comma seperator. Example: playlist.m3u?regions=local,ca</span>'
        options += '<div class="columns is-multiline is-variable is-5">'
        for elem in local_x_forward:
            options += ''
            options += '<div class="column is-one-quarter mb-0"><div class="button is-info is-dark">'
            if elem != 'local':
                params = {'regions': elem}
            else:
                params = {}
            full_url = self.url_encode(base_url, params)
            options += f'<a href="{full_url}" class="has-text-white">{elem.upper()} Playlist Default</a>'
            options += '</div></div>'
            options += '<div class="column is-one-quarter mb-0"><div class="button is-info is-dark">'
            params.update({'compatibility': 'matthuisman'})
            full_url = self.url_encode(base_url, params)
            options += f'<a href="{full_url}" class="has-text-white">{elem.upper()} Playlist Type MJH</a>'
            params.pop('compatibility', None)
            options += '</div></div>'
            options += '<div class="column is-one-quarter mb-0"><div class="button is-info is-dark">'
            params.update({'gracenote': 'include'})
            full_url = self.url_encode(base_url, params)
            options += f'<a href="{full_url}" class="has-text-white">{elem.upper()} Gracenote Playlist</a>'
            options += '</div></div>'
            options += '<div class="column is-one-quarter mb-0"><div class="button is-info is-dark">'
            params.update({'gracenote': 'exclude'})
            full_url = self.url_encode(base_url, params)
            options += f'<a href="{full_url}" class="has-text-white">{elem.upper()} Playlist No Gracenote</a>'
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

    def generate_group_listing(self, token, geo_code):
        error = None
        local_headers = self.headers.copy()
        local_x_forward = self.x_forward.copy()

        if geo_code in local_x_forward.keys():
            local_headers.update({"X-Forwarded-For": local_x_forward.get(geo_code)})

        group_listing = local_headers
        return group_listing, error
    
    def generate_m3u(self, provider, listings, gracenote, channel_id_type):
        local_token_keychain = self.token_keychain.copy()

        m3u = "#EXTM3U\r\n\r\n"
        for s in listings:
            token = local_token_keychain.get(s.get('geo_code',''),{}).get('access_token')
            if channel_id_type == 'matthuisman':
                m3u += f"#EXTINF:-1 channel-id=\"{provider}-{s.get('id')}\""
            else:
                m3u += f"#EXTINF:-1 channel-id=\"{provider}-{s.get('slug')}\""
            m3u += f" tvg-id=\"{s.get('id')}\""
            m3u += f" tvg-chno=\"{s.get('number')}\"" if s.get('number') else ""
            m3u += f" tvg-logo=\"{''.join(map(str, s.get('logo', [])))}\"" if s.get('logo') else ""
            m3u += f" tvg-name=\"{s.get('call_sign')}\"" if s.get('call_sign') else ""
            if gracenote == 'include':
                m3u += f" tvg-shift=\"{s.get('time_shift')}\"" if s.get('time_shift') else ""
                m3u += f" tvc-guide-stationid=\"{s.get('tmsid')}\"" if s.get('tmsid') else ""
            m3u += f" group-title=\"{''.join(map(str, s.get('group', [])))}\"" if s.get('group') else ""
            m3u += f",{s.get('name') or s.get('call_sign')}\n"
            m3u += f"https://epg.provider.plex.tv{s.get('key')}?X-Plex-Token={token}\n\n"
        return m3u
    
    def generate_playlist(self, provider, args, host):
        error = None        
        station_dict, error = self.channels(args)
        if error: return None, error

        geo_list = self.generate_geo_list(args)
        # print(f'[INFO - {self.client_name.upper()}] generate_playlist: {geo_list}')

        playlist_dict = {}
        for geo_code in geo_list:
            channels_by_geo = station_dict.get(geo_code)
            for ch in channels_by_geo:
                if not (ch in playlist_dict):
                    station_data = channels_by_geo.get(ch)
                    station_data.update({'geo_code': geo_code})
                    playlist_dict.update({ch: station_data})

            # print(f'[INFO - {self.client_name.upper()}] generate_playlist Playlist: {len(playlist_dict)}')

        # listings = sorted(playlist_dict.values(), key = lambda i: i.get('name', ''))
        listings = sorted(
            playlist_dict.values(), 
            key=lambda i: (
                            (i.get('call_sign') is None, i.get('call_sign', '')),
                            i.get('tmsid') is None, 
                            i.get('name').lower() or '')      
            )

        print(f'[INFO - {self.client_name.upper()}] Full Playlist: {len(listings)}')

        gracenote = args.get('gracenote')
        if gracenote == 'include':
            listings = list(filter(lambda d: d.get('tmsid'), listings))
            print(f'[INFO - {self.client_name.upper()}] Gracenote Playlist: {len(listings)}')
        elif gracenote == 'exclude':
            listings = list(filter(lambda d: d.get('tmsid', None) is None, listings))
            print(f'[INFO - {self.client_name.upper()}] No Gracenote Playlist: {len(listings)}')

        channel_id_type = args.get('compatibility')

        m3u = self.generate_m3u(provider, listings, gracenote, channel_id_type)
        return m3u, error                        

    def call_token_api(self, local_headers, local_params, local_token_sessionAt, tokenResponse):
        url = 'https://clients.plex.tv/api/v2/users/anonymous'
        error = None
        local_token_expires_in = self.token_expires_in
        local_client_name = self.client_name
        
        if self.isTimeExpired(local_token_sessionAt, local_token_expires_in) or (tokenResponse is None):
            # print(f"[INFO - {self.client_name.upper()}] Call {local_client_name} Token API Call")
            local_token_sessionAt = time.time()
            try:
                session = requests.Session()
                tokenResponse = session.post(url, params=local_params, headers=local_headers)
            except requests.ConnectionError as e:
                error = f"Connection Error. {str(e)}"
            finally:
                # print(f'[INFO - {self.client_name.upper()}] Close {local_client_name} Token API session')
                session.close()
        # else:
        #     print(f"[INFO - {self.client_name.upper()}] Return {local_client_name} Cached Token Response")

        if error:
            print(error)
            return None, None, None, error

        if tokenResponse.status_code not in (200, 201):
            print(f"HTTP: {tokenResponse.status_code}: {tokenResponse.text}")
            return None, None, None, tokenResponse.text
        else:
            resp = tokenResponse.json()

        # print(json.dumps(resp, indent = 2))
        # with self.lock:
        #    self.tokenResponse = tokenResponse
        # access_token = resp.get('authToken', None)
        return (tokenResponse, local_token_sessionAt, error)

    def generate_geo_list(self, args):
        if args:
            regions = args.get('regions')
        else:
            regions = None
        if regions:
            geo_list = [region.strip() for region in args.get('regions', '').split(',')] if args.get('regions', '') else []
            # print(geo_list)
            geo_list = list(set(geo_list))
        else:
            geo_list = ['local']

        return(geo_list)


    def token(self, args):
        error= None
        geo_list = self.generate_geo_list(args)

        token_headers=self.headers.copy()
        token_params=self.params.copy()
        local_tokenResponses=self.tokenResponses.copy()
        local_token_keychain = self.token_keychain.copy()
        local_x_forward = self.x_forward.copy()
        local_token_expires_in = self.token_expires_in

        for geo_code in geo_list:
            if geo_code not in local_x_forward.keys():
                error = f'[ERROR - {self.client_name.upper()}] Geo Code {geo_code} Not Found'
                print(error)
                return None, error
            
            token_headers.update({"X-Forwarded-For": local_x_forward.get(geo_code)})
            tokenResponse = local_tokenResponses.get(geo_code)
            tokenResponse, local_token_sessionAt, error = self.call_token_api(token_headers, token_params, local_token_keychain.get(geo_code, {}).get('token_sessionAt', 0), tokenResponse)
        
            if error: return None, error

            resp = tokenResponse.json()

            access_token = resp.get('authToken', None)
            if not access_token:
                error = f'[ERROR - {self.client_name.upper()}] No Token located for {geo_code}'
                print(error)
                return None, error

            local_tokenResponses.update({geo_code: tokenResponse})

            local_key = {"access_token": access_token,
                         "token_sessionAt": local_token_sessionAt,
                         "token_expires_in": local_token_expires_in,
                         }
        
        
            local_token_keychain.update({geo_code: local_key})
        # print(json.dumps(local_token_keychain, indent=2))
        # print(local_tokenResponses)

        with self.lock:
            self.token_keychain = local_token_keychain
            self.tokenResponses = local_tokenResponses
        return local_token_keychain, error
    
    def call_genre_api(self, geo_code):
        error = None
        url = 'https://epg.provider.plex.tv/'
        local_client_name = self.client_name
        local_headers = self.headers.copy()
        local_params = self.params.copy()
        local_x_forward = self.x_forward.copy()

        if geo_code in local_x_forward.keys():
            local_headers.update({"X-Forwarded-For": local_x_forward.get(geo_code)})

        try:
            # print(f'[INFO - {self.client_name.upper()}] Call {local_client_name} Genre API')
            session = requests.Session()
            response = session.get(url, params=local_params, headers=local_headers, timeout=300)
        except requests.ConnectionError as e:
            error = f"Connection Error. {str(e)}"
        finally:
            # print(f'[INFO - {self.client_name.upper()}] Close {local_client_name} Genre API session')
            session.close()
        if error: return None, error

        if response.status_code != 200:
            print(f'[ERROR - {self.client_name.upper()}] {local_client_name} HTTP Failure {response.status_code}')
            return None, f"HTTP failure {response.status_code}: {response.text}"
        
        resp = response.json()

        genres_temp = {}

        feature = resp.get('MediaProvider', {}).get('Feature',[])
        for elem in feature:
            if 'GridChannelFilter' in elem:
                genres_temp = elem.get('GridChannelFilter')
                break

        # print(genres_temp)
        genres = {}

        for genre in genres_temp:
            genres.update({genre.get('identifier'): genre.get('title')})

        # print(genres)
        return {geo_code: genres}, None
    
    def update_gracenote_tmsids(self, listing):
        # Fetch the CSV file from the URL
        plex_tmsid_url = "https://raw.githubusercontent.com/jgomez177/plex-for-channels/main/plex_tmsid.csv"
        plex_custom_tmsid = 'plex_data/plex_custom_tmsid.csv'

        try:
            # print(f'[INFO - {self.client_name.upper()}] Call {local_client_name} Genre API')
            session = requests.Session()
            response = session.get(plex_tmsid_url, timeout=300)
        except requests.ConnectionError as e:
            error = f"Connection Error. {str(e)}"
            print(f'[ERROR - {self.client_name.upper()}] {error}')
            print(f'[ERROR - {self.client_name.upper()}] Unable to access TMSID Data. No changes made.') 
            return listing
        finally:
            # print(f'[INFO - {self.client_name.upper()}] Close {local_client_name} Genre API session')
            session.close()

        # Check if request was successful
        if response.status_code == 200:
            # Read in the CSV data
            reader = csv.DictReader(response.text.splitlines())
        else:
            print(f'[ERROR - {self.client_name.upper()}] {response.status_code}: Unable to access TMSID Data. No changes made.') 
            return listing


        tmsid_dict = {}
        tmsid_custom_dict = {}

        for row in reader:
            tmsid_dict[row['id']] = row

        if os.path.exists(plex_custom_tmsid):
            # File exists, open it
            with open(plex_custom_tmsid, mode='r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    tmsid_custom_dict[row['id']] = row

        tmsid_dict.update(tmsid_custom_dict)
        # print(json.dumps(tmsid_dict, indent=2))

        filtered_tmsid = {k: v for k, v in tmsid_dict.items() if v.get("tmsid")}

        print(f'[INFO - {self.client_name.upper()}] Updating TMSID for {len(filtered_tmsid)} items')
        for elem in listing:
            key = listing.get(elem).get('id')

            if (tmsid_data := filtered_tmsid.get(key)):
                update_data = {'tmsid': tmsid_data['tmsid']}

                if tmsid_data.get('time_shift'):  
                    update_data['time_shift'] = tmsid_data['time_shift']

                listing[elem].update(update_data)

        #print(json.dumps(listing, indent=2))
        return listing

    def channels(self, args):
        error = None
        if args and args.get('newregion'):
            self.parse_newregion(args.get('newregion'))

        geo_list = self.generate_geo_list(args).copy()
        # channels_by_geo = self.channels_by_geo
        with self.lock:
            if self.channels_by_geo_file.exists():
                channels_by_geo = json.loads(self.channels_by_geo_file.read_text())
            else:
                channels_by_geo = {}

        sessionAt = self.sessionAt
        session_expires_in = self.session_expires_in


        if not(self.isTimeExpired(sessionAt, session_expires_in)):
            if all([ele in channels_by_geo for ele in geo_list]):
                print(f"[INFO - {self.client_name.upper()}] Reading channel id list cache for all geo locations")
                return channels_by_geo, None
            else:
                for geo_code in geo_list:
                    if channels_by_geo.get(geo_code):
                        print(f"[INFO - {self.client_name.upper()}] Reading channel id list cache for {geo_code}")
                        geo_list.remove(geo_code)

        # print(geo_list)
        local_headers = self.headers
        local_params = self.params
        local_device_id = self.device_id
        local_x_forward = self.x_forward.copy()

        token, error = self.token(args)
        if error: return None, error

        genres = {}
        for geo_code in geo_list:
            geo_genre, error = self.call_genre_api(geo_code)
            if error: return None, error
            genres.update(geo_genre)

            if geo_code in local_x_forward.keys():
                local_headers.update({"X-Forwarded-For": local_x_forward.get(geo_code)})

            access_token = token.get(geo_code).get('access_token')
            if access_token:
                print(f'[INFO - {self.client_name.upper()}] Access Token located for {geo_code}')
                local_params.update({'X-Plex-Token': access_token})
            else:
                local_params.pop('X-Plex-Token', None)

            stations = []
            for key, val in geo_genre.get(geo_code).items():
                stations = self.generate_channels(stations, key, val, local_headers, local_params, geo_code)


            channel_dict = {station.get('gridKey'): station for station in stations}
            channel_dict = self.update_gracenote_tmsids(channel_dict)

            channels_by_geo.update({geo_code: channel_dict})
            print(f'[INFO - {self.client_name.upper()}] Stations Identified for {geo_code.lower()}: {len(stations)}/{len(channel_dict)}')

        with self.lock:
            # self.channels_by_geo = channels_by_geo
            self.channels_by_geo_file.write_text(json.dumps(channels_by_geo, indent = 4))
            self.sessionAt = time.time()
            self.session_expires_in = session_expires_in
        return channels_by_geo, error
    
    def generate_channels(self, stations, genre_slug, genre, headers, params, geo_code):
        url = f'https://epg.provider.plex.tv/lineups/plex/channels?genre={genre_slug}'
        local_client_name = self.client_name

        try:
            # print(f'[INFO - {self.client_name.upper()}] Call {local_client_name} Genre Lineup API for {genre}')
            session = requests.Session()
            response = session.get(url, params=params, headers=headers, timeout=300)
        except requests.ConnectionError as e:
            error = f"Connection Error. {str(e)}"
        else:
            error = None
        finally:
            # print(f'[INFO - {self.client_name.upper()}] Close {local_client_name} Genre Lineup API session')
            session.close()
            if error:
                print(f'[ERROR - {self.client_name.upper()}] {error} for {geo_code}/{genre_slug}')
                return stations

        if response.status_code != 200:
            print(f'[ERROR - {self.client_name.upper()}] HTTP Failure {response.status_code} for {geo_code}/{genre_slug}: {response.text}')
            return stations
        
        resp = response.json()

        channels = resp.get("MediaContainer").get("Channel")
        # print(json.dumps(channels[0], indent=2))

        if channels is None:
            print(f"[INFO - {self.client_name.upper()}] No items found for {geo_code}/{genre}")
            return stations

        for elem in channels:
            callSign = elem.get('callSign')
            logo = elem.get('thumb')
            slug = elem.get('slug')
            title = elem.get('title')
            id = elem.get('id')
            gridKey = elem.get('gridKey')

            # Accessing all key values inside the Media/Part arrays
            key_values = [part["key"] for media in elem["Media"] for part in media["Part"]]

            match len(key_values):
                case 0:
                    plex_key = ''
                case 1:
                    plex_key = key_values[0]
                case _:
                    print(f'{slug} with {len(key_values)}')
                    plex_key = key_values[0]

            try:
                # Check if any Media has drm set to True and return a note
                has_drm = any(media["drm"] for media in elem["Media"])
            except KeyError as e:
                # print(f"Error: Missing 'drm' key in at least one Media item in {slug}. {e}")
                has_drm = False

            if has_drm:
                note = f"[INFO - {self.client_name.upper()}] {title} has DRM set. Skipping."
                print(note)
            else:
                new_item = {'call_sign': callSign,
                                      'slug': slug,
                                      'name': title,
                                      'logo': logo,
                                      'id': id,
                                      'key': plex_key,
                                      'gridKey': gridKey,
                                    }
                if genre is not None:
                    new_item.update({'group': [genre]})

                check_callSign = next(filter(lambda d: d.get('slug','') == slug, stations), None)
                if check_callSign is not None:
                    new_group = check_callSign.get('group')
                    new_group.append(genre)
                    check_callSign.update({'group': new_group})
                else:
                    stations.append(new_item)

        return stations

    def read_epg_from_api(self, date, station, epg_xml_data):
        url =  "https://epg.provider.plex.tv/grid"
        local_token_keychain = self.token_keychain.copy()
        local_x_forward = self.x_forward.copy()

        station_geo_code = station.get('geo_code')
        token = local_token_keychain[station_geo_code].get('access_token')
        epg_headers =   {
                        # 'accept': 'application/json, text/javascript, */*',
                        # 'accept-language': 'en',
                        'X-Forwarded-For': local_x_forward.get(station_geo_code),
                        'x-plex-client-identifier': self.device_id,
                        'x-plex-platform-version': '132.0',
                        'x-plex-provider-version': '7.2',
                        'x-plex-token': token,
                        'x-plex-version': '4.145.1',
                    }
       
        epg_params = {'channelGridKey': station.get('gridKey'),
                        'date': date}
        
        session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=3,              # Total number of retries
            backoff_factor=2,     # Time between retries will grow exponentially: 1s, 2s, 4s, etc.
            status_forcelist=[429, 500, 502, 503, 504],  # Retry for these status codes
            raise_on_status=False  # Don't raise an exception for failed retries, just return the response
        )

        # Attach the retry configuration to the session
        adapter = HTTPAdapter(max_retries=retry_strategy)

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        has_error = False
                        
        try:
            response = session.get(url, params=epg_params, headers=epg_headers, timeout=10)
            response.raise_for_status() 
        except requests.ConnectionError as e:
            print(f"[ERROR - {self.client_name.upper()}]: Connection Error. {str(e)}")
            has_error = True
        except requests.exceptions.HTTPError as e:
            print(f"[ERROR - {self.client_name.upper()}]: HTTP error occurred: {e}")
            has_error = True
        except requests.exceptions.RequestException as e:
            print(f"[ERROR - {self.client_name.upper()}]: An error occurred: {e}")
            has_error = True
        finally:
            session.close()

        if has_error: return epg_xml_data

        if response.status_code != 200:
            print(f'[ERROR - {self.client_name.upper()}] EPG HTTP Failure {response.status_code}')
            return epg_xml_data
        
        content_type = response.headers.get("Content-Type", "").lower()
        if "application/xml" in content_type or "text/xml" in content_type:
            # print("Response is XML")
            root = ET.fromstring(response.content)
            epg_xml_data.append(root)

        return epg_xml_data
        
    def generate_epg_station_list(self, channels_by_geo):
        epg_dict = {}
        for geo_loc in channels_by_geo:
            channels_dict = channels_by_geo.get(geo_loc)
            for ch in channels_dict:
                if not (ch in epg_dict):
                    station = channels_dict.get(ch)
                    station.update({'geo_code': geo_loc})
                    epg_dict.update({ch: station})
        return(epg_dict)

    def save_xml(self, xml_file, root):
        folder_path = Path(self.data_path)
        xml_file_path = folder_path / xml_file

        xml_string = ET.tostring(root, encoding="utf-8").decode("utf-8")
        dom = xml.dom.minidom.parseString(xml_string)
        output_content = dom.toprettyxml(indent="  ")

        # Remove unnecessary blank lines
        output_content = "\n".join(line for line in output_content.splitlines() if line.strip())


        with self.lock:
            try:
                xml_file_path.parent.mkdir(parents=True, exist_ok=True)
                xml_file_path.write_text(output_content, encoding="utf-8")
                # print(f"[INFO - {self.client_name.upper()}] XML data successfully written to '{xml_file_path}'")
            except Exception as e:
                print(f"[ERROR - {self.client_name.upper()}] Error writing XML file: {e}")

        return None

    def process_video(self, video, station, output_xml):
        originally_available_at = video.attrib.get("originallyAvailableAt", "0000-00-00T00:00:00Z").split("T")[0].replace("-", "")
        video_type = video.attrib.get("type")

        if video_type is not None:
            match video_type.lower():
                case 'movie':
                    date = video.attrib.get("year")
                    title = f'{video.attrib.get("title", "")} ({date})' if date else video.attrib.get("title", "")
                    subtitle, parent_index, index, grandparent_art = None, None, None, None
                case _:
                    title = video.attrib.get("grandparentTitle", "Unknown Title")
                    subtitle = video.attrib.get("title", "Unknown Subtitle")
                    parent_index = video.attrib.get("parentIndex")
                    index = video.attrib.get("index")
                    grandparent_art = video.attrib.get("grandparentArt")

        content_rating = video.attrib.get("contentRating", "NR")
        desc = video.attrib.get("summary", "")
        genres = [genre.attrib.get("tag") for genre in video.findall("Genre")]

        for media in video.findall("Media"):
            previously_shown = False 
            begins_at = media.get("beginsAt")
            ends_at = media.get("endsAt")

            if begins_at:
                dt = datetime.fromtimestamp(int(begins_at), tz=timezone.utc)
                start_time = dt.strftime("%Y%m%d%H%M%S +0000")

            if ends_at:
                dt = datetime.fromtimestamp(int(ends_at), tz=timezone.utc)
                stop_time = dt.strftime("%Y%m%d%H%M%S +0000")

            programme = ET.Element("programme", start=start_time, stop=stop_time, channel=station.get('id'))
            ET.SubElement(programme, "title").text = title
            if subtitle: ET.SubElement(programme, "sub-title").text = subtitle
            ET.SubElement(programme, "desc").text = desc

            for genre in genres:
                ET.SubElement(programme, "category").text = genre

            if grandparent_art:
                ET.SubElement(programme, "icon", src=grandparent_art)

            if originally_available_at:
                ET.SubElement(programme, "date").text = originally_available_at
            if previously_shown:
                ET.SubElement(programme, "previously-shown")
            if parent_index and index:
                ET.SubElement(programme, "episode-num", system="onscreen").text = f"S{parent_index}E{index}"
                ET.SubElement(programme, "episode-num", system="xmltv_ns").text = f"{int(parent_index)-1}.{int(index)-1}."
            elif index:
                ET.SubElement(programme, "episode-num", system="onscreen").text = f"E{index}"

            rating = ET.SubElement(programme, "rating")
            ET.SubElement(rating, "value").text = content_rating

            output_xml.append(programme)

    def generate_epg_style(self, station_dict, epg_xml_data, output_xml):
        batch_size = 100  # Number of video elements processed per batch
        tv_items = list(epg_xml_data.iterfind(".//tv"))
        num_tv_items = sum(1 for _ in epg_xml_data.iterfind(".//tv"))
        num_media_items = sum(1 for _ in epg_xml_data.iterfind(".//Media"))

        print(f"[DEBUG - {self.client_name.upper()}] Number Stations identified: {num_tv_items}")
        print(f"[DEBUG - {self.client_name.upper()}] Number Programs identified: {num_media_items}")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []

            for i, tv_element in enumerate(tv_items):
                grid_key = tv_element.attrib.get("channelGridKey")
                station = station_dict.get(grid_key)

                found = any(channel.get("id") == station.get('id') for channel in output_xml.findall(".//channel"))
                if not found:
                    channel_element = ET.Element("channel", id=station.get('id'))
                    ET.SubElement(channel_element, "display-name").text = station.get('name')
                    ET.SubElement(channel_element, "icon", src=station.get('logo'))
                    output_xml.append(channel_element)

                # **Process videos in batches**
                video_iter = iter(tv_element.findall(".//MediaContainer/Video"))

                while True:
                    batch = list(itertools.islice(video_iter, batch_size))  # Get next batch
                    if not batch:
                        break

                    futures = [executor.submit(self.process_video, video, station, output_xml) for video in batch]
                    concurrent.futures.wait(futures)

                    # **Force Garbage Collection after each batch**
                    gc.collect()

        return output_xml
                
    def process_station(self, station, date, epg_channels):
        channel_root = ET.Element("tv", attrib={"channelGridKey": station})
        channel_root = self.read_epg_from_api(date, epg_channels.get(station), channel_root)

        date_folder = Path(f'{date}')
        filename = f'{station}_{date}.xml'
        file_path = date_folder / filename
        self.save_xml(file_path, channel_root)        
        return

    def process_xml(self, file_path):
        # print(file_path)
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            if root.tag == "tv": 
                return root 
        except ET.ParseError:
            print(f"Error parsing {file_path}")
            return None

    def generate_epg_from_media_file(self, date, date_media_file, epg_channels):
        media_root = ET.parse(date_media_file)
        channel_root = ET.Element("tv", attrib={"generator-info-name": "jgomez177", "generated-ts": ""})
        channel_root = self.generate_epg_style(epg_channels, media_root, channel_root)
        media_root.getroot().clear()
        
        epg_file = f'{date}_epg.xml'
        self.save_xml(epg_file, channel_root)
        return

    def generate_media_file(self, date, epg_channels):
        # station_list = list(epg_channels.keys())
        station_list = []
        station_count = 1
        for elem in epg_channels:
            station_list.append(elem)
            station_count += 1
            if station_count > 5:
                break
        stations_completed = 0

        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.process_station, station, date, epg_channels): station for station in station_list}

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                    stations_completed += 1
                except Exception as e:
                    print(f"Error processing station: {e}")

        elapsed_time = time.time() - start_time
        print(f'[NOTIFICATION - {self.client_name.upper()}] {date} Station List completed {stations_completed}: Elapsed time: {elapsed_time:.2f} seconds.')

        start_time = time.time()
        # Merge all station XML files
        input_folder = Path(f'{self.data_path}/{date}')
        xml_files = list(input_folder.glob("*.xml"))
        # print(xml_files)

        # merged_root = ET.Element("MergedTV")
        merged_root = ET.Element("MergedTV", attrib={"generator-info-name": "jgomez177", "generated-ts": ""})

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(self.process_xml, xml_files)

        for tv_element in results:
            if tv_element is not None:
                merged_root.append(tv_element)

        channel_media_root = ET.ElementTree(merged_root)
        date_media_file = Path(f'{self.data_path}/{date}_media.xml')

        with self.lock:
            try:
                with date_media_file.open("wb") as f:
                    channel_media_root.write(f, encoding="utf-8", xml_declaration=True)
            except Exception as e:
                print(f"[ERROR - {self.client_name.upper()}] Error writing XML file: {e}")

        elapsed_time = time.time() - start_time
        print(f'[NOTIFICATION - {self.client_name.upper()}] {date} MediaContainer XML completed {stations_completed}: Elapsed time: {elapsed_time:.2f} seconds.')

        self.generate_epg_from_media_file(date, date_media_file, epg_channels)

        if input_folder.exists():
            shutil.rmtree(input_folder)
        
        return

    def epg(self, args=None):
        print(f"[DEBUG - {self.client_name.upper()}] Running EPG Call")
        channels_by_geo, error = self.channels(args)
        epg_channels = self.generate_epg_station_list(channels_by_geo)

        if epg_channels:
            print(f"[DEBUG - {self.client_name.upper()}] Number of channels {len(epg_channels)}")
            # for elem in epg_channels:
            #     print(json.dumps(epg_channels[elem], indent=2))
            #     break
        desired_timezone = pytz.timezone('UTC')
        today = datetime.now(desired_timezone)

        today_date = (today).strftime("%Y-%m-%d")

        yesterday_date = (today + timedelta(days=-1)).strftime("%Y-%m-%d")
        yesterday_epg_file = f'{yesterday_date}_epg.xml'
        yesterday_media_file = f'{yesterday_date}_media.xml'

        output_root = ET.Element("tv", attrib={"generator-info-name": "jgomez177", "generated-ts": ""})
        # self.save_xml(yesterday_epg_file, output_root)  # Testing
        # self.save_xml(yesterday_media_file, output_root) # Testing

        update_today_epg = self.update_today_epg
        num_of_cached = 4
        days_of_data = 7

        def delete_file(filename):
            filepath = Path(f'{self.data_path}/{filename}')
            try:
                filepath.unlink()
                print(f"[NOTIFICATION - {self.client_name.upper()}] {filename} deleted.")
            except FileNotFoundError:
                pass
            except PermissionError:
                print(f"[ERROR - {self.client_name.upper()}] Permission denied: Unable to delete {filename}")
            return

        delete_file(yesterday_epg_file)
        delete_file(yesterday_media_file)

        print(f"[DEBUG - {self.client_name.upper()}] EPG Pass {update_today_epg}")
        if update_today_epg == 0:
            print(f"[INFO - {self.client_name.upper()}] Update Today's EPG data")
            self.generate_media_file(today_date, epg_channels)

        break_loop = False
        merge_dates = []
        for i in range(days_of_data):
            loop_date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            print(f'[NOTIFICATION - {self.client_name.upper()}] Collect data for {loop_date}')
            date_epg_file = f'{loop_date}_epg.xml'
            date_epg_file_path = Path(f'{self.data_path}/{date_epg_file}')
            if date_epg_file_path.exists():
                print(f'[NOTIFICATION - {self.client_name.upper()}] Using Saved Data for {loop_date}')
            else:
                # Generate EPG File for loop_date
                self.generate_media_file(loop_date, epg_channels)
                # Loop Date EPG to List
                break_loop = True
            merge_dates.append(date_epg_file)
            if break_loop: break

        self.generate_main_epg(merge_dates)

        with self.lock:
            update_today_epg += 1
            if update_today_epg >= num_of_cached:
                update_today_epg = 0
            self.update_today_epg = update_today_epg
        print(f"[DEBUG - {self.client_name.upper()}] EPG Call Complete")
        return

    def generate_main_epg(self, file_list):
        main_epg = f'{self.data_path}/epg.xml'

        unique_channels = set()
        channel_elements = []

        # Open the output file in write mode with streaming support
        with open(main_epg, "wb") as f_out:
            f_out.write(b'<?xml version="1.0" ?>\n')
            f_out.write(b'<tv generator-info-name="merged-script">\n')

            # FIRST PASS: Collect Channels
            for file in file_list:
                fullpath_file = f'{self.data_path}/{file}'
                print(f"[DEBUG - {self.client_name.upper()}] Processing Channels from {file}...")
                for event, elem in ET.iterparse(fullpath_file, events=("end",)):
                    if elem.tag == "channel":
                        channel_id = elem.get("id")
                        if channel_id not in unique_channels:
                            unique_channels.add(channel_id)
                            channel_elements.append(ET.tostring(elem, encoding="utf-8"))
                        elem.clear()  # Free memory
                    
                # Write all <channel> elements at the beginning
                for channel in channel_elements:
                    f_out.write(channel)

            # SECOND PASS: Collect Channels
            for file in file_list:
                fullpath_file = f'{self.data_path}/{file}'
                print(f"[DEBUG - {self.client_name.upper()}] Processing Programs from {file}...")
                for event, elem in ET.iterparse(fullpath_file, events=("end",)):
                    if elem.tag == "programme":
                        f_out.write(ET.tostring(elem, encoding="utf-8"))
                        elem.clear()  # Free memory

            # Close the root element in the output file
            f_out.write(b'</tv>')
        
        print(f"[INFO - {self.client_name.upper()}] EPG FIle Created")

        # **GZIP Compression Step**
        gzip_file = main_epg + ".gz"
        with open(main_epg, "rb") as f_in, gzip.open(gzip_file, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        print(f"[INFO - {self.client_name.upper()}] Compressed EPG FIle Created")
        return

    def rebuild_epg(self):
        folder_path = Path(f'{self.data_path}')
        file_types = ["20*", "epg.xml", "epg.xml.gz"]

        for type in file_types:
            for file in folder_path.glob(type):
                if file.is_file():
                    try:
                        file.unlink()
                    except:
                        print(f"[ERROR - {self.client_name.upper()}] Unable to delete {file}")
                    else:
                        print(f"[ERROR - {self.client_name.upper()}] {file} Deleted")

