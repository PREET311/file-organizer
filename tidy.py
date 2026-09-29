#!/usr/bin/env python3
"""tidy.py - a careful file organizer for your laptop and your phone.

Sorts Downloads, Desktop and Documents (and photos from a phone) into one tidy library.
Safety first: nothing is ever deleted, every run is planned and shown before anything
changes, every move is written to a journal first, and any run can be undone.

    python tidy.py              the friendly menu (use python3 on Mac/Linux)
    python tidy.py selftest     proves everything works, on a throw-away folder
    python tidy.py help         all commands: scan plan apply undo phone dupes report watch import resort

One file, Python 3.9+, standard library only. Windows, macOS and Linux.
"""
import argparse, base64, csv, ctypes, datetime as dt, errno, fnmatch, hashlib, html, json, os, pathlib, random, re
import shutil, signal, stat, string, struct, subprocess, sys, tempfile, time, unicodedata, webbrowser
from collections import Counter, defaultdict

WIN, MAC = os.name == "nt", sys.platform == "darwin"
HOME = os.path.expanduser("~")
SCRIPT = os.path.abspath(__file__)
HERE = os.path.dirname(SCRIPT)
CONFIG = os.path.join(HERE, "tidy_config.json")
DATA = os.path.join(HERE, "tidy_data")      # journals, plans, reports and phone memory
STOP = [False]                              # Ctrl+C sets this: finish the current file, then stop
IGNORABLE = {".ds_store", "thumbs.db", "desktop.ini", ".localized", "icon\r"}  # OS clutter; stays with its folder
LINK_TAGS = (0xA0000003, 0xA000000C)        # Windows junctions and symbolic links
STAGING = "_Phone import (in progress)"

# ================================================================ 1. CONFIG DEFAULTS (all editable in tidy_config.json)
RULES = {  # Documents sub-folders and the whole words in a file name that point to them
    "IDs & Certificates": "passport, licence, license, national id, aadhaar, pan card, birth certificate, marksheet, "
                          "transcript, degree, certificate",
    "Money": "invoice, receipt, bill, payment, statement, bank, tax, salary, payslip, insurance, policy, loan, emi",
    "Work": "offer letter, contract, agreement, report, proposal, meeting",
    "Study": "assignment, lecture, notes, syllabus, exam, semester, lab, thesis",
    "Resumes & Applications": "resume, cv, cover letter, application",
    "Travel & Tickets": "ticket, boarding pass, itinerary, booking, hotel, visa, flight, train, bus",
    "Manuals & Guides": "manual, guide, instructions, warranty",
}
TYPES = {  # file extensions by kind; the last six are the "Other documents" type folders
    "photo": "jpg jpeg jpe jfif png gif bmp tif tiff webp heic heif avif dng cr2 cr3 nef arw orf rw2 raf srw pef",
    "video": "mp4 mov m4v avi mkv wmv flv webm 3gp 3g2 mts m2ts mpg mpeg vob ogv",
    "audio": "mp3 m4a aac flac wav ogg oga opus wma aiff aif amr 3ga mid midi",
    "ebook": "epub mobi azw azw3 djvu fb2 cbz cbr ibooks",
    "archive": "zip rar 7z tar gz tgz bz2 xz zst iso cab",
    "code": "py ipynb js ts jsx tsx java c h cpp hpp cs go rs rb php swift kt sql sh bat ps1 r lua pl json xml yml "
            "yaml toml css scss",
    "design": "psd ai sketch fig xd indd eps svg cdr afdesign afphoto xcf kra procreate blend dwg dxf ttf otf woff woff2",
    "installer": "exe msi dmg pkg apk xapk apks appx appxbundle msix msixbundle deb rpm appimage",
    "junk": "log dmp bak old crash torrent",
    "sidecar": "aae xmp",
    "PDFs": "pdf", "Word": "doc docx docm odt rtf pages wpd wps", "Sheets": "xls xlsx xlsm xlsb ods csv tsv numbers",
    "Slides": "ppt pptx pptm pps ppsx odp key", "Text": "txt md tex ics vcf eml msg xps oxps one",
    "Web pages": "html htm mhtml mht webarchive",
}
DOC_TYPES = ("PDFs", "Word", "Sheets", "Slides", "Text", "Web pages")
KIND_HOME = {"audio": "Music", "ebook": "E-books", "archive": "Archives", "code": "Code", "design": "Design files"}


def defaults():
    return {
        "_help": "Settings for tidy.py. Lists are plain words, folders are full paths. Delete this file to run the "
                 "setup again. Keyword rules match whole words in file names; my_keywords count double.",
        "phone": "", "library": "", "sources": [], "tidy_names": False, "min_age_minutes": 10,
        "watch_every_minutes": 5, "adb_path": "",
        "my_keywords": {"Work": [], "Study": [], "Money": []},
        "rules": {k: [w.strip() for w in v.split(",")] for k, v in RULES.items()},
        "types": {k: v.split() for k, v in TYPES.items()},
        "unfinished_downloads": "crdownload part partial download tmp opdownload !ut !qb aria2 filepart dtapart "
                                "crswap".split(),
        "shortcuts": "lnk url webloc desktop appref-ms website".split(),
        "app_data_types": "db sqlite sqlite3 sav dat ini cfg plist lock pst ost vmdk vhd vhdx vdi nvram".split(),
        "project_markers": ".git .hg .svn package.json node_modules venv .venv pyvenv.cfg pyproject.toml .idea "
                           ".vscode pom.xml build.gradle go.mod Cargo.toml Gemfile composer.json CMakeLists.txt "
                           "pubspec.yaml *.sln *.csproj *.xcodeproj *.xcworkspace".split(),
        "packages": "app photoslibrary photolibrary aplibrary musiclibrary tvlibrary imovielibrary fcpbundle logicx "
                    "band bundle framework plugin kext lrdata lrlibrary rtfd pages numbers key download".split(),
        "skip_folders": ["appdata", "application data", "library", "program files*", "programdata", "windows",
                         "$recycle.bin", "system volume information", "my games", "saved games", "outlook files",
                         "onenote notebooks", "custom office templates", "windowspowershell", "powershell", "zoom",
                         "adobe", "microsoft user data", "tencent files", "wechat files", "wxwork", "visual studio*",
                         "iisexpress", "my web sites", "sql server management studio*", "rockstar games",
                         "electronic arts", "ea games", "ubisoft", "battle.net", "blizzard*", "riot games",
                         "paradox interactive", "klei", "roblox", "arduino", "processing", "matlab",
                         "virtual machines*", "parallels", "snagit", "camtasia*", "audacity", "image-line",
                         "native instruments", "ableton", "fax", "sound recordings", "pictures", "music", "videos",
                         "movies", "onedrive*", "dropbox*", "google drive*", "icloud drive*", "creative cloud files*",
                         "applications", "public", "templates"],
        "generic_folders": ["new folder", "untitled", "untitled folder", "folder", "new", "misc", "stuff", "temp",
                            "tmp", "downloads", "download", "desktop", "documents", "files", "neuer ordner",
                            "nouveau dossier", "nueva carpeta", "nuova cartella", "nieuwe map", "nova pasta",
                            "新建文件夹", "新しいフォルダー", "새 폴더"],
    }


# ================================================================ 2. CONSOLE (colours, questions, progress)
def _console():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")  # an odd file name must never crash printing
        except Exception:
            pass
    if not WIN:
        return True
    try:  # switch on colours in the Windows 10+ terminal
        k = ctypes.windll.kernel32
        h, m = k.GetStdHandle(-11), ctypes.c_ulong()
        return bool(k.GetConsoleMode(h, ctypes.byref(m)) and k.SetConsoleMode(h, m.value | 4))
    except Exception:
        return False


TTY = sys.stdout.isatty()
COLOR = _console() and TTY and "NO_COLOR" not in os.environ


def paint(s, c): return f"\033[{c}m{s}\033[0m" if COLOR else str(s)
def say(s="", c=""): print(paint(s, c) if c else s, flush=True)
def good(s): say(s, "32")
def warn(s): say(s, "33")
def bad(s): say(s, "31")
def title(s): say("\n" + s, "1;36")


def ask(q, default=""):
    try:
        a = input(paint(q, "1") + (f" [{default}]" if default else "") + ": ").strip()
    except EOFError:
        a = ""
    return a or default


def yes_no(q, default="n"): return ask(q + (" (Y/n)" if default == "y" else " (y/N)"), default).lower()[:1] == "y"


def confirm(what, word="YES"):
    say(what)
    return ask(f"Type {word} to go ahead, or press Enter to cancel") == word


def pick(q, options, back="Back"):
    title(q)
    for i, o in enumerate(options, 1):
        say(f"  {i:>2}. {o}")
    if back:
        say(f"   0. {back}")
    while True:
        a = ask("Your choice")
        if a == "0" and back:
            return None
        if a.isdigit() and 1 <= int(a) <= len(options):
            return int(a) - 1
        warn("Please type one of the numbers shown.")


