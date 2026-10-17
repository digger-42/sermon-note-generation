# sermon-note-generator

Builds the weekly PCCMI Sermon Notes from Katie Winstanley's
"Sunday Morning Sermon Information" email: a LibreOffice Writer `.odt`, then a
PDF of it for pccmi.org and the weekly email.

## Usage

```
python3 -m sermon_notes.generate email.txt
```

The email can be pasted text (use `-` and paste, then Ctrl-D) or a message
Thunderbird saved as `.eml`. Katie's signature is ignored if it is there.
This writes `/MaresLeg/Church/SermonNotes/<year>/YYYY-MM-DD-sermon-notes.odt`
and `.pdf` for the upcoming Sunday. Options:

- `--date YYYY-MM-DD` sets the Sunday explicitly.
- `--notes-dir DIR` is the SermonNotes folder (default `/MaresLeg/Church/SermonNotes`).
- `--suffix ToddJones` adds a guest speaker's name to the file name.
- `--no-pdf` makes only the `.odt`.

## Layout

All text is AvenirNext LT Pro Regular: series and title 28 pt, speaker and
date 20 pt, scripture 16 pt, a bold "Description:" heading and body at 16 pt.
Every notes file ends with the Connect Card paragraph and the QR code.

The QR code is copied byte for byte out of a past notes file and checked
against a fixed SHA-256, so it is never re-encoded or altered. No documents or
images are stored in this repository.

The PDF is refused if AvenirNext LT Pro is not installed, because LibreOffice
would otherwise substitute another font.

## Requirements

Python 3.10+, LibreOffice (`soffice`) for the PDF, and the AvenirNext LT Pro
Regular font installed (`~/.local/share/fonts`, then `fc-cache -f`). No Python
packages. Run the tests with `python3 -m unittest`.

Speaker first names in the email are expanded with `sermon_notes/speakers.json`.

## Automatic notes from Thunderbird

A Thunderbird filter saves Katie's email into an inbox folder, and a systemd
user unit notices the new file and runs `python3 -m sermon_notes.inbox`. Each
email is moved to `SermonEmails/done` when its notes are made, or to
`SermonEmails/failed` with a `.log` explaining why. A desktop notification
says which happened.

1. **Clone the repo** to `~/sermon-note-generation`. If you put it elsewhere,
   change `WorkingDirectory` in `contrib/sermon-notes.service`.
2. **Install FiltaQuilla.** In Thunderbird open Tools > Add-ons and Themes,
   search for FiltaQuilla and add it. In its options, tick
   "Save Message as File" so the action appears in filters.
3. **Create the filter.** Tools > Message Filters > New, named "Sermon Notes":
   - Match all of: From contains `worship@pccmi.org`, and Subject contains
     `Sunday Morning Sermon Information`.
   - Action: Save Message as File, folder `/MaresLeg/Church/SermonEmails/inbox`.
   - Run it on "Getting New Mail" (and "Manually Run").
4. **Start the watcher:**
   ```
   mkdir -p ~/.config/systemd/user
   cp contrib/sermon-notes.path contrib/sermon-notes.service ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable --now sermon-notes.path
   ```
5. **Test it** with this week's email: select it, then Tools > Run Filters on
   Selected Messages. The notes appear in `SermonNotes/<year>/` within a few
   seconds. If they don't, check `SermonEmails/failed/` or
   `journalctl --user -u sermon-notes.service`.

The notes are always dated the Sunday after the day the email is processed,
so re-running an older week's email would overwrite this week's files. Use
`python3 -m sermon_notes.generate saved.eml --date YYYY-MM-DD` for those.
