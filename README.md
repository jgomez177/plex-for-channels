# Linear Channel Collection

Current version: **5.1.2**

# About
Generates M3U playlists and XMLTV EPG files for the following linear platforms:
 - Plex
 - FreeLiveSports

If you like this and other linear containers that I have created, please consider supporting my work.

[![](https://pics.paypal.com/00/s/MDY0MzZhODAtNGI0MC00ZmU5LWI3ODYtZTY5YTcxOTNlMjRm/file.PNG)](https://www.paypal.com/donate/?hosted_button_id=BBUTPEU8DUZ6J)

## Environement Variables
| Environment Variable | Description | Default |
|---|---|---|
| PORT | Port the API will be served on. You can set this if it conflicts with another service in your environment. | 7777 |

## Additional URL Parameters
| Parameter | Description | Default
|---|---|---|
| gracenote | "include" will utilize gracenote EPG information and filter to those streams utilizing Gracenote. "exclude" will filter those streams that do not have a matching gracenote EPG data. | 
| regions | (Plex) Identify regions wanted in playlist. Can utilize multiple regions | local

