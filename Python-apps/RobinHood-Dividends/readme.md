This is a simple app to display your dividends for RobinHood because the limit this information to mobile only and I wanted to be able to view it on a computer with a large screen, but a tiny phone screen with annoying touch screen and annoying navigation issues that come from that.

go to:
<a href="https://robinhood.com/account/reports-statements/activity-reports">https://robinhood.com/account/reports-statements/activity-reports</a>
generate a report from the oldest possible date to todays date, which is about 5 years of history.
This may take hours or a day, so if you want to use this, go ahead and request one be made before you bother with anything else.

For older purchase information you have to go to:
<A href="https://robinhood.com/account/history">https://robinhood.com/account/history</a>
scroll down, let it load and keep repeating this until you reach the start of your account.

There may be a better way to do this, but it is all I know.

Step 1.
In the "Robinhood-fetch.py" file, open it in a text editor like notepad
You will see these lines near the top.

# pip install yfinance
# (Run the above install a second time in a row, if you get an error)

You need to open a command prompt, for me I have to do it as administrator,
type:
pip install yfinance
as the note says, if you get an error with red text, try running it again, hopefully it doesn't get an error this second time.

Step 2.
After that you see the filenames:

# Update with your actual Robinhood CSV filename
ROBINHOOD_CSV_PATH = "robinhood_export.csv"
CACHE_FILE_PATH = "dividends_cache.json"

Rename your hexadecimal filename you downloaded that is something like "A7FC2-BEA23-6FD2.CSV"
rename it to "robinhood_export.csv"

in the command prompt run:
py Robinhood-fetch.py
This will take a little while and it will 
