import os
import urllib.request
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

# ==============================================================================
# CORE APP LOGIC: Helpers & Formatting
# ==============================================================================
CONFIG_FILE = "palm_sync_urls.txt"

def load_saved_urls():
    """Loads previously used URLs from a local text file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return ""

def save_urls(urls_str):
    """Saves the current URLs to a local text file for next time."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        f.write(urls_str.strip())

def clean_for_palm(text):
    """Strips out Emojis and modern unicode so Palm Desktop doesn't crash."""
    return text.encode('ascii', 'ignore').decode('ascii')

def fold_vcal_line(key, value, is_qp=False):
    """Safely wraps long lines to keep them under Palm's 75-character limit."""
    line = f"{key}:{value}"
    if len(line) <= 73: return line + "\n"
        
    folded_lines = []
    if is_qp:
        while len(line) > 72:
            cut_idx = 72
            if line[cut_idx - 1] == '=': cut_idx -= 1
            elif line[cut_idx - 2] == '=': cut_idx -= 2
            folded_lines.append(line[:cut_idx] + "=") 
            line = " " + line[cut_idx:] 
            
        if line.strip(): folded_lines.append(line)
    else:
        while len(line) > 73:
            cut_idx = 73
            folded_lines.append(line[:cut_idx]) 
            line = " " + line[cut_idx:] 
            
        if line.strip(): folded_lines.append(line)
            
    return "\n".join(folded_lines) + "\n"

def get_memory_bank(filepath):
    """Reads an old .VCS file to learn what events you've already imported."""
    fingerprints = set()
    filepath = filepath.strip(' "\'')
    
    if not filepath or not os.path.exists(filepath):
        return fingerprints 
        
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            raw_lines = f.read().splitlines()
    except Exception:
        return fingerprints

    lines = []
    for line in raw_lines:
        if line.startswith(" ") or line.startswith("\t"):
            if lines: lines[-1] += line[1:]
        else:
            lines.append(line)

    in_event = False
    start, summary = "", ""
    for line in lines:
        if line == "BEGIN:VEVENT":
            in_event = True
            start, summary = "", ""
        elif line == "END:VEVENT":
            in_event = False
            if start or summary:
                fingerprints.add(f"{start.strip()}---{summary.strip()}")
        elif in_event:
            if line.startswith("DTSTART:"): start = line.split(":", 1)[1]
            elif line.startswith("SUMMARY:"): summary = line.split(":", 1)[1]

    return fingerprints

def find_latest_vcs_file():
    """Scans the current folder to automatically find the newest .vcs file."""
    vcs_files = [f for f in os.listdir('.') if f.lower().endswith('.vcs')]
    if not vcs_files:
        return ""
    vcs_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return os.path.abspath(vcs_files[0])

