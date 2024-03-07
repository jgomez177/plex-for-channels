# Plex for Channels

Current version: **1.08**

# About
This takes Plex Live TV Channels and generates an M3U playlist and EPG XMLTV file.

# Changes
 - Version 1.08: 
    - Improved Scheduler Processing. Improved API call timing/logging
 - Version 1.07: 
    - Updated Error Handling 
 - Version 1.06: 
    - Updates to how EPG data is pulled. XML files are initialized with the current day's EPG data. Then gradually added over the course of the next 30 min. to reduce number of API calls. 
    - Illegal character XML handling has been added.
    - PLEX_CODE env variable has been added. Controls which country(ies) this session will utilize

# Running
The recommended way of running is to pull the image from [GitHub](https://github.com/jgomez177/plex-for-channels/pkgs/container/plex-for-channels).

    docker run -d --restart unless-stopped --network=host -e PLEX_PORT=[your_port_number_here] -e PLEX_CODE=local[,us_west,etc.] --name  plex-for-channels ghcr.io/jgomez177/plex-for-channels
or

    docker run -d --restart unless-stopped -p [your_port_number_here]:7777 --name  plex-for-channels ghcr.io/jgomez177/plex-for-channels

You can retrieve the playlist and EPG via the status page.

    http://127.0.0.1:[your_port_number_here]

## Environement Variables
| Environment Variable | Description | Default |
|---|---|---|
| PLEX_PORT | Port the API will be served on. You can set this if it conflicts with another service in your environment. | 7777 |
| PLEX_CODE | What country streams will be hosted. <br>Multiple can be hosted using comma separation<p><p>ALLOWED_COUNTRY_CODES:<br>**us_east** - United States East Coast,<br>**us_west** - United States West Coast,<br>**local** - Local IP address Geolocation,<br>**ca** - Canada,<br>**uk** - United Kingdom,<br>**nz** - New Zealand,<br>**au** - Australia,<br>**mx** - Mexico,<br>**es**  - Spain  | local |

## Additional URL Parameters
| Parameter | Description |
|---|---|
| gracenote | "include" will utilize gracenote EPG information and filter to those streams utilizing Gracenote. "exclude" will filter those streams that do not have a matching gracenote EPG data. |

## Optional Custom Gracenote ID Matching

Adding a docker volume to /app/plex_data will allow you to add a custom comma delimited csv file to add or change any of the default gracenote matching for any plex channel

    docker run -d --restart unless-stopped --network=host -e PLEX_PORT=[your_port_number_here] -v [your_file_location_here]:/app/plex_data --name  plex-for-channels ghcr.io/jgomez177/plex-for-channels

Create a file called `plex_custom_tmsid.csv` with the following headers (case-sensitive):
| id |  name | tmsid | time_shift | 
|---|---|---|---|
| (required) id of the Plex channel (more on obtaining this ID below) | (optional) Easy to read name | (required) New/Updated Gracenote TMSID number for the channel | (optional) Shifting EPG data for the channel in hours. Ex: To shift the EPG 5 hours earlier, value would be -5 | 

Example

    id,name,tmsid,time_shift
    5e20b730f2f8d5003d739db7-63c1ec0e0aa23f984207af82,Ax Men by History,123425,-5


## Obtaining Plex ID for a Given Channel
Plex occasionally duplicates a name of a channel, therefore the easiest way to ensure uniqueness for each station is to utilize the plex assigned ID. If you are unsure about the ID you can either refer to the generated playlist and refer to the value located in `tvg-id` or refer to the associated json data for the playlist at:

    http://127.0.0.1:[your_port_number_here]/plex/[playlist_location]/channels.json

***

If you like this and other linear containers for Channels that I have created, please consider supporting my work.

[![](https://pics.paypal.com/00/s/MDY0MzZhODAtNGI0MC00ZmU5LWI3ODYtZTY5YTcxOTNlMjRm/file.PNG)](https://www.paypal.com/donate/?hosted_button_id=BBUTPEU8DUZ6J)
