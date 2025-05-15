# FSI MailFetch

## Overview
Hello there! The intention of this script is to fetch emails addressed to 
**fsi@fsi.uni-tuebingen.de** and create a nicely formatted overview to 
paste into the weekly meeting pad.

## Configuration
To use this script, you have to provide a mail account with a subscription to the
fsi mailing list. First, copy the sample config:
```
cp sample-config.json config.json
```
After this, enter your authentication data.

## Usage
The script `fsi-mailfetch.py` accepts these parameters:
- `--since YYYY-MM-DD`: fetch and process all mails from YYYY-MM-DD to now.
    This defaults to "today - 7 days", so there is no adjustment necessary if you call this script on a thursday.
- `--config file`: loads the configuration from file `file`.
    This defaults to `./config.json`.

At least under macOS, you can call this script with the following line to copy it's output directly to the clipboard:
```
python3 ./fsi-mailfetch.py | pbcopy
```

## FAQ
### Why do we use a separate pad for the mails?
The script intents to use a separate pad for the mails with the naming convention `fsi-sitzung-YYYY-MM-DD-mails` (effectively the link to the meeting pad suffixed with `-mails`). The reason behind this is that our hedgedoc instance has a limit of 100.000 characters per pad. To avoid issues with that limit, we use a separate one.

## Last advice
Feel free to use and contribute!
If you made any contributions, please write down your name to the AUTHORS file.
