import secrets, requests, json, pytz, gzip, csv, os, re, time
from datetime import datetime, timedelta
# from urllib.parse import quote
# from io import StringIO
import xml.etree.ElementTree as ET

class Client:
    def __init__(self):

        # self.sessionID = ""
        # self.sessionToken = ""
        self.sessionAt = {}
        self.session = requests.Session()
        self.device = None
        self.load_device()
        self.offset = 0
        self.channel_list = []
        self.stations = []
        self.country_stations = {}
        self.sessionToken_list = {}
        self.sessionID_list = {}
        self.epg_data = {}
        self.genres = {}
        self.epgLastUpdatedAt = {}

        self.headers = {
                    'accept': 'application/json, text/javascript, */*; q=0.01',
                    'accept-language': 'en',
                    # 'content-length': '0',
                    'origin': 'https://app.plex.tv',
                    'referer': 'https://app.plex.tv/',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Linux"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-site',
                    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                }

        self.params = {
            'X-Plex-Product': 'Plex Web',
            'X-Plex-Version': '4.139.0',
            'X-Plex-Provider-Version': '6.5',
            'X-Plex-Client-Identifier': self.device,
            'X-Plex-Language': 'en',
            'X-Plex-Platform': 'Chrome',
            'X-Plex-Platform-Version': '129.0',
            'X-Plex-Features': 'external-media,indirect-media,hub-style-list',
            'X-Plex-Model': 'hosted',
            'X-Plex-Device': 'Linux',
            'X-Plex-Device-Name': 'Chrome',
            'X-Plex-Device-Screen-Resolution': '1282x929,1920x1080',
            'X-Plex-Language': 'en',
                }
        
        self.x_forward = {"local": {"X-Forwarded-For":""},
                          "uk": {"X-Forwarded-For":"178.238.11.6"},
                          "ca": {"X-Forwarded-For":"192.206.151.131"}, 
                          "us_clt": {"X-Forwarded-For":"108.82.206.181"},
                          "us_sea": {"X-Forwarded-For":"159.148.218.183"},
                          "us_nyc": {"X-Forwarded-For":"85.254.181.50"},
                          "us_lax": {"X-Forwarded-For":"76.81.9.69"},
                          "us_east": {"X-Forwarded-For":"108.82.206.181"},
                          "us_west": {"X-Forwarded-For":"76.81.9.69"},
                          "us": {"X-Forwarded-For": "185.236.200.172"},
                          "mx": {"X-Forwarded-For": "200.68.128.83"},
                          "es": {"X-Forwarded-For": "88.26.241.248"},
                          "ca": {"X-Forwarded-For": "192.206.151.131"},
                          "au": {"X-Forwarded-For": "110.33.122.75"},
                          "nz": {"X-Forwarded-For": "203.86.207.83"},
                        }

    def load_device(self):
        try:
            with open("plex-device.json", "r") as f:
                self.device = json.load(f)
        except FileNotFoundError:
            self.device = secrets.token_hex(12)
            with open("plex-device.json", "w") as f:
                json.dump(self.device, f)

    def token(self, country_code):
        desired_timezone = pytz.timezone('UTC')
        current_date = datetime.now(desired_timezone)
        # if (self.sessionID_list.get(country_code) is not None) and (time.time() - self.sessionAt.get(country_code, 0)) < 4 * 60 * 60:
        if (self.sessionID_list.get(country_code) is not None) and (current_date - self.sessionAt.get(country_code, datetime.now())) < timedelta(hours=4):
            # print(f'Returning valid token for {country_code}')
            return self.sessionID_list[country_code], None
        
        if country_code in self.x_forward.keys():
            self.headers.update(self.x_forward.get(country_code))

        try:
            response = self.session.post('https://clients.plex.tv/api/v2/users/anonymous', params=self.params, headers=self.headers)
        except Exception as e:
            return None, (f"Exception type Error: {type(e).__name__}")    
        
        if (200 <= response.status_code <= 201):
            # print('Return for sign-in')
            resp = response.json()
            # print(resp)
        else:
            print(f"HTTP failure {response.status_code}: {response.text}")
            return None, f"HTTP failure {response.status_code}: {response.text}"

        token = resp.get('authToken', None)
        # print(token)
        self.sessionToken_list.update({country_code: token})

        self.sessionID_list.update({country_code: token})
        self.sessionAt.update({country_code: current_date})

        print(f"New token for {country_code} generated at {(self.sessionAt.get(country_code)).strftime('%Y-%m-%d %H:%M.%S %z')}")
        return token, None

    def genre(self, country_code = "local"):
        token, error = self.token(country_code)
        if error: return None, token, error

        if country_code in self.x_forward.keys():
            self.headers.update(self.x_forward.get(country_code))

        resp, error = self.api(country_code, "")
        if error: return None, error

        genres_temp = {}


        feature = resp.get('MediaProvider', {}).get('Feature',[])
        for elem in feature:
            if 'GridChannelFilter' in elem:
                genres_temp = elem.get('GridChannelFilter')
                break
        # GridChannelFilter = feature.get('GridChannelFilter',[])

        # print(genres_temp)

        genres = {}

        for genre in genres_temp:
            genres.update({genre.get('identifier'): genre.get('title')})

        self.genres.update({country_code: genres})

        return genres, None

    def generate_channels(self, resp, genre = None):
        # print (len(resp))
        channels = resp.get("MediaContainer").get("Channel")

        if channels is None:
            print(f"No items found for {genre}")
            return 

        for elem in channels:
            callSign = elem.get('callSign')
            logo = elem.get('thumb')
            slug = elem.get('slug')
            title = elem.get('title')
            id = elem.get('id')

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
                note = f"Note: DRM is set to True in at least one item in {slug}"
                print(note)
            else:
                new_item = {'call_sign': callSign,
                                      'slug': slug,
                                      'name': title,
                                      'logo': logo,
                                      'id': id,
                                      'key': plex_key,
                                    }
                if genre is not None:
                    new_item.update({'group': [genre]})

                check_callSign = next(filter(lambda d: d.get('slug','') == slug, self.stations), None)
                if check_callSign is not None:
                    new_group = check_callSign.get('group')
                    new_group.append(genre)
                    check_callSign.update({'group': new_group})
                else:
                    self.stations.append(new_item)
        return

    def channels(self, country_code = "local"):
        token, error = self.token(country_code)
        if error: return None, token, error

        plex_tmsid_url = "https://raw.githubusercontent.com/jgomez177/plex-for-channels/main/plex_tmsid.csv"
        plex_custom_tmsid = 'plex_data/plex_custom_tmsid.csv'

        if country_code in self.x_forward.keys():
            self.headers.update(self.x_forward.get(country_code))

        genres, error = self.genre(country_code)
        if error: return None, token, error

        self.stations = []

        for genre in genres.keys():
            resp, error = self.api(country_code, f"lineups/plex/channels?genre={genre}")
            if error: return None, token, error
            self.generate_channels(resp, genres.get(genre))
        
        if len(self.stations) == 0:
            print("No channels match genres")
            resp, error = self.api(country_code, f"lineups/plex/channels")
            if error: return None, token, error
            self.generate_channels(resp)
                
        tmsid_dict = {}
        tmsid_custom_dict = {}

        # Fetch the CSV file from the URL
        response = requests.get(plex_tmsid_url)

        # Check if request was successful
        if response.status_code == 200:
            # Read in the CSV data
            reader = csv.DictReader(response.text.splitlines())
        else:
            # Use local cache instead
            print("Failed to fetch the CSV file. Status code:", response.status_code)
            print("Using local cached file.")
            with open('plex_tmsid.csv', mode='r') as file:
                reader = csv.DictReader(file)
       
        for row in reader:
            tmsid_dict[row['id']] = row

        if os.path.exists(plex_custom_tmsid):
            # File exists, open it
            with open(plex_custom_tmsid, mode='r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    tmsid_custom_dict[row['id']] = row

        tmsid_dict.update(tmsid_custom_dict)

        #self.stations = {key: {**value, 'tmsid': tmsid_dict[key]['tmsid'], 'time_shift': tmsid_dict[key]['time_shift']} 
        #                 if key in tmsid_dict else value for key, value in self.stations.items()}

        self.stations = [{**entry, 'tmsid': tmsid_dict[entry["id"]]['tmsid'], 'time_shift': tmsid_dict[entry["id"]]['time_shift']}
                         if entry["id"] in tmsid_dict and tmsid_dict[entry["id"]]['time_shift'] != ''
                         else {**entry, 'tmsid': tmsid_dict[entry["id"]]['tmsid']} if entry["id"] in tmsid_dict and tmsid_dict[entry["id"]]['tmsid'] != ''
                         else entry
                         for entry in self.stations]

        self.stations = sorted(self.stations, key=lambda x: (not x.get("call_sign", False), x["name"]))
        self.country_stations.update({country_code: self.stations})

        return self.stations, token, None

    def api(self, country_code, cmd, api_params = None, api_headers = None, data=None):
        token, error = self.token(country_code)
        if api_params is None:
            api_params = self.params
        if api_headers is None:
            api_headers = self.headers
        
        if error:
            return None, error

        if token is not None:
            self.params.update({'X-Plex-Token': token})
        # print(headers)
        url = f"https://epg.provider.plex.tv/{cmd}"
        if data:
            try:
                response = self.session.put(url, data=data, params=api_params, headers=api_headers, timeout=300)
            except Exception as e:
                return None, (f"Exception type Error: {type(e).__name__}")    
        else:
            try:
                response = self.session.get(url, params=api_params, headers=api_headers, timeout=300)
            except Exception as e:
                return None, (f"Exception type Error: {type(e).__name__}")    
        if response.status_code != 200:
            return None, f"HTTP failure {response.status_code}: {response.text}"
        # print(response.text)
        
        return response.json(), None

    def read_epg_from_api(self, run_datetime, start_datetime, range_val, id_values, country_code, verbose = False):
        token, error = self.token(country_code)
        if error: return error
        epg_headers =   {
                        'authority': 'epg.provider.plex.tv',
                        'accept': 'application/json, text/javascript, */*; q=0.01',
                        'accept-language': 'en',
                        'origin': 'https://app.plex.tv',
                        'referer': 'https://app.plex.tv/',
                        'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                        'sec-ch-ua-mobile': '?0',
                        'sec-ch-ua-platform': '"Linux"',
                        'sec-fetch-dest': 'empty',
                        'sec-fetch-mode': 'cors',
                        'sec-fetch-site': 'same-site',
                        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                        'x-plex-client-identifier': self.device,
                        'x-plex-device': 'Linux',
                        'x-plex-device-screen-resolution': '1098x1265,2560x1440',
                        'x-plex-drm': 'widevine',
                        'x-plex-features': 'external-media,indirect-media,hub-style-list',
                        'x-plex-language': 'en',
                        'x-plex-model': 'hosted',
                        'x-plex-platform': 'Chrome',
                        'x-plex-platform-version': '122.0',
                        'x-plex-product': 'Plex Web',
                        'x-plex-provider-version': '6.5',
                        'x-plex-restriction-profile': 'undefined',
                        'x-plex-text-format': 'plain',
                        'x-plex-token': token,
                        'x-plex-version': '4.125.1',
                    }

        print(f'Retrieving {country_code} EPG data for {start_datetime.strftime("%Y-%m-%d")} through {(start_datetime + timedelta(days=range_val)).strftime("%Y-%m-%d")}')

        j = 0
        k = 0
        # Start time
        start_time = time.time()

        for id in id_values:
            k += 1
            if verbose:
                print(f"Retriving data {k} for {id}")
            id_data = []
            for i in range(range_val + 1):
                resp_metadata = {}
                range_datetime = start_datetime + timedelta(days=i)
                # start_time = quote(start_datetime.strftime("%Y-%m-%d %H:00:00.000Z"))
                range_time = range_datetime.strftime("%Y-%m-%d")

                params =    {'channelGridKey': id.split("-", 1)[1] if "-" in id else id,
                             'date': range_time
                            }
                resp, error = self.api(country_code, 'grid', params, epg_headers)
                if error: return(None, error)
                j += 1
                match j:
                    case _ if j % 300 == 0:
                        time.sleep(16)
                        elapsed_time = time.time() - start_time
                        print(f"Continuing to retrive {country_code} EPG data....Elapsed time: {elapsed_time:.2f} seconds. {j} Channels parsed. Please wait")
                    case _ if j % 150 == 0:
                        time.sleep(8)
                        elapsed_time = time.time() - start_time
                        print(f"Continuing to retrive {country_code} EPG data....Elapsed time: {elapsed_time:.2f} seconds. {j} Channels parsed")
                    case _ if j % 20 == 0:
                        # print("Loading EPG data...")
                        time.sleep(1)

                resp_metadata.update({"Metadata": resp["MediaContainer"]["Metadata"],
                                      "date": range_time,
                                      "id": id})
                id_data.append(resp_metadata)

            #id_data_old = self.epg_data.get(country_code, {}).get(id, [])
            #id_data_dict = {id: id_data + id_data_old}
                
            country_data = self.epg_data.get(country_code, {})
            country_data.update({id: country_data.get(id, []) + id_data})

            self.epg_data.update({country_code: country_data})
            self.epgLastUpdatedAt.update({country_code: run_datetime})

        elapsed_time = time.time() - start_time
        print(f"Retrieving {country_code} EPG data complete. Elapsed time: {elapsed_time:.2f} seconds. {j} Channels parsed.")
        return None


    def update_epg(self, country_code):
        # print("Running EPG")
        epg_update_value = 4 # Value for updating EPG data in hours 
        range_val = 3         # Number of EPG dates to pull range_val + 1 times

        # Set desired timezone as 'UTC'
        desired_timezone = pytz.timezone('UTC')

        # Get the current time in the desired timezone
        start_datetime = datetime.now(desired_timezone)
        # start_time = quote(start_datetime.strftime("%Y-%m-%d %H:00:00.000Z"))
        # start_time = start_datetime.strftime("%Y-%m-%d")

        if country_code in self.x_forward.keys():
            self.headers.update(self.x_forward.get(country_code))

        station_list = self.country_stations.get(country_code, [])

        if len(station_list) == 0:
            print("Run channels to load self.channel_list")
            station_list, token, error = self.channels(country_code)
            if error: return error

        # Extracting all 'id' values
        id_values = [d['id'] for d in station_list]
        # id_values = [id_values[0],id_values[1]]

        if self.epg_data.get(country_code):
            # print('Returning cached data')
            today = start_datetime.date()
            if (start_datetime - self.epgLastUpdatedAt.get(country_code, start_datetime)) >= timedelta(hours=epg_update_value):
                print(f"{start_datetime - self.epgLastUpdatedAt.get(country_code, start_datetime)}: Updating data for {country_code}")
                for key, value_list in self.epg_data.get(country_code).items():
                    filtered_list = [item for item in value_list if datetime.strptime(item["date"], "%Y-%m-%d").date() > today]
                    self.epg_data.get(country_code)[key] = filtered_list

            # Using the first entry in self.epg_data, pull dates 
            first_entry_dates = [datetime.strptime(item["date"], "%Y-%m-%d").date() for item in self.epg_data[country_code][list(self.epg_data[country_code].keys())[0]]]

            # List of pulled EPG data between now and range_val + 1 
            dates_between_now_and_x_days = [(start_datetime + timedelta(days=i)).date() for i in range(range_val + 1)]

            # Check if each date is present in the list of dates from the first entry
            dates_not_present = [pytz.utc.localize(datetime.combine(date, datetime.min.time())) for date in dates_between_now_and_x_days if date not in first_entry_dates]

            # Pull data for any missing date
            if len(dates_not_present) > 0:
                error = self.read_epg_from_api(start_datetime, dates_not_present[0], 0, id_values, country_code)
                if error: return error
            return None
        else:
            print("Day One Initialization of EPG data")
            error = self.read_epg_from_api(start_datetime, start_datetime, 0, id_values, country_code)
            if error: return error

        return None

    def epg_json(self, country_code):
        error_code = self.update_epg(country_code)
        if error_code:
            print("error") 
            return None, error_code
        return self.epg_data, None

    def strip_illegal_characters(self, xml_string):
        # Define a regular expression pattern to match illegal characters
        illegal_char_pattern = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')

        # Replace illegal characters with an empty string
        clean_xml_string = illegal_char_pattern.sub('', xml_string)

        return clean_xml_string

    def parse_date(self, date_str):
        if date_str == '': return date_str
        formats = ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]


        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                pass
        print(f"Error: Could not parse date: {date_str}")
        return ''
        


    def create_programme_element(self, timeline, media, channel_id, root):
        epoch_begin_time = int(media['beginsAt'])
        start_datetime = datetime.utcfromtimestamp(epoch_begin_time).replace(tzinfo=pytz.utc)

        epoch_end_time = int(media['endsAt'])
        end_datetime = datetime.utcfromtimestamp(epoch_end_time).replace(tzinfo=pytz.utc)

        programme = ET.SubElement(root, "programme", attrib={"channel": channel_id,
                                                             "start": start_datetime.strftime("%Y%m%d%H%M%S %z"),
                                                             "stop": end_datetime.strftime("%Y%m%d%H%M%S %z")})

        # Add sub-elements to programme
        originallyAvailableAt = self.parse_date(timeline.get('originallyAvailableAt', ''))

        if timeline.get('grandparentType') is None:
            title = ET.SubElement(programme, "title")
            title.text = self.strip_illegal_characters(timeline.get('title',''))
        else:
            title = ET.SubElement(programme, "title")
            title.text = self.strip_illegal_characters(timeline.get('grandparentTitle',''))
            sub_title = ET.SubElement(programme, "sub-title")
            sub_title.text = self.strip_illegal_characters(timeline.get('title',''))

        if originallyAvailableAt != '':
            # "originallyAvailableAt": "2016-04-05T12:00:00Z",
            if timeline.get('originallyAvailableAt') == start_datetime.strftime("%Y-%m-%dT%H:%M:00Z"):
                live = ET.SubElement(programme, "live")

        if timeline.get('type') == 'movie':
            category_elem = ET.SubElement(programme, "category")
            category_elem.text = timeline.get('type').capitalize()
        else:
            episode_num_onscreen = ET.SubElement(programme, "episode-num", attrib={"system": "onscreen"})
            if timeline.get('index') is None:
                episode_num_onscreen.text = originallyAvailableAt.strftime("%Y-%m-%d")
            else:
                episode_num_onscreen.text = f"S{timeline.get('parentIndex', 0):02d}E{timeline.get('index', 0):02d}"

        if timeline.get('desc') != '':
            desc = ET.SubElement(programme, "desc")
            desc.text = self.strip_illegal_characters(timeline.get('summary',''))

        image_list = timeline.get('Image', [])
        order = {"coverPoster": 0, "coverArt": 1, "snapshot": float('inf')}
        sorted_image_list = sorted(image_list, key=lambda x: (order.get(x["type"], float('inf')), x["type"]))
        # print(sorted_timeline_items)
        art = next((item["url"] for item in sorted_image_list), '')
        if art != '':    
            icon_programme = ET.SubElement(programme, "icon", attrib={"src": art})
        
        if originallyAvailableAt != '':
            date = ET.SubElement(programme, "date")
            # originallyAvailableAt = self.parse_date(timeline.get('originallyAvailableAt', ''))
            # date.text = datetime.strptime(timeline.get('originallyAvailableAt', ''), "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y%m%d")
            date.text = originallyAvailableAt.strftime("%Y%m%d")

        categories = []
        for genres in timeline.get('Genre', []):
            categories.append(genres.get('tag', ''))
            

        unique_list = []
        for item in categories:
            if item not in unique_list:
                unique_list.append(item)

        if any(cat_elem in unique_list for cat_elem in ['News', 'Music']):
            # Check if <category>movie</category> exists and remove it
            for elem in programme.findall(".//category"):
                if elem.text.lower() == 'movie':
                    programme.remove(elem)

            # movie_category = programme.find(".//category[text()='Movie']")
            # if movie_category is not None:
            #     programme.remove(movie_category)

        for category in unique_list:
            category_elem = ET.SubElement(programme, "category")
            category_elem.text = category

        return root

    def read_epg_data_for_xml(self, metadata, channel_id, root):
        for timeline in metadata:
            # Create programme element
            for media in timeline['Media']:
                root = self.create_programme_element(timeline, media, channel_id, root)

        return root

    def create_xml_file(self, country_code):
        error_code = self.update_epg(country_code)
        if error_code: return error_code

        xml_file_path        = f"epg-{country_code}.xml"
        compressed_file_path = f"{xml_file_path}.gz"

        station_list = self.country_stations.get(country_code, [])

        if len(station_list) == 0:
            print("Run channels to load self.channel_list")
            station_list, token, error_code = self.channels(country_code)
            if error_code: return None, error_code

        root = ET.Element("tv", attrib={"generator-info-name": "jgomez177", "generated-ts": ""})

        # Create Channel Elements from list of Stations
        for station in station_list:
            channel = ET.SubElement(root, "channel", attrib={"id": station["id"]})
            display_name = ET.SubElement(channel, "display-name")
            display_name.text = self.strip_illegal_characters(station["name"])
            icon = ET.SubElement(channel, "icon", attrib={"src": station["logo"]})

        for key, value_list in self.epg_data.get(country_code).items():
            for entry in value_list:
                root = self.read_epg_data_for_xml(entry["Metadata"], key, root)

        # Sort the <programme> elements by channel and then by start
        sorted_programmes = sorted(root.findall('.//programme'), key=lambda x: (x.get('channel'), x.get('start')))

        # Clear the existing elements in the root
        # Clear the existing <programme> elements in the root
        for child in root.findall('.//programme'):
            root.remove(child)

        # Append the sorted <programme> elements to the root
        for element in sorted_programmes:
            root.append(element)

        # Create an ElementTree object
        tree = ET.ElementTree(root)
        ET.indent(tree, '  ')

        # Create a DOCTYPE declaration
        doctype = '<!DOCTYPE tv SYSTEM "xmltv.dtd">'

        # Concatenate the XML and DOCTYPE declarations in the desired order
        xml_declaration = '<?xml version=\'1.0\' encoding=\'utf-8\'?>'
        output_content = xml_declaration + '\n' + doctype + '\n' + ET.tostring(root, encoding='utf-8').decode('utf-8')

        # Write the concatenated content to the output file
        with open(xml_file_path, "w", encoding='utf-8') as f:
            f.write(output_content)

        with open(xml_file_path, 'r') as file:
            xml_data = file.read()

        # Compress the XML file
        with open(xml_file_path, 'rb') as file:
            with gzip.open(compressed_file_path, 'wb') as compressed_file:
                compressed_file.writelines(file)

        return None
        

                






