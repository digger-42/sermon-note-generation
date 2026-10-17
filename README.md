# sermon-note-generator

Builds the weekly PCCMI Sermon Notes from Katie Winstanley's
"Sunday Morning Sermon Information" email: a LibreOffice Writer `.odt`, then a
PDF of it for pccmi.org and the weekly email.

## Usage

```
python3 -m sermon_notes.generate email.txt
```

This writes `SermonNotes/<year>/YYYY-MM-DD-sermon-notes.odt` and `.pdf` for the
upcoming Sunday. Options:

- `--date YYYY-MM-DD` sets the Sunday explicitly.
- `--notes-dir DIR` is the SermonNotes folder (default `/mnt/project-files/SermonNotes`).
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

Python 3.8+ and LibreOffice (`soffice`) for the PDF. No Python packages.

Speaker first names in the email are expanded with `sermon_notes/speakers.json`.
