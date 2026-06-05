# Xteink CrossPoint — calibre device plugin

A calibre device driver that recognizes a **Xteink (X3 / X4) e-reader running [CrossPoint](https://github.com/crosspoint-reader/crosspoint-reader) firmware** and lets you send books to it like any mainstream reader — including the "on device" checkmarks in your library.

There are no USB IDs to configure. The plugin identifies the device by looking for the `.crosspoint` folder that CrossPoint creates on the SD card, so it works with any Xteink that runs that firmware.

## Features

- **Zero-config detection.** Any mounted drive that contains a `.crosspoint` folder is treated as your reader. Nothing to set up.
- **Sends plain EPUBs** (and TXT) into a single `Books/` folder, so they don't get mixed in with the device's `screenshots`, crash logs, fonts, and other root-level files.
- **Title-first filenames** — books are saved as `Title - Author.epub` (e.g. `Humble Pi - Matt Parker.epub`), using normal display order rather than calibre's stored "Lastname, Firstname".
- **On-device checkmarks**, the same as a Kindle. calibre tracks what you've already synced and shows it in the library, and that state survives reconnecting.
- **Cross-platform** — Windows, macOS, and Linux.

## Requirements

- calibre 5.0 or newer
- A Xteink X3 / X4 running CrossPoint firmware (anything that creates a `.crosspoint` folder on the SD card)

## Installation

1. Get the plugin zip. Either download it from this repo's Releases, or build it yourself from the source: from the repo folder, run `zip -j XteinkCrossPoint.zip __init__.py` (the zip just needs `__init__.py` at its top level).
2. In calibre, open **Preferences → Plugins → Load plugin from file** and select the zip.
3. Restart calibre.

The plugin will appear under **Device interface plugins**.

## Usage

1. Connect your reader to the computer over USB so its SD card mounts and the `.crosspoint` folder is visible to your OS.
2. calibre detects it automatically and the device icon appears in the toolbar.
3. Select one or more books and click **Send to device**.

Books are copied to `Books/` on the device as `Title - Author.epub`, and the "On Device" column fills in. Reconnect later and calibre still knows what's there.

## Assumptions and design decisions

This plugin is intentionally opinionated and simple. It assumes:

- **A drive is a Xteink if it has a `.crosspoint` folder at its root.** The first mounted drive matching that is used. There is no separate handling for internal storage vs. SD card.
- **Books belong in `Books/`.** The device's root tends to fill up with firmware files (`.crosspoint`, `screenshots`, crash logs, fonts, sleep images), so books are kept in their own folder for easy browsing.
- **`Title - Author` is the right filename order**, because title-first is easier to scan. It uses author display order ("Matt Parker"), not calibre's sort form ("Parker, Matt").
- **The filename template is fixed** (hardcoded as `{title} - {authors}`). The "Save template" field in the device's calibre settings is ignored on purpose, so the output is always predictable.
- **CrossPoint reads EPUB and TXT**, with EPUB preferred. Sending a book that exists only in another format (AZW3, MOBI, PDF, KEPUB, etc.) triggers calibre's normal "convert before sending?" prompt — see Troubleshooting.
- **The EPUB files themselves are left untouched** (the plugin does not rewrite metadata into them). To power the checkmarks, calibre does write two small bookkeeping files to the device root — `metadata.calibre` and `driveinfo.calibre` — which CrossPoint ignores.

## Customizing

If you want different behavior, the three knobs are constants at the top of `__init__.py`:

- `MARKER_DIR` — the folder used to recognize the device (default `.crosspoint`)
- `BOOKS_DIR` — where books are written (default `Books`)
- `NAME_TEMPLATE` — the filename template (default `{title} - {authors}`)

## Troubleshooting

**The device isn't detected.** Use **Preferences → Miscellaneous → Debug device detection** (unplug, then plug in, when prompted), or launch calibre with `calibre-debug -g` and watch the console. The plugin prints whether it found a `.crosspoint` drive, and if not, lists every drive root it checked — which tells you immediately whether the issue is a mount path it didn't see. Also make sure the drive is mounted writable, not read-only.

**calibre asks to "auto convert" a book.** That prompt means the book has no EPUB or TXT copy in your library (commonly AZW3/MOBI from a Kindle workflow, or PDF/KEPUB). Letting it convert is fine — calibre produces an EPUB, sends it, and stores it back in your library, so it won't ask again next time. You can also pre-convert with **Convert books → EPUB** before sending.

## How it works

It subclasses calibre's `USBMS` driver. Detection uses `MANAGES_DEVICE_PRESENCE` to scan mounted volumes for the `.crosspoint` marker, then hands calibre a folder-backed device (via calibre's built-in `FAKE_DEVICE_SERIAL` path) so all the cross-platform mounting, transfer, and metadata caching are handled by calibre itself. Most of the code is just the drive-scanning logic for the three operating systems.

## License

Because it builds on calibre, this plugin is released under the **GNU GPL v3**, the same license as calibre.
