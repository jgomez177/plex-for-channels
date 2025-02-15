# Plex for Channels

Current version: **4.00**

# About
Generates M3U playlists and EPG XMLTV files from Plex linear feeds.

If you like this and other linear containers for Channels that I have created, please consider supporting my work.

[![](https://pics.paypal.com/00/s/MDY0MzZhODAtNGI0MC00ZmU5LWI3ODYtZTY5YTcxOTNlMjRm/file.PNG)](https://www.paypal.com/donate/?hosted_button_id=BBUTPEU8DUZ6J)

Or Even Better support the Girl Scouts with the purchase of cookies for the 2025 campaign:

Site 1
[<img src="https://townsquare.media/site/191/files/2024/01/attachment-cookie.jpg" width=400/>](https://digitalcookie.girlscouts.org/scout/charlotte816794)

Site 2
[<img src="https://townsquare.media/site/191/files/2024/01/attachment-cookie.jpg" width=400/>](https://digitalcookie.girlscouts.org/scout/mckenna899691)

# Changes
 - Version 4.00
   - Total revamp of Plex Project!!!
   - Improved threading capability, updated web interface
   - Removed need for PLEX_CODE variable, now handled through url parameters
   - PLEX_PORT has been modified to PORT

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
| PORT | Port the API will be served on. You can set this if it conflicts with another service in your environment. | 7777 |

## Additional URL Parameters
| Parameter | Description | Default
|---|---|---|
| gracenote | "include" will utilize gracenote EPG information and filter to those streams utilizing Gracenote. "exclude" will filter those streams that do not have a matching gracenote EPG data. | 
| regions | Identify regions wanted in playlist. Can utilize multiple regions | local

