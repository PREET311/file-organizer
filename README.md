# tidy.py — a careful file organizer

`tidy.py` cleans up a messy laptop (Downloads, Desktop, Documents…) and sorts the photos, videos and
documents from your phone into one tidy library. It is one Python file with nothing to install.

**Safety first:** nothing is ever deleted. Every run is planned, shown to you and saved as a report
before anything changes, and nothing moves until you type `YES`. Every move is written to a journal
first, and any run can be undone.

```
Organized/
  Documents/   IDs & Certificates · Money · Work · Study · Resumes & Applications ·
               Travel & Tickets · Manuals & Guides · Other documents (PDFs, Word, Sheets, Slides, Text)
  Photos/2024/2024-03/    Screenshots/2024/    Videos/2024/
  WhatsApp & Chats/  (Images, Videos, Audio, Documents)
  Music/  Voice notes/  E-books/  Archives/  Code/  Design files/
  _Review/  (Duplicates, Installers, Junk, Empty folders, Unknown) - for you to check
```

## Beginner's guide

### 1. Install Python (once)
- **Windows:** go to <https://www.python.org/downloads/>, click the yellow *Download Python* button and
  run the installer. On the first screen **tick "Add python.exe to PATH"**, then click *Install Now*.
- **Mac:** go to <https://www.python.org/downloads/>, download the macOS installer (`.pkg`) and open it.
  Click *Continue* until it's done.
- **Linux:** Python 3 is almost always there already. Check with `python3 --version`.

To check: open a terminal (Windows: press the Windows key, type `cmd`, press Enter. Mac: press
Cmd+Space, type `Terminal`, press Enter) and type `python --version` (Windows) or
`python3 --version` (Mac). You should see `Python 3.9` or newer.

### 2. Save tidy.py
Make a folder just for it, for example `C:\Users\<you>\tidy` on Windows or a folder called `tidy` in
your home folder on a Mac, and save `tidy.py` there. (tidy never touches its own files, but a folder of
its own keeps things neat.) It will create `tidy_config.json` (your settings) and `tidy_data`
(journals, plans and reports) next to itself.

### 3. Open a terminal in that folder
- **Windows:** open the folder in File Explorer, click the address bar, type `cmd` and press Enter.
- **Mac:** in Finder, right-click the folder › *Services* › *New Terminal at Folder*
  (or open Terminal and type `cd ~/tidy`).

### 4. Run the self-test first
```
python tidy.py selftest        (Windows)
python3 tidy.py selftest       (Mac / Linux)
```
It builds a messy test folder in a temporary place, organizes it, undoes it three different ways, and
checks that not a single file was lost or changed. You should see **"15 of 15 checks passed"**.
Your own files are not touched.

### 5. Your first run
```
python tidy.py                 (Windows)
python3 tidy.py                (Mac / Linux)
```
It asks a few questions: which phone you have, which messy folders to tidy (Downloads, Desktop,
Documents, or others), where the organized files should go (press Enter for a folder called
`Organized` in your home folder) and, optionally, your company, course-code and bank names so it can
file documents better. Then you get the menu:

```
 1. Scan & report (changes nothing)       6. Undo a previous run
 2. Organize my files                     7. Re-sort the library
 3. Find duplicates                       8. Watch Downloads
 4. Import from my phone (USB cable)      9. Change settings
 5. Import from a folder                 10. Run the self-test
```

Start with **1**: your browser opens a report showing exactly what would move where and why, what
would be left alone and why, the largest files, and duplicates. When you're happy, choose **2**. It
shows the plan again and waits until you type `YES`. At the end it tells you what happened, e.g.
*"Moved 3,412 items (18.2 GB). 212 duplicates (4.1 GB) are waiting in _Review/Duplicates"*.

Pressing Ctrl+C while files are moving stops safely after the current file.

On a Mac, the first time tidy looks at Desktop, Documents or Downloads, macOS asks whether Terminal may
access them. Click **OK / Allow**.

### 6. Undo
Menu › **6. Undo a previous run** (or `python tidy.py undo`). Pick the run; tidy shows (and saves as a
report) where everything will go back to, and waits for `YES`. Then it moves everything back, checks
that each file really is back, and tells you about anything it couldn't restore and why. If a run was cut off (for example by a power cut), tidy tidies up the unfinished step
the next time it starts, and that run can still be undone.

### 7. The _Review folder
Duplicates, installers, junk (empty files, logs, torrents), empty folders and unknown file types go to
`Organized/_Review/`. Nothing there is deleted. Look through it and delete what you don't need
yourself. `_Review/Duplicates` also has a CSV list showing where each duplicate came from and which
copy was kept.

