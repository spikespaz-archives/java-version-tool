from pathlib import Path
import itertools
import requests
import platform
import re

from PyQt5.QtCore import QThread, QProcess, QUrl
from PyQt5 import QtCore
from PyQt5.Qt import QDesktopServices


# Wraps a function and returns None when specified exceptions are thrown.
def wrap_throwable(func, *exc):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exc:
            return None

    return wrapper


# Generator that yields the cartesian products of a polymorphic dictionary.
def product_dicts(**kwargs):
    keys = kwargs.keys()
    values = kwargs.values()

    for instance in itertools.product(*values):
        yield dict(zip(keys, instance))


# Opens the system's file manager on a file, or open a directory.
# On Windows and Mac, the explorer window will open with the specified file selected,
# much like Chrome's "Show in folder" behavior for downloads.
def open_explorer(path):
    path = Path(path).resolve()
    system = platform.system().lower()

    if system == "windows":
        if path.is_dir():
            # The path is a directory.
            QProcess.startDetached(f'explorer.exe "{path}"')
        else:
            # THe path is a file, open the parent directory and select the file in the view.
            QProcess.startDetached(f'explorer.exe /select,"{path}"')
    elif system == "darwin":
        # Apple's "open" command handles "show in folder" with the "--reveal" flag.
        QProcess.startDetached(f'open -R "{path}"')
    else:
        # The platform is not Windows or Mac, must be Linux?
        # Open the directory with generic handling provided by Qt.

        if path.is_dir():
            QDesktopServices.openUrl(QUrl(path.as_uri()))
        else:
            # If the path provided is a file, Qt needs to open the parent directory.
            QDesktopServices.openUrl(QUrl(path.parent.as_uri()))


class BackgroundThread(QThread):
    def __init__(self, destination, *args, **kwargs):
        super().__init__(*args, **kwargs)

        destination.append(self)

    def __call__(self, function):
        self._target = function

        def wrapper(*args, **kwargs):
            self._args = args
            self._kwargs = kwargs

            self.start()

        return wrapper

    def __del__(self):
        self.wait()

    def run(self):
        self._target(*self._args, **self._kwargs)


class DownloaderThread(QThread):
    filenameFound = QtCore.pyqtSignal(str)
    filesizeFound = QtCore.pyqtSignal(int)
    bytesChanged = QtCore.pyqtSignal(int)
    chunkWritten = QtCore.pyqtSignal(int)
    beginSendRequest = QtCore.pyqtSignal()
    endSendRequest = QtCore.pyqtSignal()
    beginDownload = QtCore.pyqtSignal(str)
    endDownload = QtCore.pyqtSignal(str)

    def __init__(self, chunk_size=1024, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.chunk_size = chunk_size
        self.filename = None
        self.filesize = None
        self._url = None
        self._location = None
        self.file_location = None
        self.success = False
        self._stopped = False

    def __del__(self):
        self.wait()

    def __call__(self, url, location="./"):
        self._url = url
        self._location = location

        self.start()

    def stop(self):
        self._stopped = True
        self.success = False
        self.endDownload.emit(str(self.file_location))
        self.exit(0)

    def run(self):
        self._stopped = False
        self.success = False

        self.beginSendRequest.emit()
        request = requests.get(self._url, stream=True)
        self.endSendRequest.emit()

        self.filesize = int(request.headers["content-length"])
        self.filename = re.findall(r"filename=(.+)", request.headers["content-disposition"])[0]

        self.filenameFound.emit(self.filename)
        self.filesizeFound.emit(self.filesize)

        self.file_location = Path(self._location, self.filename).resolve()

        self.beginDownload.emit(str(self.file_location))

        with open(self.file_location, "wb") as file:
            downloaded_bytes = 0

            for count, chunk in enumerate(request.iter_content(chunk_size=self.chunk_size)):
                if self._stopped:
                    return
                elif not chunk:
                    continue

                file.write(chunk)
                downloaded_bytes += len(chunk)

                self.bytesChanged.emit(downloaded_bytes)
                self.chunkWritten.emit(count)

        self.success = True
        self.endDownload.emit(str(self.file_location))
