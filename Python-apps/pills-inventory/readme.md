version 0.3.3 (beta) note this was updated a few times today, while keeping the same version)
- I haven't tested everything, but pretty sure it's fine.
- The beta features are:
- Hiding/censoring information and saving that as a setting. (remove stuff you don't want to see, simplify)
- Saving when you click "Refill Now" with messaging asking if you want to -1 to refill count and option to cancel.
- Added Save `Log-YEAR.txt` and `Refills-YEAR.txt` for logging information.
- Added `Settings.ini` for some of the settings.
- Added File/Save with a list of what is saved, this should be unnecessary, but is likely a good idea for now to hopefully avoid losing progress.

<HR>

This is version 0.3.2
- Added Pharmacy hours + phone number. (black if closing in 1+ hours, red/bold if closing in 1 or less or is already closed.)
- (the new section also collapses out of view)
<img src="https://github.com/LockMan007/PixelSwirl/blob/main/Python-apps/pills-inventory/pharmacy2.png">

<HR>

version 0.3.1
- Added refill count (also 0 count, displays red), also OTC and ??? (unknown, red)
- Added text message box for copy/paste to notify person to call for refill.
- Added negative count, displays red
- moved alignment of refill control (renamed from Quick refill control to just refill control)
- renamed "Available Refills" to "Refills Left" for consistency.
<img src="https://github.com/LockMan007/PixelSwirl/blob/main/Python-apps/pills-inventory/medicationstocktracker0.3.1.png">

  <HR>
  
version 0.2.01
added:
- Hourly Auto-Reload Loop: Implemented using self.root.after(3600000, self.auto_refresh) to reload medications.ini once every 60 minutes.
- Header Label Updates: Displays the last refreshed time in 12-hour format with AM/PM (e.g., (Refreshed at 08:00 AM)).
- Interactive Label & Tooltip: Formatted the label to trigger a refresh on <Button-1> and display a temporary tooltip when hovered over.
- Menu Addition: Added a Refresh item to the menubar between File and About.
- 
<HR>

version 0.1
The purpose is to keep track of when you need refills.
Input the Persons Name, Quantity remaining, TOTAL Quantity taken per day.
It will tell you how many days you have left and sort by least days to most days.
You can add multiple people.
When you have 7 days or less, it will tell you that you need to get a refill.

At midnight, it will deduct the daily amount of pills.
I was originally going to try to have morning and night, but then there are 3-4 times a day also, and that complicates things.
I figured it is easier to assume that at midnight that day, assume all pills for the day are now gone,
so if you need to get a refill soon, you know as soon as possible, not finding out right before bed.

The overall purpose of this app, is to know when you need to get refills, so you don't run out.
Some pharmacies have different hours on different days and are closed on some days.
Giving yourself 7 days (1 week) should be enough time.
Being able to see how many days you have left, means you can try to get a refill sooner if you want.

When you do get a refill, you need to click the medication name, add the refill amount and click to update/save it.

**TODO:**

- ~Add version number to app.~
- ~I need to add the ability to Remove and Rename medications/names without having to edit the .ini file or at least have a button to open the .ini file.~
- ~Keep the persons name by default, since most of the time, you will want to add more than 1 medication per person.~
- ~Link to this Github.~
- ~Maybe change the quantity part where you can choose to add or subtract by a set amount, for example "+30 pills"~
- ~Maybe be able to set a default refill amount for each pill, for less clicks and no typing to update.~
- ~Properly add the code in to collapse the top section when it isn't needed.~
- ~Maybe auto-resize the app based on the list. Currently it makes a set size in the code that you can edit, maybe another option to resize and "save size" as an option.~

<img width="569" height="762" alt="image" src="https://github.com/user-attachments/assets/0a0594e4-6e9e-4b29-86c0-f65a9f4dd409" />

