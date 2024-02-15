# Plex for Channels

Current version: **1.05**

# About
This takes Plex Live TV Channels and generates an M3U playlist and EPG XMLTV file.

# Running
The recommended way of running is to pull the image from [GitHub](https://github.com/jgomez177/plex-for-channels/pkgs/container/plex-for-channels).

    docker run -d --restart unless-stopped --network=host -e PLEX_PORT=[your_port_number_here] --name  plex-for-channels ghcr.io/jgomez177/plex-for-channels
or

    docker run -d --restart unless-stopped -p [your_port_number_here]:7777 --name  plex-for-channels ghcr.io/jgomez177/plex-for-channels

You can retrieve the playlist and EPG via the status page.

    http://127.0.0.1:[your_port_number_here]

## Environement Variables
| Environment Variable | Description | Default |
|---|---|---|
| PLEX_PORT | Port the API will be served on. You can set this if it conflicts with another service in your environment. | 7777 |

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


