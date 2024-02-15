import secrets, requests, json, time, pytz, gzip, csv
from datetime import datetime, timedelta
from urllib.parse import quote
import xml.etree.ElementTree as ET

class Client:
    def __init__(self):

        # self.sessionID = ""
        # self.sessionToken = ""
        # self.sessionAt = 0
        self.session = requests.Session()
        self.device = None
        self.load_device()
        self.offset = 0
        self.channel_list = []
        self.stations = []
        self.country_stations = {}
        self.sessionToken_list = {}
        self.sessionID_list = {}

        self.headers = {
                    'authority': 'clients.plex.tv',
                    'accept': 'application/json, text/javascript, */*; q=0.01',
                    'accept-language': 'en',
                    # 'content-length': '0',
                    'origin': 'https://app.plex.tv',
                    'referer': 'https://app.plex.tv/',
                }

        self.params = {
            'X-Plex-Product': 'Plex Web',
            'X-Plex-Version': '4.120.1',
            'X-Plex-Client-Identifier': self.device,
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
        if (self.sessionID_list.get(country_code) is not None) and (time.time() - self.sessionAt) < 4 * 60 * 60:
            # print(f'Returning valid token for {country_code}')
            return self.sessionID_list[country_code], None
        
        if country_code in self.x_forward.keys():
            self.headers.update(self.x_forward.get(country_code))

        try:
            response = self.session.post('https://clients.plex.tv/api/v2/users/anonymous', params=self.params, headers=self.headers)
        except requests.ConnectionError as e:
            print("Connection Error.")
            print(str(e))
            return None, f"Connection Error. {str(e)}"
        
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
        self.sessionAt = time.time()

        print(f"New token for {country_code} generated at {datetime.fromtimestamp(self.sessionAt).strftime('%Y-%m-%d %H:%M.%S %z')}")
        return token, None

    def channels(self, country_code = "local"):
        token, error = self.token(country_code)

        print (country_code)

        if country_code in self.x_forward.keys():
            self.headers.update(self.x_forward.get(country_code))

        #    gracenoteID = self.load_gracenote()
        resp, error = self.api(country_code, "lineups/plex/channels")
        if error:
            return None, error

        self.stations = []

        # print (len(resp))
        channels = resp.get("MediaContainer").get("Channel")
        # print (len(channels))

        #if len(channels) > 0:
        #    print(json.dumps(channels[0], indent=2))

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
                self.stations.append({'call_sign': callSign,
                                      'slug': slug,
                                      'name': title,
                                      'logo': logo,
                                      'id': id,
                                      'key': plex_key
                                    })
                
        tmsid_dict = {}
        with open('plex_data/plex_tmsid.csv', mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                tmsid_dict[row['id']] = row

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
            response = self.session.put(url, data=data, params=api_params, headers=api_headers)
        else:
            response = self.session.get(url, params=api_params, headers=api_headers)
        if response.status_code != 200:
            return None, f"HTTP failure {response.status_code}: {response.text}"
        # print(response.text)
        
        return response.json(), None

    def parse_date(self, date_str):
        formats = ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                pass

        return ""
        raise ValueError(f"Could not parse date: {date_str}")
    
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
            title.text = timeline.get('title','')
        else:
            title = ET.SubElement(programme, "title")
            title.text = timeline.get('grandparentTitle','')
            sub_title = ET.SubElement(programme, "sub-title")
            sub_title.text = timeline.get('title','')

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
            desc.text = timeline.get('summary','')

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

    def read_epg_data(self, resp, channel_id, root):

        # for entry in resp["MediaContainer"]:
        metadata = resp.get("MediaContainer").get("Metadata")
        # print(json.dumps(metadata, indent=2))            

        for timeline in metadata:
            # Create programme element
            for media in timeline['Media']:
                root = self.create_programme_element(timeline, media, channel_id, root)

        return root

    def epg(self, country_code = "local"):
        print("Running EPG")
        xml_file_path        = f"epg-{country_code}.xml"
        compressed_file_path = f"{xml_file_path}.gz"
        token, error = self.token(country_code)

        # Set your desired timezone, for example, 'UTC'
        desired_timezone = pytz.timezone('UTC')

        epg_headers =   {
                        'authority': 'epg.provider.plex.tv',
                        'accept': 'application/json, text/javascript, */*; q=0.01',
                        'accept-language': 'en',
                        'origin': 'https://app.plex.tv',
                        'referer': 'https://app.plex.tv/',
                        'x-plex-client-identifier': self.device,
                        'x-plex-text-format': 'plain',
                        'x-plex-token': token,
                        'x-plex-version': '4.122.0',
                        'x-plex-provider-version': '6.5'
                    }

        # Get the current time in the desired timezone
        start_datetime = datetime.now(desired_timezone)
        # start_time = quote(start_datetime.strftime("%Y-%m-%d %H:00:00.000Z"))
        start_time = start_datetime.strftime("%Y-%m-%d")


        if country_code in self.x_forward.keys():
            self.headers.update(self.x_forward.get(country_code))

        station_list = self.country_stations.get(country_code, [])

        if len(station_list) == 0:
            print("Run channels to load self.channel_list")
            station_list, token, error = self.channels(country_code)

        # Extracting all 'id' values
        id_values = [d['id'] for d in station_list]
        group_size = 100
        grouped_id_values = [id_values[i:i + group_size] for i in range(0, len(id_values), group_size)]

        root = ET.Element("tv", attrib={"generator-info-name": "jgomez177", "generated-ts": ""})



        # Create Channel Elements from list of Stations
        for station in station_list:
            channel = ET.SubElement(root, "channel", attrib={"id": station["id"]})
            display_name = ET.SubElement(channel, "display-name")
            display_name.text = station["name"]
            icon = ET.SubElement(channel, "icon", attrib={"src": station["logo"]})

        # id_values = ['5e20b730f2f8d5003d739db7-644c4bc17472b186783f35a0',]
        # Create Programme Elements
        for i in range(2):
            # Add one day to the current datetime
            range_datetime = start_datetime + timedelta(days=i)

            # start_time = quote(start_datetime.strftime("%Y-%m-%d %H:00:00.000Z"))
            start_time = range_datetime.strftime("%Y-%m-%d")

            print(f"Day {i} run for {start_time}")
            for id in id_values:
                # print("Initial Run")
                params =    {'channelGridKey': id.split("-", 1)[1] if "-" in id else id,
                             'date': start_time
                            }
                # print(params['channelGridKey'])
                resp, error = self.api(country_code, 'grid', params, epg_headers)
                if error:
                    print(error)
                    return(None, error)        

                # print(json.dumps(resp["meta"]))
                # json_filename = f'{id.split("-", 1)[1] if "-" in id else id}-{start_time}.json'
                # with open(json_filename, 'w') as the_file:
                #     the_file.write(json.dumps(resp, indent=2, sort_keys=True))


                root = self.read_epg_data(resp, id, root)




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

        return(xml_file_path, None)