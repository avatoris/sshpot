import asyncio
import os


class LogTailer:
    """Follows a text file like `tail -f`, handling rotation (inode change)
    and truncation. Starts at EOF by default so a restart doesn't replay a
    log file's entire history."""

    def __init__(self, path: str, poll_interval: float = 1.0, from_end: bool = True):
        self._path = path
        self._poll_interval = poll_interval
        self._from_end = from_end

    async def lines(self):
        inode = None
        offset = 0
        fh = None
        while True:
            try:
                st = os.stat(self._path)
            except FileNotFoundError:
                await asyncio.sleep(self._poll_interval)
                continue

            if fh is None or inode != st.st_ino:
                if fh:
                    fh.close()
                fh = open(self._path, "r", errors="replace")
                inode = st.st_ino
                offset = st.st_size if self._from_end else 0
                fh.seek(offset)
            elif st.st_size < offset:
                fh.seek(0)
                offset = 0

            line = fh.readline()
            if not line:
                await asyncio.sleep(self._poll_interval)
                continue
            if line.endswith("\n"):
                offset = fh.tell()
                yield line.rstrip("\n")
            else:
                # Partial line written so far; wait for the rest.
                fh.seek(offset)
                await asyncio.sleep(self._poll_interval)
