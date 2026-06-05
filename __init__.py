#!/usr/bin/env python
# Xteink CrossPoint device driver for calibre.
#
# Detects any mounted drive that contains a ".crosspoint" folder and treats it
# as a Xteink e-reader. Sends books as plain EPUBs into a top-level "Books"
# folder, named "Title - Author.epub". The on-device ("checkmark") column works
# the same way it does for a Kindle, because this is a normal USB mass-storage
# driver underneath.
#
# Install: calibre -> Preferences -> Plugins -> Load plugin from file -> pick
# this .zip. Then restart calibre and plug in your reader.

import os
import string

from calibre.constants import ismacos, iswindows
from calibre.devices.usbms.driver import USBMS

# The folder CrossPoint creates on the SD card. Its presence is how we decide a
# mounted drive is a Xteink device.
MARKER_DIR = '.crosspoint'

# Where books are written on the device, and the file-naming template.
# {authors} renders in display order (e.g. "Matt Parker"); {author_sort} would
# give "Parker, Matt", which is not what we want.
BOOKS_DIR = 'Books'
NAME_TEMPLATE = '{title} - {authors}'


def _dbg(*args):
    # Routes to calibre's device-debug log (visible via: calibre-debug -g).
    try:
        from calibre.prints import debug_print
        debug_print('XTEINK:', *args)
    except Exception:
        try:
            from calibre import prints
            prints('XTEINK:', *args)
        except Exception:
            pass


def _unescape_mount(path):
    # /proc/mounts escapes space/tab/newline/backslash as octal codes.
    return (path.replace('\\040', ' ')
                .replace('\\011', '\t')
                .replace('\\012', '\n')
                .replace('\\134', '\\'))


def _candidate_roots():
    '''Every mounted volume root that is worth checking for the marker folder.'''
    roots = []
    if iswindows:
        try:
            from ctypes import windll
            bitmask = windll.kernel32.GetLogicalDrives()
            for i, letter in enumerate(string.ascii_uppercase):
                if bitmask & (1 << i):
                    roots.append(letter + ':\\')
        except Exception:
            # Fall back to probing all drive letters if the API call fails.
            for letter in string.ascii_uppercase:
                roots.append(letter + ':\\')
    elif ismacos:
        try:
            for name in os.listdir('/Volumes'):
                roots.append(os.path.join('/Volumes', name))
        except OSError:
            pass
    else:
        # Linux / *BSD: real mounts first, then the usual auto-mount parents.
        try:
            with open('/proc/mounts', 'rb') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        roots.append(_unescape_mount(parts[1].decode('utf-8', 'replace')))
        except OSError:
            pass
        for parent in ('/media', '/run/media', '/mnt'):
            try:
                for name in os.listdir(parent):
                    p = os.path.join(parent, name)
                    if os.path.isdir(p):
                        roots.append(p)
                        # /media/<user>/<label> style
                        try:
                            for sub in os.listdir(p):
                                roots.append(os.path.join(p, sub))
                        except OSError:
                            pass
            except OSError:
                pass
    # De-duplicate while preserving order.
    seen = set()
    out = []
    for r in roots:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _find_xteink_root():
    '''Return the root of the first mounted drive that has a .crosspoint folder.'''
    for root in _candidate_roots():
        try:
            if os.path.isdir(os.path.join(root, MARKER_DIR)):
                return root
        except Exception:
            continue
    return None


class XTEINK(USBMS):

    name = 'Xteink CrossPoint Device Interface'
    gui_name = 'Xteink'
    description = _('Send books to a Xteink (X3/X4) reader running CrossPoint. '
                    'Auto-detects any drive containing a .crosspoint folder.')
    author = 'Community plugin'
    version = (1, 0, 0)
    minimum_calibre_version = (5, 0, 0)
    supported_platforms = ['windows', 'osx', 'linux']

    # We do our own detection by scanning for the .crosspoint marker rather than
    # by USB vendor/product id. This is the calibre-sanctioned way to detect a
    # device by something other than its USB ids.
    MANAGES_DEVICE_PRESENCE = True

    # Formats CrossPoint reads. EPUB first so calibre prefers it.
    FORMATS = ['epub', 'txt']

    # Books live directly in /Books with no per-author subfolders.
    EBOOK_DIR_MAIN = BOOKS_DIR
    SUPPORTS_SUB_DIRS = False
    SUPPORTS_SUB_DIRS_FOR_SCAN = False

    # Do not rewrite metadata into the files; keep them as plain EPUBs.
    CAN_SET_METADATA = []

    # Dummy USB ids (unused because MANAGES_DEVICE_PRESENCE is True), but set so
    # nothing in the base class trips over a bare 0.
    VENDOR_ID = [0x0000]
    PRODUCT_ID = [0x0000]
    BCD = [0x0000]

    # Detection state.
    _xteink_root = None
    _xteink_dev = None

    @classmethod
    def save_template(cls):
        # Force "Title - Author" regardless of any global device template.
        return NAME_TEMPLATE

    # ---- detection ------------------------------------------------------

    def detect_managed_devices(self, devices_on_system, force_refresh=False):
        try:
            root = _find_xteink_root()
        except Exception:
            root = None

        if root is None:
            self._xteink_root = None
            self._xteink_dev = None
            return None

        # Reuse the same device object while the same drive stays mounted, so
        # calibre does not think it is a brand-new device every poll.
        if self._xteink_dev is None or self._xteink_root != root:
            from calibre.devices.interface import FAKE_DEVICE_SERIAL
            from calibre.devices.scanner import USBDevice
            self._xteink_root = root
            # Serial starting with FAKE_DEVICE_SERIAL tells USBMS.open() to use
            # the trailing path as the device root directly.
            self._xteink_dev = USBDevice(
                0x0000, 0x0000, 0x0000, 'Xteink', 'CrossPoint',
                FAKE_DEVICE_SERIAL + root)
            _dbg('detected device at', root)
        return self._xteink_dev

    def debug_managed_device_detection(self, devices_on_system, output):
        from functools import partial
        p = partial(print, file=output)
        root = _find_xteink_root()
        if root:
            p('Found a Xteink device (a "%s" folder) at: %s' % (MARKER_DIR, root))
            p('Books will be written to: %s' % os.path.join(root, BOOKS_DIR))
            return True
        p('No Xteink device found.')
        p('Looked for a "%s" folder at the root of every mounted drive:' % MARKER_DIR)
        for r in _candidate_roots():
            p('   ', r)
        return False

    # ---- lifecycle ------------------------------------------------------

    def post_open_callback(self):
        # USBMS.open() set self._main_prefix from the marker drive. Make sure the
        # Books folder exists so the very first send has somewhere to go.
        if self._main_prefix:
            books_dir = os.path.join(self._main_prefix, self.EBOOK_DIR_MAIN)
            try:
                if not os.path.isdir(books_dir):
                    os.makedirs(books_dir)
            except Exception:
                pass
        _dbg('opened, device root =', self._main_prefix)

    def get_gui_name(self):
        return self.gui_name
