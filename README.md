# Plex for Channels

Current version: **1.04**

# About
This takes Plex Live TV Channels and generates an M3U playlist and EPG XMLTV file.

# Running
The recommended way of running is to pull the image from [GitHub](https://github.com/jgomez177/plex-for-channels/pkgs/container/plex-for-channels).

## Environement Variables
| Environment Variable | Description | Default |
|---|---|---|
| PLEX_PORT | Port the API will be served on. You can set this if it conflicts with another service in your environment. | 7777 |

## Additional URL Parameters
| Parameter | Description |
|---|---|
| gracenote | "include" will utilize gracenote EPG information and filter to those streams utilizing Gracenote. "exclude" will filter those streams that do not have a matching gracenote EPG data. |