# ==============================================================================
# THE ENGINE: Download & Convert
# ==============================================================================
def run_sync(google_urls_str, previous_vcs_path, is_delta):
    """The master function. Supports multiple URLs."""
    
    seen_events = get_memory_bank(previous_vcs_path)
    total_in_memory = len(seen_events)

    now = datetime.now()
    try: cutoff_dt = now.replace(year=now.year - 3)
    except ValueError: cutoff_dt = now.replace(year=now.year - 3, day=28)
    cutoff_yyyymmdd = int(cutoff_dt.strftime("%Y%m%d"))

    urls = [u.strip() for u in google_urls_str.splitlines() if u.strip()]
    raw_lines = []
    
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req)
            raw_lines.extend(response.read().decode('utf-8').splitlines())
        except Exception as e:
            messagebox.showerror("Download Error", f"Could not download from URL:\n{url}\n\nError: {e}")
            return

    out_lines = ["BEGIN:VCALENDAR\n", "PRODID:-//Palm Desktop//EN\n", "VERSION:1.0\n"]
    
    total_events_scanned = 0
    skipped_old = 0
    skipped_duplicates = 0
    new_events_saved = 0
    
    in_timezone = False
    in_event = False
    current_event_raw = []

    for line in raw_lines:
        stripped = line.strip() 
        if not stripped: continue 
        
        if stripped == "BEGIN:VTIMEZONE": in_timezone = True; continue
        if stripped == "END:VTIMEZONE": in_timezone = False; continue
        if in_timezone: continue

        if stripped == "BEGIN:VEVENT":
            in_event = True
            total_events_scanned += 1
            current_event_raw = [] 
            continue
            
        if stripped == "END:VEVENT":
            in_event = False
            event_data = {}
            current_key = None
            
            for ev_line in current_event_raw:
                if ev_line.startswith(" ") or ev_line.startswith("\t"):
                    if current_key: event_data[current_key] += ev_line[1:] 
                else:
                    if ":" not in ev_line: continue
                    key_part, val_part = ev_line.split(":", 1)
                    actual_key = key_part.split(";")[0] 
                    current_key = actual_key
                    if actual_key not in event_data: event_data[actual_key] = val_part
                    else: event_data[actual_key] += val_part
            
            start = event_data.get("DTSTART", "").replace("Z", "")
            if start and "T" not in start: start += "T000000"
            end = event_data.get("DTEND", "").replace("Z", "")
            if end and "T" not in end: end += "T000000"
            
            summary = clean_for_palm(event_data.get("SUMMARY", ""))
            
            skip_event = False
            if start and len(start) >= 8:
                yyyy_mm_dd = start[:8]
                if yyyy_mm_dd.isdigit() and int(yyyy_mm_dd) < cutoff_yyyymmdd:
                    skip_event = True
            if skip_event:
                skipped_old += 1
                continue 
            
            fingerprint = f"{start.strip()}---{summary.strip()}"
            if fingerprint in seen_events:
                skipped_duplicates += 1
                continue
                
            seen_events.add(fingerprint)
            new_events_saved += 1
            
            loc = clean_for_palm(event_data.get("LOCATION", ""))
            desc = clean_for_palm(event_data.get("DESCRIPTION", ""))
            
            loc = loc.replace("\\,", ",").replace("\\;", ";").replace("=", "=3D").replace("\\n", "=0D=0A").replace("\\N", "=0D=0A")
            desc = desc.replace("\\,", ",").replace("\\;", ";").replace("=", "=3D").replace("\\n", "=0D=0A").replace("\\N", "=0D=0A")
            
            notes = []
            if loc: notes.append(f"Location: {loc}")
            if desc: notes.append(desc)
            final_notes = "=0D=0A=0D=0A".join(notes)
            
            final_rrule = ""
            raw_rrule = event_data.get("RRULE", "")
            if raw_rrule:
                parts = raw_rrule.split(";")
                freq, interval, modifiers, end_cond = "D", "1", "", "#0"
                for p in parts:
                    if p.startswith("FREQ="): freq = "D" if p.split("=")[1]=="DAILY" else "W" if p.split("=")[1]=="WEEKLY" else "MD" if p.split("=")[1]=="MONTHLY" else "YM"
                    elif p.startswith("INTERVAL="): interval = p.split("=")[1]
                    elif p.startswith("BYDAY="): modifiers = " " + p.split("=")[1].replace(",", " ")
                    elif p.startswith("BYMONTHDAY=") or p.startswith("BYMONTH="): modifiers = " " + p.split("=")[1]
                    elif p.startswith("COUNT="): end_cond = "#" + p.split("=")[1]
                    elif p.startswith("UNTIL="):
                        end_cond = p.split("=")[1].replace("Z", "")
                        if "T" not in end_cond: end_cond += "T000000"
                final_rrule = f"{freq}{interval}{modifiers} {end_cond}"
            
            out_lines.append("BEGIN:VEVENT\n")
            if start: out_lines.append(fold_vcal_line("DTSTART", start))
            if end: out_lines.append(fold_vcal_line("DTEND", end))
            if summary: out_lines.append(fold_vcal_line("SUMMARY", summary))
            if final_rrule: out_lines.append(fold_vcal_line("RRULE", final_rrule))
            if final_notes: out_lines.append(fold_vcal_line("DESCRIPTION;ENCODING=QUOTED-PRINTABLE", final_notes, is_qp=True))
            
            out_lines.append(fold_vcal_line("CATEGORIES", "Personal"))
            out_lines.append("END:VEVENT\n")

        elif in_event:
            current_event_raw.append(line)

    out_lines.append("END:VCALENDAR\n")

    timestamp = now.strftime("%Y-%m-%d-%H-%M")
    sync_type = "delta" if is_delta else "full"
    output_filename = f"{timestamp}-Palm calendar {sync_type}.vcs"
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

    used_file_msg = os.path.basename(previous_vcs_path.strip(' "\'')) if previous_vcs_path else "None (Memory Bank Empty)"
    
    msg = (
        f"SYNC COMPLETE ({sync_type.upper()})!\n\n"
        f"Previous File Used: {used_file_msg}\n"
        f"Memory Bank (Existing Events): {total_in_memory}\n"
        f"Calendars Downloaded: {len(urls)}\n"
        f"Total Events Scanned: {total_events_scanned}\n"
        f"Trashed (Older than 3 Years): {skipped_old}\n"
        f"Skipped (Already in Memory): {skipped_duplicates}\n\n"
        f"--> BRAND NEW EVENTS SAVED: {new_events_saved}\n\n"
        f"File '{output_filename}' is ready to import!"
    )
    messagebox.showinfo("Success", msg)

