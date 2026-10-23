"""
Per-acquisition record of hardware problems, and the rule that stops a timelapse when they persist.

While an acquisition runs, a CSV file (acquisition_record.csv) is written in the acquisition folder.
It has one row for every region imaged at every timepoint, one summary row per timepoint, and one row
for every hardware problem:

- hardware_failure_recovered: a wrapped hardware call (see hardware/exceptions_handle.py) failed and
  then succeeded when retried. This includes stage position mismatches that were fixed by re-sending
  the move.
- hardware_failure: a wrapped hardware call failed twice. This normally ends the acquisition.
- camera_timeout: a video or z-stack received no images for too long and was retried.

A timepoint with any hardware problem is "suspect". After MAX_CONSECUTIVE_SUSPECT_TIMEPOINTS suspect
timepoints in a row, the acquisition is aborted (TooManySuspectTimepointsException), since images taken
while hardware is misbehaving (e.g. a stage not at the sample position) are likely to be bad.

Only events from the acquisition's own thread are recorded, so problems caused by clicking GUI
controls during an acquisition don't count. Rows are flushed immediately, so the file is complete up
to the moment of a crash. Analysis code can use it to exclude suspect timepoints/regions.

Usage (all functions are no-ops when no acquisition record is active):
    begin(acq_directory)      # at the start of an acquisition, on the acquisition thread
    start_timepoint() / end_timepoint()
    start_region() / end_region()
    report(event, detail)     # called by handle_exception and imaging sequences
    finish(status)            # at the end of the acquisition (always)
"""

import csv
import datetime
import logging
import os
import threading

from LS_Pycro_App.utils.exceptions import TooManySuspectTimepointsException

FILE_NAME = "acquisition_record.csv"
MAX_CONSECUTIVE_SUSPECT_TIMEPOINTS = 2
_COLUMNS = ["time", "timepoint", "fish", "region", "event", "detail"]

_logger = logging.getLogger(__name__)
_lock = threading.Lock()
_active = None


class _AcquisitionRecord():
    def __init__(self, acq_directory):
        self._acq_directory = acq_directory
        self._thread_id = threading.get_ident()
        os.makedirs(acq_directory.root, exist_ok=True)
        self.path = f"{acq_directory.root}/{FILE_NAME}"
        self._file = open(self.path, "w", newline="")
        self._writer = csv.writer(self._file)
        self._writer.writerow(_COLUMNS)
        self._file.flush()
        self._timepoint_problems = 0
        self._region_problems = 0
        self._consecutive_suspect = 0

    def is_recording_thread(self) -> bool:
        return threading.get_ident() == self._thread_id

    def write(self, event: str, detail: str = ""):
        time_point, fish, region = self._acq_directory.get_labels()
        row = [datetime.datetime.now().isoformat(timespec="seconds"), time_point, fish, region, event, detail]
        with _lock:
            self._writer.writerow(row)
            self._file.flush()

    def report(self, event: str, detail: str):
        self._timepoint_problems += 1
        self._region_problems += 1
        self.write(event, detail)

    def start_timepoint(self):
        self._timepoint_problems = 0

    def end_timepoint(self):
        if self._timepoint_problems:
            self._consecutive_suspect += 1
            self.write("timepoint_suspect", f"{self._timepoint_problems} hardware problem(s)")
        else:
            self._consecutive_suspect = 0
            self.write("timepoint_ok")
        if self._consecutive_suspect >= MAX_CONSECUTIVE_SUSPECT_TIMEPOINTS:
            message = (f"{self._consecutive_suspect} consecutive timepoints had hardware problems; "
                       f"aborting acquisition. See {self.path}")
            self.write("acquisition_aborting", message)
            _logger.error(message)
            raise TooManySuspectTimepointsException(message)

    def start_region(self):
        self._region_problems = 0

    def end_region(self):
        if self._region_problems:
            self.write("region_suspect", f"{self._region_problems} hardware problem(s)")
        else:
            self.write("region_ok")

    def close(self, status: str):
        self.write("acquisition_end", status)
        self._file.close()


def _get_active():
    record = _active
    if record is not None and record.is_recording_thread():
        return record
    return None


def begin(acq_directory):
    """
    Starts a new acquisition record in acq_directory.root. Must be called on the acquisition thread.
    Never raises: if the file can't be created, the acquisition runs without a record.
    """
    global _active
    try:
        _active = _AcquisitionRecord(acq_directory)
        _active.write("acquisition_start")
        _logger.info(f"Acquisition record started: {_active.path}")
    except Exception:
        _active = None
        _logger.exception("Could not create acquisition record; continuing without it")


def finish(status: str):
    """
    Writes the final status and closes the record.
    """
    global _active
    record = _get_active()
    if record is None:
        return
    try:
        record.close(status)
    except Exception:
        _logger.exception("Could not close acquisition record")
    finally:
        _active = None


def report(event: str, detail: str):
    """
    Records a hardware problem against the current timepoint/fish/region. Ignored when called from a
    thread other than the acquisition thread (e.g. the GUI), or when no acquisition is running.
    """
    record = _get_active()
    if record is None:
        return
    try:
        record.report(event, detail)
    except Exception:
        _logger.exception("Could not write to acquisition record")


def start_timepoint():
    record = _get_active()
    if record:
        record.start_timepoint()


def end_timepoint():
    """
    Writes the timepoint summary. Raises TooManySuspectTimepointsException after
    MAX_CONSECUTIVE_SUSPECT_TIMEPOINTS suspect timepoints in a row.
    """
    record = _get_active()
    if record:
        try:
            record.end_timepoint()
        except TooManySuspectTimepointsException:
            raise
        except Exception:
            _logger.exception("Could not write to acquisition record")


def start_region():
    record = _get_active()
    if record:
        record.start_region()


def end_region():
    record = _get_active()
    if record:
        try:
            record.end_region()
        except Exception:
            _logger.exception("Could not write to acquisition record")