def size(n):
    n = float(n)
    for u in ("bytes", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {u}" if u == "bytes" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def count(n, word): return f"{n:,} {word}" + ("" if n == 1 else "s")
def span(s): s = int(s); return f"{s // 3600}h {s // 60 % 60}m" if s >= 3600 else f"{s // 60}m {s % 60}s"
def stamp(): return time.strftime("%Y-%m-%d %H:%M:%S")


class Progress:
    """One line that updates in place: counts, sizes and time left."""
    def __init__(s, label, total=0, nbytes=0, quiet=False):
        s.label, s.total, s.tb, s.t0, s.shown, s.n, s.b, s.quiet = label, total, nbytes, time.time(), 0, 0, 0, quiet

    def step(s, n=1, b=0):
        s.n, s.b, t = s.n + n, s.b + b, time.time()
        if s.quiet or not TTY or t - s.shown < 0.25:
            return
        s.shown, el, msg = t, t - s.t0, f"{s.label} {s.n:,}"
        if s.total:
            f = (s.n / s.total + (s.b / s.tb if s.tb else s.n / s.total)) / 2
            msg += f" of {s.total:,} ({f:.0%})" + (f" - {size(s.b)} of {size(s.tb)}" if s.tb else "")
            if el > 3 and f > 0.01:
                msg += f" - about {span(el / f - el)} left"
        else:
            msg += f" - {span(el)}"
        w = shutil.get_terminal_size((80, 20)).columns - 1
        sys.stdout.write("\r" + msg[:w].ljust(w))
        sys.stdout.flush()

    def end(s):
        if s.shown:
            sys.stdout.write("\r" + " " * (shutil.get_terminal_size((80, 20)).columns - 1) + "\r")
            sys.stdout.flush()


class Stoppable:
    """While active, Ctrl+C means 'stop safely after the current file' instead of 'quit right now'."""
    def __enter__(s):
        STOP[0] = False
        s.old = signal.signal(signal.SIGINT, s.hit)
        return s

    def hit(s, *_):
        if not STOP[0]:
            warn("\nStopping safely after the current file...")
        STOP[0] = True

    def __exit__(s, *_):
        signal.signal(signal.SIGINT, s.old)
        STOP[0] = False


# ================================================================ 3. SAFE FILE OPERATIONS
def L(p):
    """Windows: the \\\\?\\ form reaches very long paths (over 260 characters)."""
    if not WIN or p.startswith("\\\\?\\"):
        return p
    p = os.path.abspath(p)
    return "\\\\?\\UNC\\" + p[2:] if p.startswith("\\\\") else "\\\\?\\" + p


def key(p):
    p = os.path.normcase(os.path.abspath(p))
    return p.lower() if MAC else p


def inside(p, root):
    p, r = key(p), key(root)
    return p == r or p.startswith(r.rstrip(os.sep) + os.sep)


def exists(p): return os.path.lexists(L(p))
def isdir(p): return os.path.isdir(L(p))
def lstat(p): return os.stat(L(p), follow_symlinks=False)
def ext_of(name): return os.path.splitext(name)[1][1:].lower()


def scandir(p):
    with os.scandir(L(p)) as it:
        return sorted(it, key=lambda e: e.name.lower())


def tree_of(d):
    """Every sub-folder and file below d (links are not followed)."""
    dirs, files, stack = [d], [], [d]
    while stack:
        cur = stack.pop()
        for e in scandir(cur):
            p = os.path.join(cur, e.name)
            if e.is_dir(follow_symlinks=False):
                dirs.append(p)
                stack.append(p)
            else:
                files.append(p)
    return dirs, files


def is_hidden(name, st):
    return name.startswith(".") or bool(getattr(st, "st_file_attributes", 0) & 6) \
        or bool(getattr(st, "st_flags", 0) & 0x8000)  # Windows hidden/system, macOS UF_HIDDEN


def is_link(e, st): return e.is_symlink() or getattr(st, "st_reparse_tag", 0) in LINK_TAGS


def is_cloud(st):
    """Online-only placeholders (OneDrive/iCloud/Dropbox): reading them would start a download."""
    return bool(getattr(st, "st_file_attributes", 0) & 0x441000) or bool(getattr(st, "st_flags", 0) & 0x40000000)


def unique(p, taken=(), folder=False):
    """'name (2).ext', 'name (3).ext'...: the first name that is free on disk and not already planned."""
    b, e = (p, "") if folder else os.path.splitext(p)
    k = 1
    while exists(p) or key(p) in taken:
        k += 1
        p = f"{b} ({k}){e}"
    return p


class Skip(Exception):
    """A file we leave alone; the message says why in plain words."""


def reason(e):
    if isinstance(e, Skip):
        return str(e)
    if isinstance(e, FileNotFoundError):
        return "it was moved or deleted by something else meanwhile"
    if isinstance(e, FileExistsError):
        return "something with that name appeared at the destination meanwhile"
    if isinstance(e, PermissionError) or getattr(e, "winerror", 0) in (5, 32, 33):
        return "open in another app, or no permission (close it and run tidy again)"
    if getattr(e, "errno", 0) == errno.ENOSPC:
        return "the destination drive is full"
    return f"{type(e).__name__}: {e}"


def _noreplace():
    """The OS call that renames but refuses to replace an existing file (Linux renameat2, macOS renamex_np)."""
    if WIN:
        return None  # os.rename on Windows already refuses to overwrite
    try:
        c = ctypes.CDLL(None, use_errno=True)
        if MAC:
            f = c.renamex_np
            return lambda a, b: f(os.fsencode(a), os.fsencode(b), 4)
        f = c.renameat2
        return lambda a, b: f(-100, os.fsencode(a), -100, os.fsencode(b), 1)
    except Exception:
        return None


NOREPLACE = _noreplace()


def rename(a, b):
    """Rename a to b, never replacing anything that is already at b."""
    if NOREPLACE:
        if NOREPLACE(a, b) == 0:
            return
        e = ctypes.get_errno()
        if e not in (errno.EINVAL, errno.ENOSYS, errno.ENOTSUP, getattr(errno, "EOPNOTSUPP", 95)):
            raise OSError(e, os.strerror(e), a)
    if exists(b):
        raise FileExistsError(errno.EEXIST, "already exists", b)
    os.rename(L(a), L(b))


def mkdirs(d, J=None):
    """Create missing folders one level at a time; each is journaled so undo can remove it again."""
    todo = []
    while not isdir(d):
        todo.append(d)
        up = os.path.dirname(d)
        if up == d:
            break
        d = up
    for x in reversed(todo):
        os.mkdir(L(x))
        if J:
            J.w(t="mkdir", path=x)


def remove(p):
    """Only ever used for an original after a verified copy, or for tidy's own temporary copies."""
    try:
        os.remove(L(p))
    except PermissionError:
        if not WIN:
            raise
        os.chmod(L(p), stat.S_IWRITE)  # a read-only file on Windows
        os.remove(L(p))


def sha(p):
    h = hashlib.sha256()
    with open(L(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def quick(p, n):
    """Cheap first look for duplicates: the first and last 64 KB (the whole file if it is 128 KB or less)."""
    with open(L(p), "rb") as f:
        if n <= 131072:
            return hashlib.sha256(f.read()).hexdigest()
        b = f.read(65536)
        f.seek(-65536, 2)
        return hashlib.sha256(b + f.read()).hexdigest()


def same_content(a, b):
    try:
        return lstat(a).st_size == lstat(b).st_size and sha(a) == sha(b)
    except OSError:
        return False


def copy(src, dst, st):
    """Copy to a temporary name, check size + SHA-256 against the original, then rename into place.
    Keeps the modified date. A half-written file never appears under the real name."""
    tmp = dst + ".tidy-part"
    if exists(tmp):
        remove(tmp)  # a leftover of an interrupted run: always tidy's own partial copy
    h = hashlib.sha256()
    try:
        with open(L(src), "rb") as f, open(L(tmp), "xb") as g:
            for b in iter(lambda: f.read(1 << 20), b""):
                if STOP[0]:
                    raise Skip("stopped before this one finished copying")
                h.update(b)
                g.write(b)
            g.flush()
            os.fsync(g.fileno())
        os.utime(L(tmp), ns=(st.st_atime_ns, st.st_mtime_ns))
        now = lstat(src)
        if (now.st_size, now.st_mtime_ns) != (st.st_size, st.st_mtime_ns):
            raise Skip("it changed while it was being copied")
        if lstat(tmp).st_size != st.st_size or sha(tmp) != h.hexdigest():
            raise Skip("the copy didn't match the original (drive or cable problem?)")
        rename(tmp, dst)
    except BaseException:
        if exists(tmp):
            remove(tmp)
        raise
    try:
        os.chmod(L(dst), stat.S_IMODE(st.st_mode))
    except OSError:
        pass
    return h.hexdigest()


def same_drive(a, b):
    while not exists(b):
        up = os.path.dirname(b)
        if up == b:
            return False
        b = up
    return lstat(a).st_dev == os.stat(L(b)).st_dev


def transfer(src, dst, how, st):
    """One move. how='rename' (same drive) or 'copy' (other drive: copy, verify, then remove the original)."""
    if how == "rename":
        return rename(src, dst)
    h = copy(src, dst, st)
    try:
        remove(src)
    except OSError as e:  # e.g. open in another app: take our copy back and leave the original alone
        remove(dst)
        raise Skip(f"copied, but the original couldn't be removed ({reason(e)}), so it was left as it was")
    return h


class Journal:
    """One JSON-lines file per run. Each move is written *before* it happens ('begin', flushed to disk)
    and again after ('done' or 'fail'), so undo knows exactly what happened, even after a crash."""
    def __init__(s, kind, **info):
        os.makedirs(os.path.join(DATA, "runs"), exist_ok=True)
        s.id = time.strftime("%Y%m%d-%H%M%S-") + f"{int(time.time() * 1000) % 1000:03d}" + \
            "".join(random.choices(string.ascii_lowercase, k=2))
        s.path = os.path.join(DATA, "runs", s.id + ".jsonl")
        s.f, s.n = open(s.path, "a", encoding="utf-8"), 0
        s.w(t="run", id=s.id, kind=kind, started=stamp(), **info)
        s.sync()

    def w(s, **r):
        s.f.write(json.dumps(r, ensure_ascii=False) + "\n")
        s.f.flush()

    def sync(s): os.fsync(s.f.fileno())

    def begin(s, **r):
        s.n += 1
        s.w(t="begin", n=s.n, **r)
        return s.n

    def close(s, **r):
        s.w(t="end", ended=stamp(), **r)
        s.sync()
        s.f.close()


class Busy(Exception):
    pass


def pid_alive(pid):
    if pid <= 0:
        return False
    if WIN:
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)
        if not h:
            return False
        code = ctypes.c_ulong()
        k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return code.value == 259
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        pass
    return True


class Lock:
    """Only one tidy may change files at a time (for example watch mode and the menu)."""
    def __init__(s, ask_user=True):
        s.ask, s.p = ask_user, os.path.join(DATA, "tidy.lock")

    def __enter__(s):
        os.makedirs(DATA, exist_ok=True)
        for attempt in (1, 2):
            try:
                fd = os.open(s.p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                break
            except FileExistsError:
                try:
                    with open(s.p) as f:
                        pid = int(f.read().strip() or 0)
                except (OSError, ValueError):
                    pid = 0
                if attempt == 2 or pid_alive(pid) and not (s.ask and confirm(
                        f"Another tidy (process {pid}) seems to be busy. Only continue if you're sure it isn't.")):
                    raise Busy()
                os.remove(s.p)
        recover()
        return s

    def __exit__(s, *_):
        try:
            os.remove(s.p)
        except OSError:
            pass


# ================================================================ 4. SETTINGS FILE AND FIRST-RUN SETUP
def load_config():
    if not os.path.exists(CONFIG):
        return None
    try:
        with open(CONFIG, encoding="utf-8") as f:
            user = json.load(f)
        if not isinstance(user, dict):
            raise ValueError("it doesn't contain settings")
    except (OSError, ValueError) as e:
        keep = unique(CONFIG[:-5] + time.strftime("-broken-%Y%m%d-%H%M%S.json"))
        bad(f"tidy_config.json couldn't be read ({e}).")
        rename(CONFIG, keep)
        warn(f"I kept it as {os.path.basename(keep)}; let's set things up again.")
        return None
    cfg = defaults()
    cfg.update(user)
    return cfg


def save_config(cfg):
    with open(CONFIG + ".tmp", "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(CONFIG + ".tmp", CONFIG)


def known_folders():
    """Where Desktop, Documents and Downloads really are (on Windows they may live inside OneDrive)."""
    f = {n: os.path.join(HOME, n) for n in ("Desktop", "Documents", "Downloads")}
    try:
        if WIN:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
            for n, v in (("Desktop", "Desktop"), ("Documents", "Personal"),
                         ("Downloads", "{374DE290-123F-4565-9164-39C4925E467B}")):
                try:
                    f[n] = os.path.expandvars(winreg.QueryValueEx(k, v)[0])
                except OSError:
                    pass
        elif not MAC:
            with open(os.path.join(HOME, ".config", "user-dirs.dirs"), encoding="utf-8") as fh:
                for line in fh:
                    m = re.match(r'XDG_(DESKTOP|DOCUMENTS|DOWNLOAD)_DIR="(.+)"', line)
                    if m:
                        f[{"DESKTOP": "Desktop", "DOCUMENTS": "Documents", "DOWNLOAD": "Downloads"}[m[1]]] = \
                            m[2].replace("$HOME", HOME)
    except (OSError, ImportError):
        pass
    return f


def is_system(p):
    roots = ["/System", "/Library", "/usr", "/bin", "/sbin", "/etc", "/opt", "/proc", "/sys", "/dev", "/boot", "/lib",
             "/snap", "/Applications", os.path.join(HOME, "Library"), os.path.join(HOME, "AppData")]
    if WIN:
        roots += [os.environ.get(v, "") for v in ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramData")]
    return any(r and inside(p, r) for r in roots)


def too_broad(p):
    return key(p) == key(HOME) or os.path.dirname(os.path.abspath(p)) == os.path.abspath(p)


def bad_folder(p):
    """Why a folder can't be tidied, or '' if it's fine."""
    if not isdir(p):
        return "that folder doesn't exist"
    if too_broad(p):
        return "that's too broad - pick specific folders such as Downloads"
    return "that's a system or app folder" if is_system(p) else ""


def bad_library(lib, sources):
    if exists(lib) and not isdir(lib):
        return "that's a file, not a folder"
    if not isdir(os.path.dirname(os.path.abspath(lib))):
        return "the folder it would go in doesn't exist"
    if too_broad(lib) or is_system(lib):
        return "that's a system folder or too broad"
    if any(inside(s["path"], lib) for s in sources):
        return "one of your messy folders is inside it"
    return ""


def clean_path(p): return os.path.abspath(os.path.expanduser(p.strip().strip('"\'')))


def setup(cfg=None):
    cfg = cfg or defaults()
    title("Welcome to tidy! A few quick questions (about a minute). Nothing gets moved yet.")
    say(f"You're on {'Windows' if WIN else 'a Mac' if MAC else 'Linux'}.")
    i = pick("Which phone do you have?", ["Android", "iPhone", "No phone / skip"], back=None)
    cfg["phone"] = ["Android", "iPhone", "none"][i]
    say("\nWhich messy folders should tidy look after? It sorts only the loose files in Downloads and Desktop,")
    say("and in Documents it also keeps named folders (like 'Tax 2023') together.")
    cfg["sources"], kf = [], known_folders()
    for n in ("Downloads", "Desktop", "Documents"):
        if isdir(kf[n]) and yes_no(f"  Tidy {n} ({kf[n]})?", "y"):
            cfg["sources"].append({"path": kf[n], "subfolders": n == "Documents"})
    add_folders(cfg)
    while True:
        lib = clean_path(ask("\nWhere should the organized files go?", cfg["library"] or os.path.join(HOME, "Organized")))
        why = bad_library(lib, cfg["sources"])
        if not why:
            break
        warn(f"  Can't use that: {why}.")
    cfg["library"] = lib
    say("\nWhat are your documents mostly about? Names help tidy file them (press Enter to skip any).")
    for cat, q in (("Work", "Company or client names"), ("Study", "Course codes or subjects (e.g. CS101, MA2003)"),
                   ("Money", "Your bank, card or insurance names")):
        words = [w.strip() for w in ask(f"  {q}, separated by commas").split(",") if w.strip()]
        cfg["my_keywords"][cat] = sorted(set(cfg["my_keywords"].get(cat, []) + words))
    save_config(cfg)
    good(f"\nSaved your settings in {CONFIG}")
    say("You can change them any time with 'Change settings' in the menu.")
    return cfg


def add_folders(cfg):
    while True:
        p = ask("Another messy folder? Paste its path, or press Enter to skip")
        if not p:
            return
        p = clean_path(p)
        why = bad_folder(p) or ("it's your library" if cfg["library"] and inside(p, cfg["library"]) else "")
        if why:
            warn(f"  Can't use that: {why}.")
        else:
            cfg["sources"].append({"path": p, "subfolders": yes_no("  Also sort what's inside its sub-folders?")})


def open_path(p):
    try:
        if WIN:
            os.startfile(p)
        elif MAC:
            subprocess.run(["open", p])
        else:
            subprocess.run(["xdg-open", p], stderr=subprocess.DEVNULL)
    except Exception:
        say(f"Please open it yourself: {p}")


def settings(cfg):
    while True:
        src = ", ".join(os.path.basename(s["path"].rstrip("\\/")) + (" (+ folders)" if s["subfolders"] else "")
                        for s in cfg["sources"]) or "none"
        kw = "; ".join(f"{k}: {', '.join(v)}" for k, v in cfg["my_keywords"].items() if v) or "none"
        i = pick("Change settings", [
            f"Messy folders: {src}", f"Library: {cfg['library']}", f"Phone: {cfg['phone'] or 'not set'}",
            f"My keywords: {kw}", f"Tidy names: {'ON' if cfg['tidy_names'] else 'off'} "
                                  "(rename camera photos to their date, drop 'Copy of' and ' (1)')",
            "Run the whole setup again", "Open tidy_config.json to edit rules and skip lists"])
        if i is None:
            return cfg
        if i == 0:
            edit_sources(cfg)
        elif i == 1:
            lib = clean_path(ask("New library folder", cfg["library"]))
            why = bad_library(lib, cfg["sources"])
            if why:
                warn(f"Can't use that: {why}.")
            else:
                cfg["library"] = lib
                say("New runs go there. Earlier runs can still be undone; files already sorted stay where they are.")
        elif i == 2:
            cfg["phone"] = ["Android", "iPhone", "none"][pick("Which phone?", ["Android", "iPhone", "None"], None)]
        elif i == 3:
            for cat in cfg["my_keywords"]:
                v = ask(f"{cat} words, separated by commas", ", ".join(cfg["my_keywords"][cat]))
                cfg["my_keywords"][cat] = [w.strip() for w in v.split(",") if w.strip()]
        elif i == 4:
            cfg["tidy_names"] = not cfg["tidy_names"]
        elif i == 5:
            cfg = setup(cfg)
        else:
            save_config(cfg)
            open_path(CONFIG)
            ask("Edit and save the file, then press Enter here")
            cfg = load_config() or setup()
        save_config(cfg)


def edit_sources(cfg):
    while True:
        opts = [f"{s['path']}  (sort inside folders: {'ON' if s['subfolders'] else 'off'})" for s in cfg["sources"]]
        i = pick("Messy folders - choose one to change it", opts + ["Add a folder"])
        if i is None:
            return
        if i == len(opts):
            add_folders(cfg)
            continue
        s = cfg["sources"][i]
        j = pick(s["path"], [f"Turn 'sort inside folders' {'off' if s['subfolders'] else 'ON'}",
                             "Stop tidying this folder"])
        if j == 0:
            s["subfolders"] = not s["subfolders"]
        elif j == 1:
            cfg["sources"].pop(i)


# ================================================================ 5. RULES: TYPES, TOPICS, DATES
def norm(s):
    """'BankStatement_March2024' -> ' bank statement march 2024 ' (accents dropped, words split)."""
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[^\W\d_])(?=\d)|(?<=\d)(?=[^\W\d_])", " ", s)
    return " " + " ".join(re.findall(r"[^\W_]+", s.lower())) + " "


class Rules:
    """The settings turned into quick lookups."""
    def __init__(s, cfg):
        s.cfg, s.kind, s.words = cfg, {}, []
        for k, v in cfg["types"].items():
            for x in v:
                s.kind.setdefault(x.lower().lstrip("."), k)
        for pts, table in ((1, cfg["rules"]), (2, cfg["my_keywords"])):
            for cat, ws in table.items():
                for w in ws:
                    t = norm(w).split()
                    if t:  # whole words only, plural allowed: "bill" matches "bills" but not "billboard"
                        rx = re.compile(r"(?<= )" + " ?".join(map(re.escape, t)) + r"(?:e?s)?(?= )")
                        s.words.append((cat, rx, pts * len(t), w))
        s.age = float(cfg["min_age_minutes"]) * 60
        s.unfinished, s.shortcuts, s.appdata, s.packages = (set(cfg[k]) for k in (
            "unfinished_downloads", "shortcuts", "app_data_types", "packages"))
        s.markers = {m.lower() for m in cfg["project_markers"] if not m.startswith("*")}
        s.marker_ends = tuple(m[1:].lower() for m in cfg["project_markers"] if m.startswith("*"))
        s.skipdirs = [x.lower() for x in cfg["skip_folders"]]
        s.generic = {x.lower() for x in cfg["generic_folders"]}

    def topic(s, name):
        """Best Documents sub-folder for a name: (category, matched words) or (None, why not)."""
        n, score, hits = norm(name), Counter(), defaultdict(list)
        for cat, rx, pts, w in s.words:
            if rx.search(n):
                score[cat] += pts
                hits[cat].append(f'"{w}"')
        if not score:
            return None, "no topic words in its name"
        best = score.most_common(2)
        if len(best) > 1 and best[0][1] == best[1][1]:
            return None, f"its name fits {best[0][0]} and {best[1][0]} equally"
        return best[0][0], ", ".join(hits[best[0][0]])

    def is_generic(s, name):
        return re.sub(r"[\s_-]*(\(\d+\)|\d+)$", "", name.lower()).strip() in s.generic

    def project(s, d):
        """The file or folder that marks d as a code project, or None."""
        try:
            for e in scandir(d):
                n = e.name.lower()
                if n in s.markers or n.endswith(s.marker_ends):
                    return e.name
        except OSError:
            pass
        return None

    def recent(s, st, now): return -86400 < now - st.st_mtime < s.age


DATE_RX = re.compile(r"(?<!\d)(199\d|20\d\d)[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?:(?:[ _T-]|[ _]at[ _])"
                     r"([01]?\d|2[0-3])[.:_-]?([0-5]\d)[.:_-]?([0-5]\d)(?:\s?([AaPp])[Mm])?)?")
MS_RX = re.compile(r"(?<!\d)(1[3-7]\d{11})(?!\d)")  # a 13-digit millisecond timestamp, e.g. FB_IMG_1710238272000
CAMERA_RX = re.compile(r"(?i)^(img|vid|dsc[nf]?|pxl|mvimg|pano|burst|gopr|dji|mov|p\d{3}|20\d{6})[_-]?\d")
SCREEN_RX = re.compile(r"(?i)^(screenshot|screen shot|screen_shot|scr_|capture d.{1,2}[ée]cran|bildschirmfoto|"
                       r"schermafbeelding|captura de pantalla|スクリーンショット|截屏|屏幕截图)")
WA_RX = re.compile(r"(?i)^((img|vid|aud|ptt|doc|stk)-\d{8}-wa\d+|whatsapp (image|video|audio|ptt|document) )")
TG_RX = re.compile(r"(?i)^(photo|video|file)_\d{4}-\d\d-\d\d_\d\d-\d\d-\d\d")
VOICE_RX = re.compile(r"(?i)^(ptt-|voice|recording|new recording|rec[_-]|call|memo|audio recording|sound recording)")


def real_date(*a):
    """A datetime, or None if impossible (before 1990 or in the future)."""
    try:
        t = dt.datetime(*a)
    except (ValueError, OverflowError):
        return None
    return t if dt.datetime(1990, 1, 1) <= t <= dt.datetime.now() + dt.timedelta(days=1) else None


def ts_date(ts):
    try:
        return real_date(*dt.datetime.fromtimestamp(ts).timetuple()[:6])
    except (OverflowError, OSError, ValueError):
        return None


def name_date(name):
    """Dates in names like IMG_20240312_101112, 'Screenshot 2024-03-12 at 10.11.12', VID-20240312-WA0001."""
    m = DATE_RX.search(name)
    if m:
        y, mo, d, h, mi, se, ap = m.groups()
        h = int(h or 0)
        if ap:
            h = h % 12 + (12 if ap.lower() == "p" else 0)
        t = real_date(int(y), int(mo), int(d), h, int(mi or 0), int(se or 0))
        if t:
            return t, m.group(4) is not None
    m = MS_RX.search(name)
    t = m and ts_date(int(m[1]) / 1000)
    return (t, True) if t else (None, False)


def _tiff(t):
    """DateTimeOriginal (or DateTimeDigitized / DateTime) from an EXIF TIFF block."""
    e = "<" if t[:2] == b"II" else ">"
    def u(f, o): return struct.unpack(e + f, t[o:o + struct.calcsize(f)])[0]
    def ifd(o): return {u("H", o + 2 + 12 * i): o + 2 + 12 * i for i in range(u("H", o))}
    def text(p):
        n = u("I", p + 4)
        o = u("I", p + 8) if n > 4 else p + 8
        return t[o:o + n].split(b"\0")[0].decode("ascii", "replace")
    top = ifd(u("I", 4))
    sub = ifd(u("I", top[0x8769] + 8)) if 0x8769 in top else {}
    for tags, tag in ((sub, 0x9003), (sub, 0x9004), (top, 0x0132)):
        m = tag in tags and re.match(r"(\d{4}):(\d\d):(\d\d) (\d\d):(\d\d):(\d\d)", text(tags[tag]))
        d = m and real_date(*map(int, m.groups()))
        if d:
            return d
    return None


def _heif_exif(f):
    """The EXIF block inside a HEIC/HEIF file (found through its 'meta', 'iinf' and 'iloc' boxes)."""
    b = f.read(1 << 20)
    def boxes(i, end):
        while i + 8 <= end:
            n, typ = struct.unpack(">I4s", b[i:i + 8])
            h = 8
            if n == 1:
                n, h = struct.unpack(">Q", b[i + 8:i + 16])[0], 16
            n = n or end - i
            if n < h:
                return
            yield typ, i + h, min(i + n, end)
            i += n
    def num(i, k): return int.from_bytes(b[i:i + k], "big")
    meta = next(((a, z) for t, a, z in boxes(0, len(b)) if t == b"meta"), None)
    exif, loc = None, {}
    for t, a, z in boxes(meta[0] + 4, meta[1]) if meta else ():
        v = b[a]
        if t == b"iinf":
            for t2, a2, _ in boxes(a + (6 if v == 0 else 8), z):
                k = 2 if b[a2] == 2 else 4
                if t2 == b"infe" and b[a2] >= 2 and b[a2 + 6 + k:a2 + 10 + k] == b"Exif":
                    exif = num(a2 + 4, k)
        elif t == b"iloc":
            p, k = a + 6, 2 if v < 2 else 4
            osz, lsz, bsz, isz = b[a + 4] >> 4, b[a + 4] & 15, b[a + 5] >> 4, b[a + 5] & 15
            items, p = num(p, k), p + k
            for _ in range(items):
                iid = num(p, k)
                p += k + (2 if v else 0) + 2
                base, ext_count = num(p, bsz), num(p + bsz, 2)
                p += bsz + 2
                for j in range(ext_count):
                    p += isz if v else 0
                    if j == 0:
                        loc[iid] = (base + num(p, osz), num(p + osz, lsz))
                    p += osz + lsz
    if exif not in loc:
        return None
    f.seek(loc[exif][0])
    x = f.read(min(loc[exif][1], 1 << 16))
    return x[4 + int.from_bytes(x[:4], "big"):]


def exif_date(path, ext):
    """When a JPEG or HEIC photo was taken, read with a small built-in parser (no Pillow needed)."""
    with open(L(path), "rb") as f:
        if ext in ("heic", "heif"):
            t = _heif_exif(f)
            return _tiff(t) if t else None
        if f.read(2) != b"\xff\xd8":
            return None
        while True:
            h = f.read(4)
            if len(h) < 4 or h[0] != 0xFF or h[1] in (0xD9, 0xDA):
                return None
            n = struct.unpack(">H", h[2:])[0] - 2
            if h[1] == 0xE1:
                b = f.read(n)
                if b[:6] == b"Exif\0\0":
                    return _tiff(b[6:])
            else:
                f.seek(n, 1)


def movie_date(path):
    """Recording time from an MP4/MOV header ('mvhd' box)."""
    with open(L(path), "rb") as f:
        end, i = os.fstat(f.fileno()).st_size, 0
        while i + 8 <= end:
            f.seek(i)
            n, t = struct.unpack(">I4s", f.read(8))
            h = 8
            if n == 1:
                n, h = struct.unpack(">Q", f.read(8))[0], 16
            n = n or end - i
            if n < h:
                return None
            if t == b"moov":
                b = f.read(min(n - h, 1 << 16))
                j = b.find(b"mvhd")
                if j < 4:
                    return None
                secs = struct.unpack(">Q", b[j + 8:j + 16])[0] if b[j + 4] else struct.unpack(">I", b[j + 8:j + 12])[0]
                return ts_date(secs - 2082844800)  # seconds since 1904
            i += n
    return None


def media_date(path, name, ext, st):
    """(date, where it came from, whether it includes the time) for a photo or video."""
    try:
        d = exif_date(path, ext) if ext in ("jpg", "jpeg", "jpe", "jfif", "heic", "heif") else None
    except Exception:  # a damaged photo simply has no EXIF date
        d = None
    if d:
        return d, "photo info (EXIF)", True
    d, timed = name_date(name)
    if d:
        return d, "its name", timed
    try:
        d = movie_date(path) if ext in ("mp4", "mov", "m4v", "3gp") else None
    except Exception:
        d = None
    if d:
        return d, "video info", True
    return ts_date(st.st_mtime), "its modified date", False


def chat_app(name, rel):
    low = rel.lower()
    if WA_RX.match(name) or "whatsapp" in low:
        return "WhatsApp"
    if TG_RX.match(name) or "telegram" in low:
        return "Telegram"
    if name.lower().startswith("signal-") or "signal" in low.split("/")[:-1]:
        return "Signal"
    return None


def classify(R, path, rel, st):
    """Where one loose file belongs: (folders inside the library, reason, kind, date, date has time)."""
    name = os.path.basename(path)
    x = ext_of(name)
    kind, folders = R.kind.get(x, "other"), rel.lower().split("/")[:-1]
    if st.st_size == 0:
        return ["_Review", "Junk"], "empty file (0 bytes)", "junk", None, False
    if kind == "junk":
        return ["_Review", "Junk"], f".{x} files are usually leftovers", kind, None, False
    if kind == "installer":
        return ["_Review", "Installers"], "an installer - keep it only if you still need it", kind, None, False
    chat = chat_app(name, rel)
    if kind in DOC_TYPES:
        cat, words = R.topic(name)
        if cat:
            return ["Documents", cat], f"its name has {words}", kind, None, False
        if chat:
            return ["WhatsApp & Chats", "Documents"], f"a {chat} document ({words})", kind, None, False
        return ["Documents", "Other documents", kind], f"{kind[:-1] if kind.endswith('s') else kind}: {words}", \
            kind, None, False
    if kind in ("photo", "video", "audio") and chat:
        sub = {"photo": "Images", "video": "Videos", "audio": "Audio"}[kind]
        return ["WhatsApp & Chats", sub], f"{chat} {sub.lower()} (from its name or folder)", kind, None, False
    if kind in ("photo", "video"):
        d, how, timed = media_date(path, name, x, st)
        y = f"{d:%Y}" if d else "Undated"
        when = f"{d:%d %b %Y}" if d else "no usable date"
        if kind == "photo" and (SCREEN_RX.match(name) or "screenshots" in folders):
            return ["Screenshots", y], f"screenshot from {when} ({how})", "screenshot", d, timed
        if kind == "video":
            return ["Videos", y], f"video from {when} ({how})", kind, d, timed
        if how == "its modified date" and not CAMERA_RX.match(name):
            cat, words = R.topic(name)
            if cat:  # e.g. a photo of a passport or a receipt that you named yourself
                return ["Documents", cat], f"picture whose name has {words}", kind, d, timed
        return ["Photos", y] + ([f"{d:%Y-%m}"] if d else []), f"photo taken {when} ({how})", kind, d, timed
    if kind == "audio":
        if x in ("amr", "3ga") or VOICE_RX.match(name) or any("record" in f or "voice" in f for f in folders):
            return ["Voice notes"], "voice recording (from its name, type or folder)", "voice", None, False
        return ["Music"], "music or audio", kind, None, False
    if kind in KIND_HOME:
        return [KIND_HOME[kind]], f".{x} file", kind, None, False
    return ["_Review", "Unknown"], f"tidy doesn't know .{x or 'extension-less'} files", "other", None, False


# ================================================================ 6. SCANNING (read-only)
class Scan:
    """Walks folders with os.scandir and sorts what it finds into: loose files to sort, named folders that move
    as one unit, generic folders that get opened, and things left alone (each with the reason)."""
    def __init__(s, cfg, R, allow=None, trust=False, quiet=False):
        s.cfg, s.R, s.lib, s.allow, s.trust, s.now = cfg, R, cfg["library"], allow, trust, time.time()
        s.own = {key(SCRIPT), key(CONFIG), key(DATA)}
        s.files, s.units, s.opened, s.skipped, s.entries, s.bytes = [], [], [], [], {}, 0
        s.prog = Progress("Looking at files:", quiet=quiet)

    def skip(s, p, why): s.skipped.append([p, why])

    def leave_alone(s, p, e, st):
        if key(p) in s.own:
            return "tidy's own file"
        if inside(p, s.lib) and not (s.allow and inside(p, s.allow)):
            return "already in your library"
        if is_hidden(e.name, st):
            return "hidden"
        if is_link(e, st):
            return "a link or shortcut to somewhere else"
        return None

    def dir_problem(s, p, name, names=True):
        if inside(HERE, p):
            return "this folder holds tidy.py itself"
        if ext_of(name) in s.R.packages:
            return "an app or photo-library package"
        if names and any(fnmatch.fnmatchcase(name.lower(), x) for x in s.R.skipdirs):
            return "an app's or the system's folder (never touched)"
        m = s.R.project(p)
        return f"a code project (it has {m}), kept exactly as it is" if m else None

    def file_problem(s, name, st):
        x, low = ext_of(name), name.lower()
        if x in s.R.unfinished:
            return "download not finished yet"
        if low.startswith("~$"):
            return "temporary file of an open Office document"
        if x in s.R.shortcuts:
            return "a shortcut (kept where it is)"
        if low in s.R.markers or low.endswith(s.R.marker_ends):
            return "belongs to a code project"
        if is_cloud(st):
            return "online-only cloud file (left alone so nothing downloads)"
        if not s.trust and s.R.recent(st, s.now):
            return f"changed in the last {s.cfg['min_age_minutes']} minutes (maybe still in use)"
        return None

    def walk(s, d, rel, sub, mode, rank):
        try:
            ents = scandir(d)
        except OSError as e:
            return s.skip(d, reason(e))
        s.entries[key(d)] = 0
        for e in ents:
            p, r = os.path.join(d, e.name), f"{rel}/{e.name}" if rel else e.name
            if e.name.lower() in IGNORABLE:
                continue
            s.entries[key(d)] += 1
            try:
                st = e.stat(follow_symlinks=False)
            except OSError as x:
                s.skip(p, reason(x))
                continue
            why = s.leave_alone(p, e, st)
            if not why and stat.S_ISDIR(st.st_mode):
                why = s.dir_problem(p, e.name, names=mode != "import")
                if not why:
                    if mode == "resort":
                        if structural(r.split("/")):
                            s.walk(p, r, sub, mode, rank)
                            continue
                        why = "a folder inside your library (kept as it is)"
                    elif not sub:
                        why = "a folder (only loose files are sorted here; switch on 'sort inside folders' to change)"
                    elif mode == "import" or s.R.is_generic(e.name):
                        s.opened.append(p)
                        s.walk(p, r, sub, mode, rank)
                        continue
                    else:
                        s.unit(p, r, rank, st.st_mtime)
                        continue
            elif not why and stat.S_ISREG(st.st_mode):
                why = s.file_problem(e.name, st)
                if not why:
                    s.files.append({"src": p, "rel": r, "st": st, "rank": rank})
                    s.bytes += st.st_size
                    s.prog.step()
                    continue
            s.skip(p, why or "not a regular file")

    def unit(s, p, rel, rank, mtime):
        """A named folder ('Tax 2023') moves as one piece - unless something inside makes that unsafe."""
        files, why, stack = [], None, [p]
        while stack and not why:
            d = stack.pop()
            why = s.dir_problem(d, os.path.basename(d), names=False) if d != p else None
            try:
                ents = [] if why else scandir(d)
            except OSError as e:
                why = reason(e)
                break
            for e in ents:
                q, x = os.path.join(d, e.name), ext_of(e.name)
                try:
                    st = e.stat(follow_symlinks=False)
                except OSError as err:
                    why = reason(err)
                    break
                if is_link(e, st):
                    why = "it has a link or shortcut folder inside"
                elif stat.S_ISDIR(st.st_mode):
                    stack.append(q)
                    continue
                elif not stat.S_ISREG(st.st_mode):
                    why = "it has a special file inside"
                elif is_cloud(st):
                    why = "it has online-only cloud files inside"
                elif s.R.recent(st, s.now):
                    why = f"something inside changed in the last {s.cfg['min_age_minutes']} minutes"
                elif x in s.R.unfinished:
                    why = "a download inside isn't finished"
                elif x in s.R.appdata and e.name.lower() not in IGNORABLE:
                    why = f"it looks like an app's data folder (it has .{x} files)"
                else:
                    files.append((q, e.name, st))
                    s.prog.step()
                    continue
                break
        if why:
            return s.skip(p, f"folder left as it is: {why}")
        s.units.append({"src": p, "rel": rel, "files": files, "rank": rank, "mtime": mtime})
        s.bytes += sum(f[2].st_size for f in files)


def structural(parts):
    """Folders tidy itself makes inside the library (re-sorting opens these; any other folder stays whole)."""
    top, rest, n = parts[0], parts[1:], len(parts) - 1
    if top == "Documents":
        return n == 0 or n == 1 and (rest[0] in RULES or rest[0] == "Other documents") or \
            n == 2 and rest[0] == "Other documents" and rest[1] in DOC_TYPES
    if top == "Photos":
        return n == 0 or re.fullmatch(r"\d{4}|Undated", rest[0]) and (n == 1 or n == 2 and re.fullmatch(
            r"\d{4}-\d\d", rest[1])) is not None
    if top in ("Screenshots", "Videos"):
        return n == 0 or n == 1 and re.fullmatch(r"\d{4}|Undated", rest[0]) is not None
    return top == "WhatsApp & Chats" and n <= 1 or top in ("Music", "Voice notes", *KIND_HOME.values()) and n == 0


# ================================================================ 7. PLANNING (never changes anything on disk)
def rank_of(p):
    kf = known_folders()
    for i, n in enumerate(("Documents", "Desktop", "Downloads"), 1):
        if key(kf[n]) == key(p) or os.path.basename(p.rstrip("\\/")).lower() == n.lower():
            return i
    return 4


def roots_for(cfg, mode, folder):
    if mode == "import":
        return [(folder, True, 5)]
    if mode == "resort":
        return [(cfg["library"], True, 0)]
    src = cfg["sources"]
    if mode == "watch":
        src = [s for s in src if os.path.basename(s["path"].rstrip("\\/")).lower() == "downloads"][:1] or src[:1]
        return [(s["path"], False, rank_of(s["path"])) for s in src]
    return [(s["path"], bool(s.get("subfolders")), rank_of(s["path"])) for s in src]


COPY_RX = re.compile(r"(?i)(\s\(\d+\)|\s-\scopy(\s\(\d+\))?|\scopy(\s\d+)?)$")


def plain_name(name):
    """'Copy of report (1).pdf' -> 'report.pdf' (used to compare names and to pick the copy to keep)."""
    b, e = os.path.splitext(name)
    return (COPY_RX.sub("", re.sub(r"(?i)^(copy of |copy_of_)+", "", b)) + e).lower()


def find_dupes(pool, quiet=False):
    """Byte-identical files: same size -> same first/last 64 KB -> same SHA-256. Also 'probably the same' pairs."""
    by_size = defaultdict(list)
    for x in pool:
        if x["size"] > 0:
            by_size[x["size"]].append(x)
    todo = [g for g in by_size.values() if len(g) > 1]
    prog, groups, maybe = Progress("Checking for duplicates:", sum(map(len, todo)), quiet=quiet), [], []
    for g in todo:
        n, byq = g[0]["size"], defaultdict(list)
        for x in g:
            prog.step()
            try:
                byq[quick(x["src"], n)].append(x)
            except OSError:
                pass
        for g2 in byq.values():
            if len(g2) > 1 and n <= 131072:  # small files: the quick look already read all of them
                groups.append(g2)
            elif len(g2) > 1:
                byh = defaultdict(list)
                for x in g2:
                    try:
                        byh[sha(x["src"])].append(x)
                    except OSError:
                        pass
                groups += [g3 for g3 in byh.values() if len(g3) > 1]
    prog.end()
    for i, grp in enumerate(groups):
        grp.sort(key=lambda x: (x["rank"], x["mtime"], plain_name(os.path.basename(x["src"])) !=
                                os.path.basename(x["src"]).lower(), len(os.path.basename(x["src"]))))
        for x in grp:
            x["_g"] = i
    for g in todo:  # same size and name apart from ' (1)' / 'Copy of', but different content
        names = defaultdict(list)
        for x in g:
            names[plain_name(os.path.basename(x["src"]))].append(x)
        for same in names.values():
            maybe += [[same[0]["src"], x["src"], size(x["size"])] for x in same[1:] if not (
                      same[0].get("lib") and x.get("lib")) and (x.get("_g") is None or x.get("_g") != same[0].get("_g"))]
    return groups, maybe


def library_files(lib, sizes=None, skip=()):
    """Files already in the library (not in _Review or the phone staging area): used to spot duplicates."""
    out, stack = [], [lib] if isdir(lib) else []
    while stack:
        d = stack.pop()
        try:
            ents = scandir(d)
        except OSError:
            continue
        for e in ents:
            p = os.path.join(d, e.name)
            try:
                st = e.stat(follow_symlinks=False)
            except OSError:
                continue
            if e.name in ("_Review", STAGING) and d == lib or is_link(e, st) or any(inside(p, x) for x in skip):
                continue
            if stat.S_ISDIR(st.st_mode):
                stack.append(p)
            elif stat.S_ISREG(st.st_mode) and not is_hidden(e.name, st) and (sizes is None or st.st_size in sizes):
                out.append({"src": p, "size": st.st_size, "mtime": st.st_mtime, "rank": 0, "lib": True})
    return out


def place_unit(R, lib, u):
    """Where a named folder goes, as a whole."""
    name, all_files = os.path.basename(u["src"]), u["files"]
    fs = [f for f in all_files if f[1].lower() not in IGNORABLE and not f[1].startswith(".")]
    it = {"src": u["src"], "kind": "dir", "size": sum(f[2].st_size for f in all_files), "rank": u["rank"],
          "mtime": u["mtime"], "files": len(all_files)}
    kinds = Counter(R.kind.get(ext_of(f[1]), "other") for f in fs)
    if not fs:
        return dict(it, dst=os.path.join(lib, "_Review", "Empty folders", name), why="empty folder")
    if kinds["photo"] + kinds["video"] >= 0.6 * len(fs):
        years = Counter()
        for q, n, st in [f for f in fs if R.kind.get(ext_of(f[1])) in ("photo", "video")][:60]:
            d = media_date(q, n, ext_of(n), st)[0]
            if d:
                years[d.year] += 1
        y = str(years.most_common(1)[0][0]) if years else "Undated"
        return dict(it, dst=os.path.join(lib, "Photos", y, name), why=f"a folder of photos and videos, mostly from {y}")
    cat, words = R.topic(name)
    if cat:
        return dict(it, dst=os.path.join(lib, "Documents", cat, name), why=f"folder name has {words}")
    top, k = kinds.most_common(1)[0]
    if top in KIND_HOME and k >= 0.6 * len(fs):
        return dict(it, dst=os.path.join(lib, KIND_HOME[top], name), why=f"a folder of mostly {top} files")
    return dict(it, dst=os.path.join(lib, "Documents", "Other documents", name),
                why="a named folder of related files, kept together")


def make_plan(cfg, mode="organize", folder=None, quiet=False):
    """Build the plan: what moves where, and why. Reads only; never changes anything on disk.
    mode: organize | dupes | watch | resort | import (a folder, e.g. photos copied from a phone)."""
    R, lib = Rules(cfg), cfg["library"]
    staging = bool(folder) and inside(folder, os.path.join(lib, STAGING))
    scan = Scan(cfg, R, allow=folder if mode == "import" else lib if mode == "resort" else None,
                trust=staging, quiet=quiet)
    roots = roots_for(cfg, mode, folder)
    for root, sub, rank in roots:
        m = isdir(root) and R.project(root)
        if not isdir(root):
            scan.skip(root, "folder not found")
        elif m and (isdir(os.path.join(root, m)) or m.lower() == "pyvenv.cfg"):
            scan.skip(root, f"the whole folder is a code project (it has {m})")
        else:
            scan.walk(root, "", sub, mode, rank)
    scan.prog.end()
    items, prog = [], Progress("Working out where things go:", len(scan.files), quiet=quiet)
    for f in scan.files:
        prog.step()
        parts, why, kind, d, timed = classify(R, f["src"], f["rel"], f["st"])
        items.append({"src": f["src"], "dst": os.path.join(lib, *parts, os.path.basename(f["src"])), "why": why,
                      "kind": "file", "size": f["st"].st_size, "mtime": f["st"].st_mtime, "rank": f["rank"],
                      "_group": kind, "_date": d, "_timed": timed})
    prog.end()
    # Live Photos and edit files (IMG_1234.HEIC + IMG_1234.MOV / .AAE) stay together with their photo
    pairs = defaultdict(list)
    for it in items:
        stem = re.sub(r"(?i)^img_[eo](?=\d)", "img_", os.path.splitext(os.path.basename(it["src"]))[0]).lower()
        pairs[(key(os.path.dirname(it["src"])), stem)].append(it)
    for grp in pairs.values():
        main = next((i for i in grp if ext_of(i["src"]) in ("heic", "heif", "jpg", "jpeg") and
                     i["_group"] == "photo" and os.sep + "Photos" + os.sep in i["dst"]), None)
        for it in grp:
            k = R.kind.get(ext_of(it["src"]))
            if main and it is not main and not it["_group"] == "junk" and (k in ("video", "sidecar") or k ==
                                                                            "photo" and it["_group"] == "photo"):
                it["dst"] = os.path.join(os.path.dirname(main["dst"]), os.path.basename(it["src"]))
                it["why"], it["_main"] = f"kept together with {os.path.basename(main['src'])} (Live Photo/edit/RAW)", main
    # duplicates (compared with each other and with what is already in the library)
    if mode != "resort":  # (re-sorting compares the library's loose files with each other)
        sizes = None if mode == "dupes" else {i["size"] for i in items}
        pool = items + library_files(lib, sizes, [folder] if folder else [])
    groups, maybe = find_dupes(items if mode == "resort" else pool, quiet)
    dups = []
    for grp in groups:
        keep = grp[0]
        for x in grp[1:]:
            if x.get("lib") and mode != "dupes":
                continue
            x.update(kind="file", dst=os.path.join(lib, "_Review", "Duplicates", os.path.basename(x["src"])), dup=1,
                     why=f"identical to {keep['src']} (that copy is kept)",
                     _keep={"src": keep["src"]} if mode == "dupes" else keep)  # in this mode the kept copy stays
            x.pop("_main", None)
            dups.append(x)
    if mode == "dupes":
        items, scan.units, scan.opened = dups, [], []  # only duplicates move in this mode
    items += [place_unit(R, lib, u) for u in scan.units]
    if cfg.get("tidy_names"):
        tidy_names(items)
    # never overwrite: a taken name gets ' (2)', ' (3)'...; identical content means duplicate
    taken, keep = set(), []
    for it in sorted(items, key=lambda i: (i["kind"] != "file", "_main" in i, key(i["src"]))):
        d = it["dst"]
        if key(d) == key(it["src"]):
            continue  # re-sort: already in the right place
        if it.get("_orig") and (exists(d) or key(d) in taken):
            d, it["why"] = it["_orig"], it["why"].split("; tidy name")[0]
        if it["kind"] == "file" and not it.get("dup") and exists(d) and not isdir(d) and same_content(d, it["src"]):
            d = os.path.join(lib, "_Review", "Duplicates", os.path.basename(it["src"]))
            it.update(dup=1, why=f"identical to {it['dst']} already in your library", _keep={"src": it["dst"]})
        it["dst"] = unique(d, taken, folder=it["kind"] != "file")
        taken.add(key(it["dst"]))
        keep.append(it)
    items = keep
    # generic folders that end up empty go to _Review/Empty folders (not for tidy's own phone staging area)
    moving = Counter(key(os.path.dirname(i["src"])) for i in items)
    empty = set()
    for d in sorted(scan.opened, key=lambda p: -p.count(os.sep)):
        if moving[key(d)] >= scan.entries.get(key(d), 1 << 30):
            empty.add(key(d))
            moving[key(os.path.dirname(d))] += 1
    for d in [] if staging else scan.opened:
        if key(d) in empty and key(os.path.dirname(d)) not in empty:
            dst = unique(os.path.join(lib, "_Review", "Empty folders", os.path.basename(d)), taken, folder=True)
            taken.add(key(dst))
            items.append({"src": d, "dst": dst, "kind": "dir", "size": 0, "mtime": 0, "files": 0, "empty": 1,
                          "why": "folder left empty after sorting"})
    for it in items:
        if it.get("_keep"):
            it["kept"] = it["_keep"].get("dst") or it["_keep"]["src"]
        r = os.path.relpath(it["dst"], lib).split(os.sep)
        it["cat"] = "/".join(r[:2]) if r[0] in ("Documents", "_Review", "WhatsApp & Chats") and len(r) > 2 else r[0]
    items = [{k: v for k, v in i.items() if not k.startswith("_") and k not in ("rank", "lib")} for i in items]
    return {"id": time.strftime("%Y%m%d-%H%M%S-") + f"{int(time.time() * 1000) % 1000:03d}", "made": stamp(), "mode": mode, "library": lib, "folder": folder,
            "roots": [r[0] for r in roots], "items": items, "skipped": scan.skipped, "maybe": maybe,
            "scanned": len(scan.files) + sum(len(u["files"]) for u in scan.units), "scanned_bytes": scan.bytes}


def tidy_names(items):
    """Optional: camera files get their date as name ('2024-03-12 10.11.12.jpg'); 'Copy of' and ' (1)' go."""
    for it in sorted((i for i in items if i["kind"] == "file" and not i.get("dup")), key=lambda i: "_main" in i):
        name = os.path.basename(it["src"])
        b, x = os.path.splitext(name)
        if it.get("_main"):
            new = os.path.splitext(os.path.basename(it["_main"]["dst"]))[0] + x
        elif it.get("_timed") and it.get("_group") in ("photo", "video") and CAMERA_RX.match(name):
            new = f"{it['_date']:%Y-%m-%d %H.%M.%S}{x.lower()}"
        else:
            new = re.sub(r" \(1\)$", "", re.sub(r"(?i)^copy of ", "", b)) + x
        if new != name and new.strip():
            it["_orig"], it["dst"] = it["dst"], os.path.join(os.path.dirname(it["dst"]), new)
            it["why"] += f"; tidy name (was {name})"


def cats(plan):
    out = defaultdict(lambda: [0, 0])
    for i in plan["items"]:
        out[i["cat"]][0] += 1
        out[i["cat"]][1] += i["size"]
    return sorted(out.items(), key=lambda kv: -kv[1][1])


def summary(plan):
    it = plan["items"]
    du = [i for i in it if i.get("dup")]
    mv = [i for i in it if not i.get("dup")]
    title("The plan (nothing has been changed yet)")
    say(f"Looked at {count(plan['scanned'], 'file')} ({size(plan['scanned_bytes'])}).")
    say(f"Will move {count(len(mv), 'item')} ({size(sum(i['size'] for i in mv))}) into {plan['library']}")
    if du:
        say(f"{count(len(du), 'duplicate')} ({size(sum(i['size'] for i in du))}) go to _Review/Duplicates "
            "(nothing is deleted).")
    say(f"{count(len(plan['skipped']), 'thing')} will be left alone (the report says why for each one).")
    for c, (n, b) in cats(plan)[:14]:
        say(f"   {c[:40]:<40} {n:>8,}  {size(b):>10}")


def save_plan(plan):
    os.makedirs(os.path.join(DATA, "plans"), exist_ok=True)
    p = os.path.join(DATA, "plans", plan["id"] + ".json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False)
    return p


def last_plan():
    d = os.path.join(DATA, "plans")
    names = sorted(n for n in os.listdir(d) if n.endswith(".json")) if os.path.isdir(d) else []
    if not names:
        return None
    with open(os.path.join(d, names[-1]), encoding="utf-8") as f:
        return json.load(f)


# ================================================================ 8. APPLYING THE PLAN, WITH THE JOURNAL
def has_files(d):
    return any(os.path.basename(f).lower() not in IGNORABLE for f in tree_of(d)[1])


def move_split(J, src, dst):
    """A folder going to another drive: file by file (each copied, verified and journaled), then the emptied
    folders are removed."""
    dirs, files = tree_of(src)
    for d in dirs:
        mkdirs(os.path.normpath(os.path.join(dst, os.path.relpath(d, src))), J)
    for f in files:
        if STOP[0]:
            raise Skip("stopped part-way; the rest of this folder is still where it was")
        t, st = os.path.join(dst, os.path.relpath(f, src)), lstat(f)
        n = J.begin(op="move", src=f, dst=t, how="copy", kind="file", size=st.st_size, mtime=st.st_mtime)
        J.sync()
        try:
            J.w(t="done", n=n, sha=transfer(f, t, "copy", st))
        except (OSError, Skip) as e:
            J.w(t="fail", n=n, why=reason(e))
            raise
    for d in reversed(dirs):
        try:
            os.rmdir(L(d))
            J.w(t="rmdir", path=d)
        except OSError:
            pass


def apply_plan(plan, kind=None, force_copy=False, stop_after=None, quiet=False):
    """Carry out a plan the user said YES to. Each batch of intentions is on disk before any file moves."""
    items, lib = plan["items"], plan["library"]
    J = Journal(kind or plan["mode"], plan=plan["id"], library=lib)
    prog = Progress("Moving", len(items), sum(i["size"] for i in items), quiet)
    moved, failed, streak, taken = [], [], 0, set()
    with Stoppable():
        for start in range(0, len(items), 64):
            batch = []
            for it in items[start:start + 64]:
                try:
                    st = lstat(it["src"])
                    if exists(it["dst"]) or key(it["dst"]) in taken:  # never overwrite: pick a free name
                        it["dst"] = unique(it["dst"], taken, folder=it["kind"] != "file")
                    taken.add(key(it["dst"]))
                    how = "copy" if force_copy or not same_drive(it["src"], it["dst"]) else "rename"
                    how = "split" if how == "copy" and it["kind"] != "file" else how
                except OSError as e:
                    failed.append([it["src"], reason(e)])
                    prog.step(1, it["size"])
                    continue
                it["_n"], it["_how"] = J.begin(op="move", src=it["src"], dst=it["dst"], how=how, kind=it["kind"],
                                               size=it["size"], mtime=it["mtime"]), how
                batch.append(it)
            J.sync()  # the intentions are safely on disk before anything moves
            for it in batch:
                if STOP[0] or stop_after is not None and len(moved) >= stop_after:
                    STOP[0] = True
                    J.w(t="fail", n=it["_n"], why="stopped before this one")
                    continue
                try:
                    st = lstat(it["src"])
                    if it["kind"] == "file" and (st.st_size != it["size"] or abs(st.st_mtime - it["mtime"]) > 2):
                        raise Skip("it changed after the plan was made - run tidy again to include it")
                    if it.get("empty") and has_files(it["src"]):
                        raise Skip("it isn't empty any more")
                    mkdirs(os.path.dirname(it["dst"]), J)
                    if it["_how"] == "split":
                        move_split(J, it["src"], it["dst"])
                        h = None
                    else:
                        h = transfer(it["src"], it["dst"], it["_how"], st)
                    J.w(t="done", n=it["_n"], **({"sha": h} if h else {}))
                    moved.append(it)
                    streak = 0
                except (OSError, Skip) as e:
                    J.w(t="fail", n=it["_n"], why=reason(e))
                    failed.append([it["src"], reason(e)])
                    streak += 1
                    if getattr(e, "errno", 0) == errno.ENOSPC or streak >= 25:
                        warn("\nToo many problems in a row (drive full or unplugged?) - stopping to be safe.")
                        STOP[0] = True
                prog.step(1, it["size"])
            if STOP[0]:
                break
        stopped = STOP[0]
    prog.end()
    dups = [i for i in moved if i.get("dup")]
    if dups:  # the list of duplicates: where each came from and which copy was kept
        out = unique(os.path.join(lib, "_Review", "Duplicates", f"duplicates {J.id}.csv"))
        with open(L(out), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Duplicate (now here)", "It came from", "The copy that was kept", "Size"])
            w.writerows([i["dst"], i["src"], i.get("kept", ""), i["size"]] for i in dups)
        J.w(t="create", path=out, size=lstat(out).st_size)
    J.close(status="stopped" if stopped else "complete", moved=len(moved), failed=len(failed))
    res = {"run": J.id, "moved": moved, "failed": failed, "stopped": stopped}
    if not quiet:
        mv = [i for i in moved if not i.get("dup")]
        title("Stopped early - everything already moved is safe, and can be undone." if stopped else "Done!")
        good(f"Moved {count(len(mv), 'item')} ({size(sum(i['size'] for i in mv))}).")
        if dups:
            say(f"{count(len(dups), 'duplicate')} ({size(sum(i['size'] for i in dups))}) are waiting in "
                "_Review/Duplicates - check them, then delete them yourself if you like.")
        for src, why in failed[:15]:
            warn(f"  Not moved: {src}\n      because {why}")
        if len(failed) > 15:
            warn(f"  ...and {len(failed) - 15:,} more (see the report).")
        say(f"Changed your mind? 'Undo' in the menu (or: tidy.py undo) puts everything back. Run id: {J.id}")
    return res


# ================================================================ 9. UNDO AND CRASH RECOVERY
def read_run(path):
    """A journal as a dict. A half-written last line (power cut) is simply ignored."""
    r = {"path": path, "head": {}, "seq": [], "done": {}, "fail": {}, "end": None, "undone": None}
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                x = json.loads(line)
            except ValueError:
                continue
            t = x.get("t")
            if t == "run":
                r["head"] = x
            elif t in ("begin", "mkdir", "rmdir", "create"):
                r["seq"].append(x)
            elif t in ("done", "fail"):
                r[t][x.get("n")] = x
            elif t in ("end", "undone"):
                r[t] = x
    return r


def list_runs():
    d = os.path.join(DATA, "runs")
    names = sorted((n for n in os.listdir(d) if n.endswith(".jsonl")), reverse=True) if os.path.isdir(d) else []
    return [read_run(os.path.join(d, n)) for n in names]


def moves(r): return [b for b in r["seq"] if b["t"] == "begin" and b["n"] in r["done"] and b["how"] != "split"]


def describe(r):
    mv = moves(r)
    s = f"{r['head'].get('started', '?')}  {r['head'].get('kind', '?'):<9} moved {count(len(mv), 'item')} " \
        f"({size(sum(b['size'] for b in mv))})"
    if not r["end"] or r["end"].get("status") in ("stopped", "interrupted"):
        s += "  [stopped part-way]"
    if r["undone"]:
        s += "  [undone]" if not r["undone"].get("problems") else "  [partly undone]"
    return s


def recover(quiet=False):
    """After a crash or power cut: settle the one unfinished step of any run that never reached its end.
    Our own partial copies are removed; a finished copy whose original still exists is taken back."""
    for r in list_runs():
        if r["end"]:
            continue
        with open(r["path"], "a", encoding="utf-8") as f:
            for b in r["seq"]:
                if b["t"] != "begin" or b["n"] in r["done"] or b["n"] in r["fail"]:
                    continue
                src, dst, state = b["src"], b["dst"], "fail"
                try:
                    if b["how"] == "copy":
                        if exists(dst + ".tidy-part") and exists(src):
                            remove(dst + ".tidy-part")
                        if exists(dst) and exists(src):
                            if lstat(dst).st_size == lstat(src).st_size and sha(dst) == sha(src):
                                remove(dst)
                        elif exists(dst):
                            state = "done"
                    elif exists(dst) and not exists(src):
                        state = "done"
                except OSError:
                    pass
                f.write(json.dumps({"t": state, "n": b["n"], "why": "interrupted"}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"t": "end", "ended": stamp(), "status": "interrupted"}) + "\n")
        if not quiet:
            warn(f"An earlier run ({r['head'].get('started')}) was cut off. I've tidied up its unfinished step - "
                 "nothing was lost, and it can be undone from the menu.")


def undo_run(r, quiet=False):
    """Put everything from one run back where it was, then check each file really is back."""
    J = Journal("undo", of=r["head"].get("id"), library=r["head"].get("library"))
    seq = list(reversed(r["seq"]))  # newest first; folders tidy created are removed last, once they're empty
    todo, problems, back = [b for b in seq if b["t"] != "mkdir"] + [b for b in seq if b["t"] == "mkdir"], [], []
    prog = Progress("Putting back", len(todo), quiet=quiet)
    with Stoppable():
        for b in todo:
            if STOP[0]:
                break
            prog.step()
            try:
                if b["t"] == "mkdir":
                    if isdir(b["path"]) and not os.listdir(L(b["path"])):
                        os.rmdir(L(b["path"]))
                elif b["t"] == "rmdir":
                    mkdirs(b["path"], J)
                elif b["t"] == "create":
                    if exists(b["path"]) and lstat(b["path"]).st_size == b.get("size"):
                        remove(b["path"])  # tidy's own list of duplicates
                elif b["n"] in r["done"] and b["how"] != "split":
                    src, dst = b["src"], b["dst"]
                    if not exists(dst):
                        if not exists(src):
                            problems.append([src, f"not found at {dst} any more (moved or deleted after that run?)"])
                        continue  # otherwise it is already back
                    to = unique(src, folder=isdir(dst))
                    mkdirs(os.path.dirname(to), J)
                    how = "rename" if same_drive(dst, to) else "split" if isdir(dst) else "copy"
                    n = J.begin(op="move", src=dst, dst=to, how=how, kind=b["kind"], size=b["size"], mtime=b["mtime"])
                    J.sync()
                    if how == "split":
                        move_split(J, dst, to)
                    else:
                        transfer(dst, to, how, lstat(dst))
                    J.w(t="done", n=n)
                    back.append((b, to))
                    if to != src:
                        problems.append([src, f"put back as '{os.path.basename(to)}' because another file now has "
                                              "the original name"])
            except (OSError, Skip) as e:
                problems.append([b.get("src") or b.get("path"), reason(e)])
        stopped = STOP[0]
    prog.end()
    for b, to in back:  # check that every file really is back
        if not exists(to) or b["kind"] == "file" and lstat(to).st_size != b["size"]:
            problems.append([to, "not found where it should be after undo"])
    J.close(status="stopped" if stopped else "complete", moved=len(back), failed=len(problems))
    if not stopped:
        with open(r["path"], "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": "undone", "at": stamp(), "by": J.id, "problems": len(problems)}) + "\n")
    if not quiet:
        (warn if problems or stopped else good)(f"\nPut back {count(len(back), 'item')}" +
                                                (" (stopped early)." if stopped else "."))
        for p, why in problems[:30]:
            warn(f"  {p}\n      {why}")
        say("Every other file is back exactly where it was." if back else "")
        if r["head"].get("kind") == "phone":
            say(f"The imported copies are back in the '{STAGING}' folder of your library; your phone still has "
                "its originals. Delete that folder if you don't want them.")
    return not problems and not stopped


def undo_menu(run_id=None):
    runs = [r for r in list_runs() if moves(r)]
    if not runs:
        return say("There is nothing to undo yet.")
    if run_id:
        r = next((r for r in runs if r["head"].get("id") == run_id), None)
        if not r:
            return bad(f"No run with id {run_id}.")
    else:
        i = pick("Which run should be undone? (newest first)", [describe(r) for r in runs[:30]])
        if i is None:
            return
        r = runs[i]
    later = [x for x in runs if x["head"].get("started", "") > r["head"].get("started", "") and not x["undone"]]
    if later:
        warn(f"Note: {count(len(later), 'later run')} came after this one. If they moved the same files again, "
             "undo those first.")
    if confirm(f"This moves {count(len(moves(r)), 'item')} back to where they were before that run."):
        with Lock():
            undo_run(r)


# ================================================================ 10. THE HTML REPORT
REPORT = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,
initial-scale=1"><title>tidy report</title><style>
:root{--bg:#fff;--fg:#1d2330;--mut:#5d6675;--card:#f1f4f8;--line:#dde2e8;--bar:#2a78d6}
@media(prefers-color-scheme:dark){:root{--bg:#14171c;--fg:#e8ebf0;--mut:#9aa3b1;--card:#1f242c;--line:#2e3540;
--bar:#3b82d6}}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,-apple-system,sans-serif}
main{max-width:1100px;margin:auto;padding:16px}h2{margin:1.8em 0 .5em;font-size:1.15em}.mut{color:var(--mut)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.card{background:var(--card);border-radius:10px;padding:12px}.card b{display:block;font-size:1.35em}
.bar{display:grid;grid-template-columns:minmax(0,15em) minmax(0,1fr) 9em;gap:8px;align-items:center;margin:4px 0}
.bar span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.bar i{display:block;height:12px;
border-radius:3px;background:var(--bar)}table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:5px;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}
input{box-sizing:border-box;width:100%;padding:8px;margin:4px 0;font:inherit;color:inherit;background:var(--bg);
border:1px solid var(--line);border-radius:8px}pre{background:var(--card);padding:10px;border-radius:8px;
overflow:auto;font-size:12.5px;max-height:500px}.two{display:grid;gap:12px;
grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr))}</style><main>@BODY@</main>
<script id="d" type="application/json">@DATA@</script><script>
const D=JSON.parse(document.getElementById('d').textContent),E=s=>String(s).replace(/[&<>"]/g,c=>'&#'+
c.charCodeAt(0)+';'),N=n=>String(n).replace(/\\B(?=(\\d{3})+(?!\\d))/g,',');
function T(id,rows,cols){const b=document.getElementById(id);if(!b)return;const q=b.querySelector('input'),
o=b.querySelector('div');function draw(){const w=q.value.toLowerCase(),m=w?rows.filter(r=>r.join(' ')
.toLowerCase().includes(w)):rows;o.innerHTML='<p class=mut>'+N(m.length)+' of '+N(rows.length)+(m.length>500?
' - showing the first 500, type to narrow down':'')+'</p><table><tr>'+cols.map(c=>'<th>'+c).join('')+'</tr>'+
m.slice(0,500).map(r=>'<tr>'+r.map(c=>'<td>'+E(c)).join('')).join('')+'</table>'}q.oninput=draw;draw()}
T('plan',D.items,['From','To','Why']);T('skip',D.skipped,['Left alone','Why']);
T('maybe',D.maybe,['File','Looks like','Size']);T('fail',D.failed,['Not moved','Why']);</script>"""


def tree_text(rows, root, depth):
    agg = defaultdict(lambda: [0, 0])
    for parts, n in rows:
        for k in range(min(len(parts), depth) + 1):
            a = agg[tuple(parts[:k])]
            a[0], a[1] = a[0] + 1, a[1] + n
    return "\n".join("   " * len(k) + (k[-1] if k else root) + f"/   {a[0]:,} - {size(a[1])}"
                     for k, a in sorted(agg.items()))


def write_report(plan, res=None):
    """A self-contained HTML page: summary cards, sizes by category, the 25 largest, the full searchable plan,
    what is left alone and why, and a before/after folder preview."""
    e, lib, items = html.escape, plan["library"], plan["items"]
    du = [i for i in items if i.get("dup")]
    mv = [i for i in items if not i.get("dup")]
    def short(p): return "~" + p[len(HOME):] if inside(p, HOME) else p
    cards = [("Files looked at", f"{plan['scanned']:,}"), ("Total size", size(plan["scanned_bytes"])),
             ("Will move", f"{len(mv):,} - {size(sum(i['size'] for i in mv))}"),
             ("Duplicates", f"{len(du):,} - {size(sum(i['size'] for i in du))} wasted"),
             ("Left alone", f"{len(plan['skipped']):,}")]
    body = [f"<h1>tidy report</h1><p class=mut>Plan made {e(plan['made'])} ({e(plan['mode'])}). Library: "
            f"{e(lib)}. " + ("<b>Nothing has been changed yet.</b>" if res is None else "") + "</p>"]
    if res is not None:
        body.append(f"<h2>What happened</h2><p>Moved {len(res['moved']):,} items" +
                    (" (stopped early)" if res["stopped"] else "") + f". Run id {e(res['run'])} - undo it from the "
                    "menu if you change your mind.</p><div id=fail><input placeholder='Search...'><div></div></div>")
    body.append("<div class=cards>" + "".join(f"<div class=card>{e(a)}<b>{e(b)}</b></div>" for a, b in cards) +
                "</div><h2>Size by category</h2>")
    top = max([b for _, (n, b) in cats(plan)] + [1])
    body += [f"<div class=bar><span>{e(c)}</span><i style='width:{max(1, 100 * b // top)}%'></i><span>{n:,} - "
             f"{size(b)}</span></div>" for c, (n, b) in cats(plan)]
    big = sorted(items, key=lambda i: -i["size"])[:25]
    body.append("<h2>The 25 largest</h2><table><tr><th>Size<th>File<th>Goes to</tr>" + "".join(
        f"<tr><td>{size(i['size'])}<td>{e(short(i['src']))}<td>{e(os.path.relpath(i['dst'], lib))}" for i in big) +
        "</table>")
    before = tree_text([(short(os.path.dirname(i["src"])).split(os.sep), i["size"]) for i in items], "", 9)
    after = tree_text([(os.path.relpath(os.path.dirname(i["dst"]), lib).split(os.sep), i["size"]) for i in items],
                      os.path.basename(lib), 3)
    body.append(f"<h2>Before and after</h2><div class=two><div><b>Where things are now</b><pre>{e(before)}</pre>"
                f"</div><div><b>Where they will be</b><pre>{e(after)}</pre></div></div>")
    for sid, h in (("plan", "The full plan"), ("skip", "Left alone, and why"),
                   ("maybe", "Probably the same (same size and name, different content) - not moved")):
        body.append(f"<h2>{h}</h2><div id={sid}><input placeholder='Search...'><div></div></div>")
    data = {"items": [[short(i["src"]), os.path.relpath(i["dst"], lib), i["why"]] for i in items],
            "skipped": [[short(p), w] for p, w in plan["skipped"]], "maybe": [[short(a), short(b), n] for a, b, n in plan["maybe"]],
            "failed": [[short(p), w] for p, w in (res or {}).get("failed", [])]}
    pre, rest = REPORT.split("@BODY@")
    mid, post = rest.split("@DATA@")
    os.makedirs(os.path.join(DATA, "reports"), exist_ok=True)
    out = os.path.join(DATA, "reports", f"report {plan['id']}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(pre + "".join(body) + mid + json.dumps(data, ensure_ascii=False).replace("<", "\\u003c") + post)
    return out


def show(path):
    try:
        webbrowser.open(pathlib.Path(os.path.abspath(path)).as_uri())
    except Exception:
        pass


# ================================================================ 11. PHONE IMPORT
PHONE_DIRS = ["DCIM", "Pictures", "Download", "Documents", "Movies", "Music", "Recordings",
              "Android/media/com.whatsapp/WhatsApp/Media", "WhatsApp/Media", "Telegram",
              "Android/media/org.telegram.messenger/Telegram"]
NEVER_ON_PHONE = re.compile(r"(?i)(^|/)(\.[^/]*|Databases|Backups)(/|$)|^Android/(data|obb)/")  # app-private: never

ANDROID_HELP = """
To import from an Android phone, tidy uses Google's free tool "adb" (Android platform-tools).
 1. Download "SDK Platform-Tools" for your computer from the official page:
    https://developer.android.com/tools/releases/platform-tools
 2. Unzip it and put the "platform-tools" folder next to tidy.py (or tell tidy where it is).
 3. On the phone: Settings > About phone > tap "Build number" 7 times, until it says you are a developer.
    (Samsung: Settings > About phone > Software information > Build number.)
 4. Settings > System > Developer options (Samsung: Settings > Developer options): turn on "USB debugging".
 5. Plug the phone in with a USB cable, unlock it, and when it asks "Allow USB debugging?" tick
    "Always allow from this computer" and tap Allow."""
MANUAL_HELP = """
No adb? You can copy the files by hand instead:
 Windows: plug the phone in, pick "File transfer" on the phone, open it in File Explorer > Internal storage,
          and copy DCIM, Pictures, Download, Documents and WhatsApp into a new folder on the laptop.
 Mac:     install OpenMTP (free) or Android File Transfer, and copy the same folders into a new folder.
Then choose "Import from a folder" and give tidy that folder."""
IPHONE_HELP = """
iPhones don't show up as a normal drive over USB, so no program can copy from them directly. Instead:
 Windows: unlock the iPhone, plug it in and tap "Trust". Open the Photos app > Import > "From a connected
          device", pick the photos and choose a new, empty folder (e.g. Pictures\\From iPhone) to import into.
 Mac:     unlock the iPhone, plug it in and tap "Trust". Open Image Capture (in Applications), click the
          iPhone, set "Import To" to a new folder (e.g. Pictures/From iPhone) and click "Download All".
Tip: on the iPhone, Settings > Photos > "Transfer to Mac or PC" > "Keep Originals" keeps the original HEIC
photos and MOV videos. tidy reads their dates and keeps Live Photo pairs (IMG_1234.HEIC + IMG_1234.MOV) together.
Then choose "Import from a folder" and give tidy that folder."""


def q(s): return "'" + s.replace("'", "'\\''") + "'"


def safe_name(n):
    """Phone file names can contain characters Windows forbids."""
    if not WIN:
        return n
    n = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", n).rstrip(". ") or "_"
    return "_" + n if re.match(r"(?i)^(con|prn|aux|nul|com\d|lpt\d)(\.|$)", n) else n


def find_adb(cfg):
    exe = "adb.exe" if WIN else "adb"
    for p in (cfg.get("adb_path"), shutil.which("adb"), os.path.join(HERE, "platform-tools"),
              os.path.join(HOME, "platform-tools"), os.path.join(HOME, "Downloads", "platform-tools"),
              os.path.join(os.environ.get("LOCALAPPDATA", HOME), "Android", "Sdk", "platform-tools"),
              os.path.join(HOME, "Library", "Android", "sdk", "platform-tools"),
              os.path.join(HOME, "Android", "Sdk", "platform-tools"), "C:\\platform-tools", "/opt/homebrew/bin"):
        p = os.path.join(p, exe) if p and os.path.isdir(p) else p
        if p and os.path.isfile(p):
            return p
    return None


def wait_for_phone(exe):
    say("Waiting for the phone - plug it in, unlock it and tap Allow (press Ctrl+C to give up).")
    last = None
    try:
        while True:
            out = subprocess.run([exe, "devices"], capture_output=True, text=True, timeout=60).stdout
            devs = [line.split("\t")[:2] for line in out.splitlines()[1:] if "\t" in line]
            ready = [d for d, s in devs if s == "device"]
            if ready:
                return ready[0] if len(ready) == 1 else ready[pick("Which phone?", ready, back=None)]
            msg = ("The phone is asking for permission: unlock it and tap Allow." if any(
                s == "unauthorized" for _, s in devs) else "Connected but not ready: unplug it and plug it in again."
                   if devs else "No phone yet...")
            if msg != last:
                say("  " + msg)
                last = msg
            time.sleep(2)
    except KeyboardInterrupt:
        say("\nOK, stopped waiting.")
    except (OSError, subprocess.SubprocessError) as e:
        bad(f"adb didn't work: {e}")
    return None


class Adb:
    """An Android phone over USB. tidy only reads from it, except the optional 'free up space' step, which
    deletes verified files after you type DELETE FROM PHONE."""
    def __init__(s, exe, serial):
        s.exe, s.serial, s.id = exe, serial, "android-" + re.sub(r"\W", "_", serial)
        s.can_hash = len(s.sh("sha256sum /dev/null")[1].split(" ")[0]) == 64

    def run(s, *a):
        r = subprocess.run([s.exe, "-s", s.serial, *a], capture_output=True, timeout=7200)
        return r.returncode, r.stdout.decode("utf-8", "replace")

    def sh(s, cmd): return s.run("shell", cmd)

    def listing(s):
        """{path on the phone: (size, modified time)} for the usual photo, document and chat folders."""
        out = {}
        for d in PHONE_DIRS:
            txt = s.sh(f"cd /sdcard && [ -d {q(d)} ] && find {q(d)} -type f -exec stat -c '%s %Y %n' {{}} +")[1]
            for line in txt.splitlines():
                n, m, rel = (line.split(" ", 2) + ["", ""])[:3]
                if n.isdigit() and m.isdigit() and not NEVER_ON_PHONE.search(rel):
                    out[rel] = (int(n), int(m))
        return out

    def pull(s, rels, dest):
        """Copy files (adb pull -a keeps their dates) keeping the phone's folder layout."""
        got, by_dir = {}, defaultdict(list)
        for r in rels:
            by_dir[os.path.dirname(r)].append(r)
        for d, rs in by_dir.items():
            local = os.path.join(dest, *[safe_name(x) for x in d.split("/")])
            mkdirs(local)
            plain = [r for r in rs if safe_name(os.path.basename(r)) == os.path.basename(r)]
            if plain:
                s.run("pull", "-a", *["/sdcard/" + r for r in plain], local)
            for r in rs:
                got[r] = os.path.join(local, safe_name(os.path.basename(r)))
                if r not in plain:
                    s.run("pull", "-a", "/sdcard/" + r, got[r])
        return got

    def hashes(s, rels):
        out = {}
        for i in range(0, len(rels), 40):
            for line in s.sh("cd /sdcard && sha256sum " + " ".join(q(r) for r in rels[i:i + 40]))[1].splitlines():
                h, _, r = line.partition("  ")
                if len(h) == 64:
                    out[r] = h
        return out

    def delete(s, rels):
        for i in range(0, len(rels), 40):
            s.sh("cd /sdcard && rm -f -- " + " ".join(q(r) for r in rels[i:i + 40]))


class Folder:
    """A phone that shows up as a folder (e.g. a Linux MTP mount). Its files are copied, never moved."""
    def __init__(s, root, only=None):
        s.root, s.only, s.can_hash = root, only, True
        s.id = "folder-" + re.sub(r"\W", "_", root)[-80:]

    def path(s, r): return os.path.join(s.root, *r.split("/"))

    def listing(s):
        out = {}
        for top in s.only or [""]:
            base = s.path(top) if top else s.root
            for f in tree_of(base)[1] if isdir(base) else []:
                r = os.path.relpath(f, s.root).replace(os.sep, "/")
                if not NEVER_ON_PHONE.search(r):
                    st = lstat(f)
                    out[r] = (st.st_size, int(st.st_mtime))
        return out

    def pull(s, rels, dest):
        got = {}
        for r in rels:
            t = os.path.join(dest, *[safe_name(x) for x in r.split("/")])
            try:
                mkdirs(os.path.dirname(t))
                copy(s.path(r), t, lstat(s.path(r)))
                got[r] = t
            except (OSError, Skip):
                pass
        return got

    def hashes(s, rels):
        out = {}
        for r in rels:
            try:
                out[r] = sha(s.path(r))
            except OSError:
                pass
        return out

    def delete(s, rels):
        for r in rels:
            try:
                remove(s.path(r))
            except OSError:
                pass


def mtp_mounts():
    """Linux: phones mounted by the file manager (gvfs), e.g. /run/user/1000/gvfs/mtp:host=.../Internal storage."""
    base, out = f"/run/user/{os.getuid()}/gvfs" if hasattr(os, "getuid") else "", []
    try:
        for e in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            if e.startswith(("mtp:", "gphoto2:")):
                r = os.path.join(base, e)
                out += [x for x in [r] + [os.path.join(r, n) for n in sorted(os.listdir(r))]
                        if os.path.isdir(os.path.join(x, "DCIM"))][:1]
    except OSError:
        pass
    return out


def memory(pid, mem=None):
    """What was imported from each phone: {phone path: [size, modified, sha256, where the copy is now]}."""
    p = os.path.join(DATA, "phone", pid + ".json")
    if mem is None:
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(mem, f, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def fetch(src, new, stage, mem, quiet=False):
    """Copy new phone files into the staging folder and check each copy (size, plus SHA-256 when the phone
    can compute it). Only checked copies are remembered as imported."""
    rels = sorted(new)
    prog, ok, failed = Progress("Copying from the phone", len(rels), sum(new[r][0] for r in rels), quiet), 0, 0
    for i in range(0, len(rels), 40):
        if STOP[0]:
            break
        part = rels[i:i + 40]
        got = src.pull(part, stage)
        hs = src.hashes(part) if src.can_hash else {}
        for r in part:
            p, (n, m) = got.get(r), new[r]
            try:
                h = p and exists(p) and lstat(p).st_size == n and sha(p)
            except OSError:
                h = None
            if h and (not src.can_hash or hs.get(r) == h):
                mem[r], ok = [n, m, h, p], ok + 1
            else:
                failed += 1
                if p and exists(p):
                    remove(p)  # our own bad copy; the phone still has the original
            prog.step(1, n)
    prog.end()
    if not quiet:
        good(f"Copied and checked {count(ok, 'file')}.")
        if failed:
            warn(f"{count(failed, 'file')} didn't copy correctly; they stay on the phone and are tried again next time.")
    return ok


def phone(cfg):
    kind = cfg.get("phone")
    if kind not in ("Android", "iPhone"):
        i = pick("Which phone is it?", ["Android", "iPhone"])
        if i is None:
            return
        kind = ["Android", "iPhone"][i]
    if kind == "iPhone":
        say(IPHONE_HELP)
        return import_folder(cfg) if yes_no("\nHave you imported the photos into a folder already?") else None
    exe, mounts = find_adb(cfg), mtp_mounts()
    if not exe and mounts:
        good(f"Found the phone as a folder: {mounts[0]}")
        return phone_import(cfg, Folder(mounts[0], PHONE_DIRS))
    if not exe:
        say(ANDROID_HELP)
        p = ask("\nIf you have platform-tools already, paste its folder here (or press Enter to skip)")
        if p:
            cfg["adb_path"] = clean_path(p)
            save_config(cfg)
            exe = find_adb(cfg) or bad("adb wasn't found in that folder.")
        if not exe:
            say(MANUAL_HELP)
            return import_folder(cfg) if yes_no("\nImport from a folder now?") else None
    serial = wait_for_phone(exe)
    if serial:
        phone_import(cfg, Adb(exe, serial))


def phone_import(cfg, src):
    lib = cfg["library"]
    stage = os.path.join(lib, STAGING)
    say("Reading the list of files on the phone (this can take a minute)...")
    files, mem = src.listing(), memory(src.id)
    new = {r: v for r, v in files.items() if tuple(mem.get(r, [0, 0])[:2]) != tuple(v)}
    say(f"The phone has {count(len(files), 'file')} in its photo, download, document, music and chat folders; "
        f"{len(new):,} are new since the last import ({size(sum(n for n, _ in new.values()))}).")
    if new and confirm(f"\nCopy them into {stage}?\nNothing on the phone is changed."):
        with Lock(), Stoppable():
            fetch(src, new, os.path.join(stage, time.strftime("%Y-%m-%d %H.%M.%S")), mem)
        memory(src.id, mem)
    if isdir(stage) and has_files(stage):
        res = organize(cfg, "import", stage, kind="phone")
        if res:
            where = {key(i["src"]): i.get("kept") or i["dst"] for i in res["moved"]}
            for v in mem.values():
                v[3] = where.get(key(v[3]), v[3])
            memory(src.id, mem)
            for d in reversed(tree_of(stage)[0]):  # tidy's own staging folders, now empty
                try:
                    os.rmdir(L(d))
                except OSError:
                    pass
    free_up(cfg, src, mem)


def free_up(cfg, src, mem):
    """Optional: delete from the phone only files whose library copies are verified, after DELETE FROM PHONE."""
    now = src.listing()
    ok = [r for r, v in mem.items() if now.get(r) == tuple(v[:2]) and v[2] and v[3] and exists(v[3]) and not
          inside(v[3], os.path.join(cfg["library"], STAGING)) and not NEVER_ON_PHONE.search(r) and
          any(r.startswith(d + "/") for d in PHONE_DIRS)]
    if not ok:
        return
    say(f"\n{count(len(ok), 'file')} ({size(sum(mem[r][0] for r in ok))}) on the phone are safely in your library.")
    if not src.can_hash:
        return warn("This phone can't double-check its files (no sha256sum), so tidy won't delete anything from it.")
    if not yes_no("Free up space on the phone by deleting those files from the phone?"):
        return
    say("Double-checking every copy first, on the laptop and on the phone...")
    prog, lib_ok = Progress("Checking", len(ok)), []
    for r in ok:
        prog.step()
        try:
            if sha(mem[r][3]) == mem[r][2]:
                lib_ok.append(r)
        except OSError:
            pass
    prog.end()
    ph = src.hashes(lib_ok)
    sure = [r for r in lib_ok if ph.get(r) == mem[r][2]]
    total = sum(mem[r][0] for r in sure)
    if not sure or not confirm(f"\nThis deletes {count(len(sure), 'file')} ({size(total)}) FROM THE PHONE. Your "
                               "library keeps its checked copies. WhatsApp's database and app folders are never "
                               "touched.", "DELETE FROM PHONE"):
        return say("OK - nothing was deleted from the phone.")
    J = Journal("phone-delete", phone=src.id)
    for r in sure:
        J.w(t="deleted", phone=r, copy=mem[r][3], sha=mem[r][2])
    J.sync()
    src.delete(sure)
    left = src.listing()
    gone = [r for r in sure if r not in left]
    J.close(status="complete", deleted=len(gone))
    good(f"Freed {size(sum(mem[r][0] for r in gone))} on the phone ({count(len(gone), 'file')} deleted). "
         "The gallery app may take a little while to notice.")


def import_folder(cfg, folder=None):
    folder = clean_path(folder or ask("Which folder? Paste its path"))
    why = bad_folder(folder) or ("it's inside your library" if inside(folder, cfg["library"]) else "") or \
        ("your library is inside it" if inside(cfg["library"], folder) else "")
    return warn(f"Can't use that: {why}.") if why else organize(cfg, "import", folder)


# ================================================================ 12. ORGANIZE, WATCH, MENU
def organize(cfg, mode="organize", folder=None, kind=None):
    say("\nLooking at your files... (this changes nothing)")
    plan = make_plan(cfg, mode, folder)
    save_plan(plan)
    rep = write_report(plan)
    summary(plan)
    say(f"\nFull report: {rep}")
    show(rep)
    if not plan["items"]:
        return good("Nothing needs moving - everything is tidy!")
    if not confirm("\nGo ahead and move everything as shown in the plan and the report?"):
        return say("OK - nothing was changed.")
    with Lock():
        res = apply_plan(plan, kind)
    write_report(plan, res)
    return res


def scan_only(cfg):
    plan = make_plan(cfg)
    save_plan(plan)
    rep = write_report(plan)
    summary(plan)
    say(f"\nFull report: {rep}\nNothing was changed. Choose 'Organize my files' to carry it out.")
    show(rep)


def autostart_help():
    py, log = sys.executable, os.path.join(DATA, "watch.log")
    if WIN:
        pyw = os.path.join(os.path.dirname(py), "pythonw.exe")
        return f"""To start watch mode automatically when you log in (Windows Task Scheduler):
 1. Press the Windows key, type Task Scheduler, open it and click "Create Basic Task...".
 2. Name it tidy watch > Trigger "When I log on" > Action "Start a program".
 3. Program/script:  {pyw}
    Add arguments:   "{SCRIPT}" watch --yes
 4. Click Finish. (Or type this in Command Prompt:
    schtasks /Create /SC ONLOGON /TN "tidy watch" /TR "\\"{pyw}\\" \\"{SCRIPT}\\" watch --yes" )"""
    if MAC:
        pl, e = os.path.expanduser("~/Library/LaunchAgents/com.tidy.watch.plist"), html.escape
        return f"""To start watch mode automatically when you log in (macOS launchd):
 1. Save this text as {pl}
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>Label</key><string>com.tidy.watch</string>
<key>ProgramArguments</key><array><string>{e(py)}</string><string>{e(SCRIPT)}</string><string>watch</string>
<string>--yes</string></array><key>RunAtLoad</key><true/><key>StandardOutPath</key><string>{e(log)}</string>
<key>StandardErrorPath</key><string>{e(log)}</string></dict></plist>
 2. In Terminal run:  launchctl load -w "{pl}"
 3. If nothing gets sorted: System Settings > Privacy & Security > Full Disk Access > + and add {py}"""
    return f"""To start watch mode automatically (Linux), use either:
 cron:    run  crontab -e  and add this line:
          @reboot sleep 60 && "{py}" "{SCRIPT}" watch --yes >> "{log}" 2>&1
 systemd: save this as ~/.config/systemd/user/tidy-watch.service
          [Unit]
          Description=tidy watch
          [Service]
          ExecStart="{py}" "{SCRIPT}" watch --yes
          Restart=on-failure
          [Install]
          WantedBy=default.target
          then run:  systemctl --user enable --now tidy-watch.service"""


def watch(cfg, every=None, assume=False):
    every, roots = float(every or cfg["watch_every_minutes"]), roots_for(cfg, "watch", None)
    if not roots:
        return bad("No messy folders are set up yet (see Change settings).")
    title(f"Watch mode: every {every:g} minutes, loose files in {roots[0][0]} that haven't changed for "
          f"{cfg['min_age_minutes']} minutes get sorted, with the same rules and journal (so undo works).")
    if not assume:
        say("\n" + autostart_help())
        if not confirm("\nStart watching now? While it runs, tidy sorts new files without asking each time."):
            return None
    say("Watching... press Ctrl+C to stop.")
    try:
        while True:
            try:
                with Lock(ask_user=False):
                    plan = make_plan(cfg, "watch", quiet=True)
                    if plan["items"]:
                        save_plan(plan)
                        res = apply_plan(plan, "watch", quiet=True)
                        write_report(plan, res)
                        say(f"{stamp()}  sorted {count(len(res['moved']), 'file')}" +
                            (f", {len(res['failed'])} left for next time" if res["failed"] else ""))
            except Busy:
                pass
            time.sleep(every * 60)
    except KeyboardInterrupt:
        say("\nStopped watching.")


def menu(cfg):
    while True:
        say(f"\nLibrary: {cfg['library']}", "2")
        i = pick("What would you like to do?", [
            "Scan & report (changes nothing)", "Organize my files", "Find duplicates",
            "Import from my phone (USB cable)", "Import from a folder (e.g. photos copied from a phone)",
            "Undo a previous run", "Re-sort the library (after changing settings)",
            "Watch Downloads (sort new files automatically)", "Change settings", "Run the self-test"], back="Quit")
        if i is None:
            return say("Bye!")
        try:
            if i == 8:
                cfg = settings(cfg)
            else:
                [scan_only, organize, lambda c: organize(c, "dupes"), phone, import_folder, lambda c: undo_menu(),
                 lambda c: organize(c, "resort"), watch, None, lambda c: selftest()][i](cfg)
        except KeyboardInterrupt:
            warn("\nCancelled (tidy only stops between files, so nothing is half-done).")
        except Busy:
            bad("Another tidy is busy right now - try again when it has finished.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tidy.py", description="A careful file organizer. Run it with no command "
                                 "for the friendly menu. Nothing is deleted, and every run can be undone.")
    sp = ap.add_subparsers(dest="cmd", metavar="command")
    for name, text in (("scan", "look at everything and open the HTML report (changes nothing)"),
                       ("plan", "make a plan and list it here (changes nothing)"),
                       ("apply", "carry out the latest plan (asks you to type YES)"),
                       ("phone", "import from a phone plugged in by USB"),
                       ("dupes", "move duplicates to _Review/Duplicates"), ("report", "open the latest report"),
                       ("resort", "re-sort the library with the current rules"), ("help", "show this help")):
        sp.add_parser(name, help=text)
    p = sp.add_parser("undo", help="undo the latest run, or one you pick")
    p.add_argument("--run", help="id of the run to undo")
    p = sp.add_parser("watch", help="sort new files in Downloads every few minutes")
    p.add_argument("--every", type=float, help="minutes between checks")
    p.add_argument("--yes", action="store_true", help="don't ask first (for starting at login)")
    p = sp.add_parser("import", help="sort a folder, e.g. photos copied from a phone")
    p.add_argument("folder")
    p = sp.add_parser("selftest", help="test tidy on a throw-away folder")
    p.add_argument("--keep", action="store_true", help="keep the test folder afterwards")
    a = ap.parse_args(argv)
    if a.cmd == "help":
        return ap.print_help()
    if a.cmd == "selftest":
        return 0 if selftest(a.keep) else 1
    cfg = load_config()
    if not cfg:
        if not sys.stdin.isatty():
            return bad("tidy isn't set up yet: run  python tidy.py  once and answer a few questions.") or 1
        cfg = setup()
    if not a.cmd:
        return menu(cfg)
    if a.cmd == "plan":
        plan = make_plan(cfg)
        save_plan(plan)
        say(f"\nFull report: {write_report(plan)}")
        for i in plan["items"][:300]:
            say(f"{i['src']}\n    -> {i['dst']}\n       ({i['why']})")
        if len(plan["items"]) > 300:
            say(f"...and {len(plan['items']) - 300:,} more (see the report).")
        summary(plan)
        say("\nRun  tidy.py apply  to carry out this plan.")
    elif a.cmd == "apply":
        plan = last_plan()
        if not plan:
            return bad("There's no plan yet: run  tidy.py plan  first.") or 1
        summary(plan)
        if time.time() - time.mktime(time.strptime(plan["made"], "%Y-%m-%d %H:%M:%S")) > 86400:
            warn("This plan is more than a day old. tidy re-checks every file and skips anything that changed.")
        if not confirm("\nCarry out this plan?"):
            return say("OK - nothing was changed.")
        with Lock():
            write_report(plan, apply_plan(plan))
    elif a.cmd == "report":
        d = os.path.join(DATA, "reports")
        reps = sorted(os.listdir(d), key=lambda n: os.path.getmtime(os.path.join(d, n))) if os.path.isdir(d) else []
        if not reps:
            return say("No report yet: run  tidy.py scan  first.")
        say(os.path.join(d, reps[-1]))
        show(os.path.join(d, reps[-1]))
    else:
        {"scan": scan_only, "phone": phone, "dupes": lambda c: organize(c, "dupes"),
         "resort": lambda c: organize(c, "resort"), "import": lambda c: import_folder(c, a.folder),
         "undo": lambda c: undo_menu(a.run), "watch": lambda c: watch(c, a.every, a.yes)}[a.cmd](cfg)
    return 0


# ================================================================ 13. SELF-TEST
TINY_JPEG = ("/9sAQwAQCwwODAoQDg0OEhEQExgoGhgWFhgxIyUdKDozPTw5Mzg3QEhcTkBEV0U3OFBtUVdfYmdoZz5NcXlwZHhcZWdj/8AACwgAAQA"
             "BAQERAP/EABQAAQAAAAAAAAAAAAAAAAAAAAD/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAA/AD//2Q==")


def exif_jpeg(when):
    """A tiny, real JPEG whose EXIF says it was taken at `when` ('YYYY:MM:DD HH:MM:SS')."""
    t = b"II*\0" + struct.pack("<IHHHII", 8, 1, 0x8769, 4, 1, 26) + b"\0" * 4 + \
        struct.pack("<HHHII", 1, 0x9003, 2, 20, 44) + b"\0" * 4 + when.encode() + b"\0"
    app1 = b"Exif\0\0" + t
    return b"\xff\xd8\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + base64.b64decode(TINY_JPEG)


def selftest(keep=False):
    """Builds a messy throw-away folder, then plan -> apply -> undo (three ways), and checks nothing is lost."""
    global DATA
    root, saved, results = tempfile.mkdtemp(prefix="tidy-selftest-"), DATA, []
    DATA, H = os.path.join(root, "tidy_data"), os.path.join(root, "home")
    lib = os.path.join(H, "Organized")

    def check(name, ok, detail=""):
        results.append(bool(ok))
        say(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok or not detail else f"\n        {detail}"),
            "32" if ok else "31")
    title(f"Self-test in {root}")
    try:
        old = time.time() - 40 * 86400
        ym = time.strftime("%Y/%Y-%m", time.localtime(old))
        long = "A very long file name that goes on " * 6 + "and on.pdf"
        F = [  # (where it starts, content, where it must end up in the library - or None if it must not move)
            ("Downloads/Invoice March 2024.pdf", b"invoice", "Documents/Money/Invoice March 2024.pdf"),
            ("Downloads/syntax guide.pdf", b"syntax", "Documents/Manuals & Guides/syntax guide.pdf"),
            ("Downloads/billboard photo.pdf", b"billboard", "Documents/Other documents/PDFs/billboard photo.pdf"),
            ("Downloads/Passport scan.pdf", b"passport", "Documents/IDs & Certificates/Passport scan.pdf"),
            ("Downloads/boarding pass.pdf", b"boarding", "Documents/Travel & Tickets/boarding pass.pdf"),
            ("Downloads/My Resume 2024.docx", b"resume", "Documents/Resumes & Applications/My Resume 2024.docx"),
            ("Desktop/report.pdf", b"report one", "Documents/Work/report.pdf"),
            ("Downloads/report.pdf", b"report two", "Documents/Work/report (2).pdf"),
            ("Downloads/DSC_0001.JPG", exif_jpeg("2019:07:04 15:30:45"), "Photos/2019/2019-07/DSC_0001.JPG"),
            ("Downloads/IMG_20240312_101112.jpg", b"camera", "Photos/2024/2024-03/IMG_20240312_101112.jpg"),
            ("Desktop/Screenshot 2024-03-12 at 10.11.12.png", b"shot",
             "Screenshots/2024/Screenshot 2024-03-12 at 10.11.12.png"),
            ("Downloads/WhatsApp Image 2024-03-12 at 10.11.12.jpeg", b"wa image",
             "WhatsApp & Chats/Images/WhatsApp Image 2024-03-12 at 10.11.12.jpeg"),
            ("Downloads/VID-20240312-WA0001.mp4", b"wa video", "WhatsApp & Chats/Videos/VID-20240312-WA0001.mp4"),
            ("Downloads/PXL_20230105_080910123.mp4", b"pixel video", "Videos/2023/PXL_20230105_080910123.mp4"),
            ("Downloads/IMG_1234.HEIC", b"live photo", f"Photos/{ym}/IMG_1234.HEIC"),
            ("Downloads/IMG_1234.MOV", b"live photo video", f"Photos/{ym}/IMG_1234.MOV"),
            ("Downloads/Recording 12.m4a", b"voice", "Voice notes/Recording 12.m4a"),
            ("Downloads/song.mp3", b"music", "Music/song.mp3"),
            ("Downloads/book.epub", b"book", "E-books/book.epub"),
            ("Downloads/photos.zip", b"zip", "Archives/photos.zip"),
            ("Downloads/script.py", b"print(1)", "Code/script.py"),
            ("Downloads/logo.psd", b"psd", "Design files/logo.psd"),
            ("Downloads/setup.exe", b"MZ", "_Review/Installers/setup.exe"),
            ("Downloads/empty.txt", b"", "_Review/Junk/empty.txt"),
            ("Downloads/mystery.xyz", b"?", "_Review/Unknown/mystery.xyz"),
            ("Downloads/Überweisung März 日本語 ✓.pdf", b"unicode", "Documents/Other documents/PDFs/"
                                                                "Überweisung März 日本語 ✓.pdf"),
            ("Downloads/" + long, b"long name", "Documents/Other documents/PDFs/" + long),
            ("Desktop/holiday (1).jpg", b"same photo", f"Photos/{ym}/holiday (1).jpg"),
            ("Downloads/holiday.jpg", b"same photo", "_Review/Duplicates/holiday.jpg"),
            ("Organized/Documents/Money/bank statement.pdf", b"statement", "Documents/Money/bank statement.pdf"),
            ("Downloads/bank statement.pdf", b"statement", "_Review/Duplicates/bank statement.pdf"),
            ("Downloads/notes.txt", b"aaaa", "Documents/Study/notes.txt"),
            ("Desktop/notes (1).txt", b"bbbb", "Documents/Study/notes (1).txt"),
            ("Documents/Untitled folder/lecture 5.pdf", b"lecture", "Documents/Study/lecture 5.pdf"),
            ("Documents/Tax 2023/form 16.pdf", b"form", "Documents/Money/Tax 2023/form 16.pdf"),
            ("Documents/Tax 2023/receipts.xlsx", b"sheet", "Documents/Money/Tax 2023/receipts.xlsx"),
            ("Documents/Italy trip 2024/IMG_20240601_101010.jpg", b"italy 1",
             "Photos/2024/Italy trip 2024/IMG_20240601_101010.jpg"),
            ("Documents/Italy trip 2024/IMG_20240602_111111.jpg", b"italy 2",
             "Photos/2024/Italy trip 2024/IMG_20240602_111111.jpg"),
            ("Documents/Italy trip 2024/plan.txt", b"plan", "Photos/2024/Italy trip 2024/plan.txt"),
            ("Documents/myapp/.git/config", b"git", None), ("Documents/myapp/main.py", b"code", None),
            ("Downloads/movie.mp4.crdownload", b"partial", None), ("Downloads/fresh.pdf", b"fresh", None),
            ("Downloads/.hidden.txt", b"hidden", None), ("Downloads/Some folder/inside.txt", b"inside", None),
        ]
        for p, data, _ in F:
            full = os.path.join(H, *p.split("/"))
            mkdirs(os.path.dirname(full))
            with open(L(full), "wb") as f:
                f.write(data)
            os.utime(L(full), (old, old))
        os.utime(L(os.path.join(H, "Downloads", "fresh.pdf")), None)  # changed just now
        os.chmod(L(os.path.join(H, "Downloads", "Invoice March 2024.pdf")), stat.S_IREAD)  # read-only
        mkdirs(os.path.join(H, "Documents", "New folder"))
        cfg = defaults()
        cfg.update(library=lib, sources=[{"path": os.path.join(H, n), "subfolders": n == "Documents"}
                                         for n in ("Downloads", "Desktop", "Documents")])

        def state():
            dirs, files = tree_of(H)
            return ({os.path.relpath(f, H): (sha(f), lstat(f).st_mtime_ns) for f in files
                     if not os.path.basename(f).startswith("duplicates ")}, {os.path.relpath(d, H) for d in dirs})

        def undo(res): undo_run(read_run(os.path.join(DATA, "runs", res["run"] + ".jsonl")), quiet=True)

        def same_hashes(a, b): return sorted(v[0] for v in a[0].values()) == sorted(v[0] for v in b[0].values())
        s0 = state()
        plan = make_plan(cfg, quiet=True)
        check("Planning changed nothing on disk", state() == s0)
        res = apply_plan(plan, quiet=True)
        s1 = state()
        check("Nothing lost or changed after organizing (the same set of SHA-256 hashes)", same_hashes(s1, s0))
        wrong = [e for p, c, e in F if e and s1[0].get(os.path.join("Organized", *e.split("/")), ("",))[0] !=
                 hashlib.sha256(c).hexdigest()]
        check("Every sample file is in the right folder (dates from EXIF, names and file dates; categories)",
              not wrong, "wrong or missing: " + "; ".join(wrong[:5]))
        stayed = [p for p, c, e in F if e is None and s1[0].get(os.path.join(*p.split("/"))) !=
                  s0[0].get(os.path.join(*p.split("/")))]
        check("Project folder, unfinished download, fresh file, hidden file and Downloads sub-folder untouched",
              not stayed, ", ".join(stayed))
        w = os.path.join(lib, "Documents", "Work")
        check("A name collision got ' (2)' instead of overwriting",
              exists(os.path.join(w, "report.pdf")) and exists(os.path.join(w, "report (2).pdf")))
        dd = os.path.join(lib, "_Review", "Duplicates")
        check("Duplicates went to _Review/Duplicates, with a CSV of where they came from and what was kept",
              isdir(dd) and any(n.endswith(".csv") for n in os.listdir(L(dd))))
        check("'Probably the same' files were listed, not treated as duplicates",
              any("notes" in a and "notes" in b for a, b, _ in plan["maybe"]))
        check("Empty folders, and folders left empty, went to _Review/Empty folders",
              all(isdir(os.path.join(lib, "_Review", "Empty folders", n)) for n in ("New folder", "Untitled folder")))
        undo(res)
        check("Undo put every file back exactly where it was (same content, same dates, no new folders)",
              state() == s0)
        res = apply_plan(make_plan(cfg, quiet=True), force_copy=True, quiet=True)
        check("Other-drive mode (copy, verify SHA-256, remove original) kept every file and its date",
              res["moved"] and not res["failed"] and same_hashes(state(), s0) and all(
                  lstat(i["dst"]).st_mtime_ns == s0[0][os.path.relpath(i["src"], H)][1]
                  for i in res["moved"] if i["kind"] == "file"))
        undo(res)
        check("...and undoing it restored everything", state() == s0)
        plan = make_plan(cfg, quiet=True)
        res = apply_plan(plan, stop_after=7, quiet=True)
        check("A run stopped half-way (like Ctrl+C) loses nothing", res["stopped"] and 0 < len(res["moved"]) <
              len(plan["items"]) and same_hashes(state(), s0))
        undo(res)
        check("...and can be undone exactly", state() == s0)
        a, b = os.path.join(H, "Downloads", "song.mp3"), os.path.join(lib, "Music", "song.mp3")
        J = Journal("organize", library=lib)
        J.begin(op="move", src=a, dst=b, how="copy", kind="file", size=5, mtime=old)
        J.sync()
        J.f.close()
        mkdirs(os.path.dirname(b))
        with open(L(b + ".tidy-part"), "wb") as f:
            f.write(b"mus")  # ...and then the power went off in the middle of the copy
        recover(quiet=True)
        os.rmdir(L(os.path.dirname(b)))
        check("After a simulated power cut, recovery removes the half-made copy and the original is safe",
              state() == s0 and read_run(J.path)["end"])
        ph = os.path.join(root, "phone")
        for p, c in (("DCIM/Camera/IMG_20240101_120000.jpg", b"phone photo"),
                     ("Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images/IMG-20240102-WA0001.jpg", b"wa"),
                     ("WhatsApp/Databases/msgstore.db.crypt14", b"private")):
            full = os.path.join(ph, *p.split("/"))
            mkdirs(os.path.dirname(full))
            with open(L(full), "wb") as f:
                f.write(c)
            os.utime(L(full), (old, old))
        src, mem = Folder(ph, PHONE_DIRS), {}
        before = src.listing()
        fetch(src, before, os.path.join(lib, STAGING, "test"), mem, quiet=True)
        res = apply_plan(make_plan(cfg, "import", os.path.join(lib, STAGING), quiet=True), "phone", quiet=True)
        again = {r: v for r, v in src.listing().items() if tuple(mem.get(r, [0, 0])[:2]) != tuple(v)}
        check("Phone import copies (never moves), sorts, skips WhatsApp's database and remembers what it copied",
              exists(os.path.join(lib, "Photos", "2024", "2024-01", "IMG_20240101_120000.jpg")) and exists(
                  os.path.join(lib, "WhatsApp & Chats", "Images", "IMG-20240102-WA0001.jpg")) and len(before) == 2
              and not again and len(tree_of(ph)[1]) == 3)
    except Exception as e:
        import traceback
        check(f"The self-test itself crashed: {e!r}", False, traceback.format_exc())
    finally:
        DATA = saved
        if keep:
            say(f"Test folder kept: {root}")
        else:
            shutil.rmtree(L(root), onerror=lambda f, p, _: (os.chmod(p, stat.S_IWRITE), f(p)))
    n = sum(results)
    (good if n == len(results) else bad)(f"\n{n} of {len(results)} checks passed" +
                                         (" - tidy is working correctly." if n == len(results) else "."))
    return n == len(results)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        say("\nStopped. (tidy only ever stops between files, so nothing is half-done.)")
        sys.exit(130)
    except Busy:
        bad("Another tidy is busy right now - try again when it has finished.")
        sys.exit(1)
    except Exception:
        import traceback
        os.makedirs(DATA, exist_ok=True)
        log = os.path.join(DATA, "error.log")
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"\n--- {stamp()}\n{traceback.format_exc()}")
        bad(f"Sorry - something unexpected went wrong. The details are in {log}")
        say("Your files are safe: every move is journaled first, and 'Undo' in the menu puts runs back.")
        sys.exit(1)