### 8. Android phone (USB)
1. Download **SDK Platform-Tools** for your computer from the official page:
   <https://developer.android.com/tools/releases/platform-tools>. Unzip it and put the
   `platform-tools` folder **next to tidy.py**.
2. On the phone: *Settings › About phone* › tap **Build number 7 times** until it says you're a
   developer (Samsung: *Settings › About phone › Software information › Build number*).
3. *Settings › System › Developer options* (Samsung: *Settings › Developer options*) › turn on
   **USB debugging**.
4. Plug the phone in with a USB cable, unlock it and tap **Allow** when it asks
   "Allow USB debugging?" (tick "Always allow from this computer").
5. In tidy choose **4. Import from my phone**. It lists the phone's DCIM, Pictures, Download, Documents,
   Movies, Music, Recordings, WhatsApp and Telegram folders and **copies** only the new files (the phone
   is not changed). It checks each copy (size, plus SHA-256 when the phone can compute it), then shows
   the sorting plan and waits for `YES`. It remembers what it imported, so next time only new files are
   copied.
6. Optional: afterwards tidy can **free up space on the phone**. It only deletes files whose copies it
   has double-checked on both sides, and only after you type `DELETE FROM PHONE`. WhatsApp's database
   and apps' private folders are never touched.

No adb? On Linux, if the phone shows up in the file manager, tidy finds it by itself. Otherwise copy
the phone's folders to the laptop (Windows: File Explorer; Mac: OpenMTP or Android File Transfer) and
use **5. Import from a folder**.

### 9. iPhone
iPhones don't appear as a normal drive over USB, so import the photos first:
- **Windows:** unlock the iPhone, plug it in, tap *Trust*. Open the **Photos** app › *Import* ›
  *From a connected device* and import into a new, empty folder (e.g. `Pictures\From iPhone`).
- **Mac:** unlock the iPhone, plug it in, tap *Trust*. Open **Image Capture**, click the iPhone, set
  *Import To* to a new folder (e.g. `Pictures/From iPhone`) and click *Download All*.

Then choose **5. Import from a folder** and paste that folder's path. tidy reads HEIC and MOV dates and
keeps Live Photo pairs (`IMG_1234.HEIC` + `IMG_1234.MOV`) together. Tip: on the iPhone,
*Settings › Photos › Transfer to Mac or PC › Keep Originals* keeps the original HEIC/MOV files.

### 10. Watch mode (optional)
Menu › **8. Watch Downloads** (or `python tidy.py watch`) sorts new files in Downloads every few
minutes, once they haven't changed for 10 minutes. It uses the same rules and journal, so it can be
undone like any other run. tidy prints the exact steps to start it automatically at login (Task
Scheduler on Windows, launchd on Mac, cron or systemd on Linux).

### 11. Good to know
- **"python is not recognized" (Windows):** reinstall Python and tick *Add python.exe to PATH*, or type
  `py tidy.py` instead. If typing `python` opens the Microsoft Store, install from python.org as above.
- **OneDrive / iCloud:** files that are only in the cloud ("online-only") are left alone, so nothing gets
  downloaded by accident. Files tidy moves out of a synced Desktop or Documents folder leave that cloud
  folder but are safe in your library. If you want the library synced too, put it inside your OneDrive
  or iCloud Drive folder.
- **Files that are open** in another app (Windows) are skipped and listed in the report. Close the app
  and run tidy again.
- **What tidy never touches:** system and app folders, apps, hidden files, code projects (folders with
  `.git`, `package.json`, `venv`…), downloads that are still in progress, anything changed in the last
  10 minutes, and online-only cloud files.

## Commands for power users
```
python tidy.py scan       look at everything and open the report (changes nothing)
python tidy.py plan       make a plan and list it (changes nothing)
python tidy.py apply      carry out the latest plan (asks for YES)
python tidy.py undo       undo the latest run, or one you pick (--run ID)
python tidy.py phone      import from a phone
python tidy.py import F   sort folder F (e.g. photos copied from a phone)
python tidy.py dupes      move duplicates to _Review/Duplicates
python tidy.py resort     re-sort the library after changing settings
python tidy.py report     open the latest report
python tidy.py watch      sort new files in Downloads every few minutes (--every N, --yes)
python tidy.py selftest   test everything on a throw-away folder (--keep to look at it)
```

All rules (keywords, file types, skip lists, folder names) live in `tidy_config.json` and can be
edited; menu › *Change settings* › *Open tidy_config.json*.
