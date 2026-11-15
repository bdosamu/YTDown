import argparse
import contextlib
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from downloader_core import download_album, parse_urls


def send_notification(title, message):
    notifier = shutil.which('notify-send')
    if not notifier:
        print(f"{title}: {message}")
        return

    try:
        subprocess.run([notifier, title, message], check=False)
    except Exception as e:
        print(f"Notification failed: {e}")


def run_cli():
    raw_input = input("Enter YouTube Music URL(s), separated by commas, spaces, or new lines: ").strip()
    output_directory = input("Enter output directory (default: ~/Downloads): ").strip() or os.path.expanduser("~/Downloads")

    urls = parse_urls(raw_input)

    if not urls:
        print("No valid URL entered.")
        send_notification("YouTube Music Downloader", "Nincs érvényes URL.")
    else:
        for url in urls:
            print(f"\n=== Downloading: {url} ===")
            download_album(url, output_directory)
        send_notification("YouTube Music Downloader", "Minden letöltés kész!")


class QueueWriter:
    def __init__(self, output_queue):
        self.output_queue = output_queue

    def write(self, text):
        if text:
            self.output_queue.put(('log', text))

    def flush(self):
        pass

    def isatty(self):
        return False


class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Music Downloader")
        self.root.minsize(560, 500)
        self.output_queue = queue.Queue()
        self.formats = ('flac', 'mp3', 'm4a', 'wav')
        self.ffmpeg_location = None

        main = ttk.Frame(root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)
        main.rowconfigure(6, weight=1)

        ttk.Label(main, text="Download music", font=('TkDefaultFont', 16, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 12)
        )
        ttk.Label(main, text="Paste one or more YouTube Music links").grid(
            row=1, column=0, sticky=tk.W, pady=(0, 5)
        )

        url_frame = ttk.Frame(main)
        url_frame.grid(row=2, column=0, sticky=tk.NSEW, pady=(0, 12))
        url_frame.columnconfigure(0, weight=1)
        url_frame.rowconfigure(0, weight=1)
        self.url_text = tk.Text(url_frame, height=5, wrap=tk.WORD)
        self.url_text.grid(row=0, column=0, sticky=tk.NSEW)
        url_scrollbar = ttk.Scrollbar(url_frame, orient=tk.VERTICAL, command=self.url_text.yview)
        url_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.url_text.configure(yscrollcommand=url_scrollbar.set)

        ttk.Label(main, text="Save to").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        folder_frame = ttk.Frame(main)
        folder_frame.grid(row=4, column=0, sticky=tk.EW, pady=(0, 12))
        folder_frame.columnconfigure(0, weight=1)
        self.folder_var = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        ttk.Entry(folder_frame, textvariable=self.folder_var).grid(
            row=0, column=0, sticky=tk.EW, padx=(0, 8)
        )
        ttk.Button(folder_frame, text="Browse...", command=self.choose_folder).grid(row=0, column=1)

        options = ttk.Frame(main)
        options.grid(row=5, column=0, sticky=tk.EW, pady=(0, 12))
        ttk.Label(options, text="Audio format").pack(side=tk.LEFT, padx=(0, 8))
        self.format_var = tk.StringVar(value='flac')
        ttk.Combobox(
            options,
            textvariable=self.format_var,
            values=self.formats,
            state='readonly',
            width=10,
        ).pack(side=tk.LEFT)

        log_frame = ttk.LabelFrame(main, text="Progress", padding=8)
        log_frame.grid(row=6, column=0, sticky=tk.NSEW, pady=(0, 12))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=tk.NSEW)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main, textvariable=self.status_var).grid(row=7, column=0, sticky=tk.W)
        self.download_button = ttk.Button(main, text="Download", command=self.start_download)
        self.download_button.grid(row=8, column=0, sticky=tk.E, pady=(8, 0))

        self.root.after(100, self.process_queue)

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get() or os.path.expanduser("~"))
        if folder:
            self.folder_var.set(folder)

    def append_log(self, text):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def start_download(self):
        urls = parse_urls(self.url_text.get('1.0', tk.END).strip())
        if not urls:
            messagebox.showerror("Missing links", "Paste at least one valid http(s) link to download.")
            return

        output_directory = self.folder_var.get().strip()
        if not output_directory:
            messagebox.showerror("Missing folder", "Choose where the downloads should be saved.")
            return

        self.download_button.configure(state=tk.DISABLED)
        self.status_var.set("Downloading...")
        worker = threading.Thread(
            target=self.download_in_background,
            args=(urls, output_directory, self.format_var.get(), self.ffmpeg_location),
            daemon=True,
        )
        worker.start()

    def download_in_background(self, urls, output_directory, audio_format, ffmpeg_location=None):
        all_successful = True
        writer = QueueWriter(self.output_queue)
        with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
            try:
                for url in urls:
                    print(f"\n=== Downloading: {url} ===")
                    if not download_album(url, output_directory, audio_format, ffmpeg_location):
                        all_successful = False
            except Exception as error:
                print(f"Download failed: {error}")
                all_successful = False
            finally:
                self.output_queue.put(('complete', all_successful))

    def process_queue(self):
        try:
            while True:
                message_type, content = self.output_queue.get_nowait()
                if message_type == 'log':
                    self.append_log(content)
                else:
                    self.download_button.configure(state=tk.NORMAL)
                    if content:
                        self.status_var.set("All downloads finished.")
                    else:
                        self.status_var.set("Finished with errors. See progress above.")
                    if messagebox.askyesno(
                        "Download more?",
                        "All downloads have finished. Would you like to download more songs?",
                        parent=self.root,
                    ):
                        self.url_text.delete('1.0', tk.END)
                        self.url_text.focus_set()
                        self.status_var.set("Ready for more downloads.")
                    else:
                        self.root.destroy()
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)


def main():
    parser = argparse.ArgumentParser(description="Download YouTube Music tracks and albums.")
    parser.add_argument(
        '--cli',
        action='store_true',
        help="Use the original terminal prompts instead of the desktop interface.",
    )
    args = parser.parse_args()

    if args.cli:
        run_cli()
        return

    root = tk.Tk()
    app = DownloaderApp(root)
    app.ffmpeg_location = bundled_ffmpeg_location()
    root.mainloop()


def bundled_ffmpeg_location():
    if not getattr(sys, 'frozen', False):
        return None

    bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    ffmpeg_dir = os.path.join(bundle_dir, 'ffmpeg')
    ffmpeg_name = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
    ffprobe_name = 'ffprobe.exe' if os.name == 'nt' else 'ffprobe'
    if os.path.isfile(os.path.join(ffmpeg_dir, ffmpeg_name)) and os.path.isfile(
        os.path.join(ffmpeg_dir, ffprobe_name)
    ):
        return ffmpeg_dir
    return None


if __name__ == "__main__":
    main()