# ==============================================================================
# THE GRAPHICAL INTERFACE (GUI)
# ==============================================================================
def start_gui():
    window = tk.Tk()
    window.title("Palm Desktop Sync Tool")
    window.geometry("550x330") 
    window.resizable(False, False)

    tk.Label(window, text="Palm Desktop Sync Tool", font=("Arial", 14, "bold")).pack(pady=(10, 0))
    tk.Label(window, text="Fetch multiple Google Calendars into perfectly formatted .VCS files.").pack(pady=(0, 15))

    url_frame = tk.Frame(window)
    url_frame.pack(fill="x", padx=20, pady=5)
    tk.Label(url_frame, text="Google Calendar Secret URLs (Paste one per line):", anchor="w").pack(fill="x")
    url_text = tk.Text(url_frame, height=4, width=50)
    url_text.pack(fill="x")
    
    # Automatically load the URLs from the save file when the app opens
    saved_urls = load_saved_urls()
    if saved_urls:
        url_text.insert("1.0", saved_urls)

    file_frame = tk.Frame(window)
    file_frame.pack(fill="x", padx=20, pady=10)
    tk.Label(file_frame, text="Previous Palm Sync File (For Delta Syncs):", anchor="w").pack(fill="x")
    
    file_input_frame = tk.Frame(file_frame)
    file_input_frame.pack(fill="x")
    file_entry = tk.Entry(file_input_frame)
    file_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
    
    auto_detected_file = find_latest_vcs_file()
    if auto_detected_file:
        file_entry.insert(0, auto_detected_file)
    
    def browse_file():
        filename = filedialog.askopenfilename(title="Select previous .vcs file", filetypes=[("vCalendar files", "*.vcs"), ("All files", "*.*")])
        if filename:
            file_entry.delete(0, tk.END)
            file_entry.insert(0, filename)
            
    tk.Button(file_input_frame, text="Browse", command=browse_file).pack(side="right")

    def on_sync_click(is_delta):
        urls_str = url_text.get("1.0", tk.END).strip()
        prev_file = file_entry.get().strip()
        
        # Save whatever is in the URL box to the permanent text file!
        if urls_str:
            save_urls(urls_str)
            
        if is_delta:
            if not prev_file:
                prev_file = find_latest_vcs_file()
                if prev_file:
                    file_entry.insert(0, prev_file)
                else:
                    messagebox.showwarning("Missing File", "Delta Sync requires a previous .vcs file to compare against.\n\nPlease generate a Full Export first to create your initial file.")
                    return
        else:
            prev_file = "" 
        
        if not urls_str:
            messagebox.showwarning("Missing Info", "Please enter at least one Google Calendar Secret URL.")
            return
            
        delta_btn.config(state="disabled")
        full_btn.config(state="disabled")
        window.update() 
        
        run_sync(urls_str, prev_file, is_delta)
        
        delta_btn.config(state="normal")
        full_btn.config(state="normal")

    btn_frame = tk.Frame(window)
    btn_frame.pack(pady=10)

    delta_btn = tk.Button(btn_frame, text="Generate Delta Sync", bg="green", fg="white", font=("Arial", 10, "bold"), command=lambda: on_sync_click(True))
    delta_btn.pack(side="left", padx=10)

    full_btn = tk.Button(btn_frame, text="Generate Full Export", bg="#0066cc", fg="white", font=("Arial", 10, "bold"), command=lambda: on_sync_click(False))
    full_btn.pack(side="left", padx=10)

    window.mainloop()

if __name__ == "__main__":
    start_gui()