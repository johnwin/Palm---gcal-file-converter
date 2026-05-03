# 🌴 gCal to Palm Desktop converion tool 📅
*Because 1996 called, and we absolutely wanted to answer.*

A lightweight, standalone Windows app designed to bridge the gap between your modern Google Calendar and your classic Palm Desktop software (v6.2+). 

🤖 **FULL DISCLOSURE: THIS CODE IS AI-GENERATED!** A human had the brilliant idea for this workflow, and an AI (that's me) wrote the Python code. We spent hours battling ancient 75-character line limits, reverse-engineering 1990s Quoted-Printable `=0D=0A` carriage returns, and building a scrubber to violently eject modern Emojis so Palm Desktop wouldn't crash. Use at your own risk, but enjoy the retro-computing magic!

---

## ✨ What It Does
This tool pulls data from multiple Google Calendars and spits out a perfectly formatted `.VCS` file that Palm Desktop can actually read. 

It has two modes:
* **Full Export:** Grabs everything from the last 3 years (the nuclear option).
* **Delta Sync:** Reads your *previous* sync file to build a memory bank, and only exports *brand new* events to prevent massive duplicate nightmares. 

---

## ⚠️ The "Not-So-Fine" Print (Read This Before Syncing!)
This is a helpful utility, **not a true two-way sync.** Please understand the following limits:

1. **It is a One-Way Street:** Data goes *from* Google *to* Palm Desktop. Nothing you do on your PDA will ever sync back to Google. 
2. **The "Modified Event" Duplicate Trap:** The Delta Sync identifies events using their Start Time and Title. If you log into Google and change the *time* or *name* of an existing meeting, this app will think it is a brand new event. When you import it, Palm Desktop will add the new one, but it won't delete the old one. You will have a duplicate.
3. **The "Unfiled" Panic:** This app forces all imported events into a category called `Personal`. **You MUST manually create a category named "Personal" in Palm Desktop before importing.** If you don't, Palm Desktop will panic and dump your entire life into the "Unfiled" bucket.
4. **Emoji Annihilation:** Palm Desktop is strictly ASCII. Any emojis, smart quotes, or modern unicode symbols in your Google Calendar will be silently stripped out to prevent the 1990s parser from crashing.

---

## 🛠️ How to Use It (No Python Required)

1. **Download the App:** Grab `PalmSync.exe` from the files above and drop it on your PC. 
2. **Get your Secret Link:** Open Google Calendar on the web -> Settings -> Click your calendar -> Scroll to the bottom and copy the **"Secret address in iCal format"**. *(You can do this for as many calendars as you want).*
3. **Run the App:** Double-click `PalmSync.exe`. 
4. **Paste & Sync:** Paste your URLs into the top box. If this is your first time, click **Generate Full Export**. If you are updating, the app will auto-find your last file; just click **Generate Delta Sync**.
5. **Import:** Open Palm Desktop, go to `File > Import`, and select your newly generated file!

*Note: The app will automatically create a tiny `palm_sync_urls.txt` file next to the `.exe`. This is just the app remembering your URLs so you don't have to paste them in tomorrow!*

---

## 💻 For Developers / Tinkering
If you don't trust random `.exe` files (good for you!) or want to modify the code:
1. Clone this repository.
2. Run `python convert.py` to start the GUI.
3. The only external dependency required is `tkinter` (which usually ships with Windows Python). 

## 📄 License
Released under the MIT License. Feel free to fork it, fix it, or port it to Windows 95. Keep vintage tech alive!
