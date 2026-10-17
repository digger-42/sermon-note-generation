"""Extract sermon details from Katie's "Sunday Morning Sermon Information" email."""

import re
from dataclasses import dataclass, field

FIELDS = ("Series", "Title", "Scripture", "Description")


@dataclass
class SermonInfo:
    speaker: str = ""
    series: str = ""
    title: str = ""
    scripture: str = ""
    description: list = field(default_factory=list)  # one string per paragraph


def _strip_signature(text):
    # Everything after the "-- " signature separator is Katie's signature block.
    return re.split(r"^--\s*$", text, maxsplit=1, flags=re.M)[0]


def parse_email(text):
    text = _strip_signature(text.replace("\r\n", "\n"))
    info = SermonInfo()

    m = re.search(r"for\s+([A-Z][\w.\-]*(?:\s+[A-Z][\w.\-]*)*?)'s\s+message", text)
    if m:
        info.speaker = m.group(1).strip()

    label = re.compile(r"^(%s)\s*:\s*(.*)$" % "|".join(FIELDS), re.M | re.I)
    matches = list(label.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        value = (m.group(2) + text[m.end():end]).strip()
        key = m.group(1).lower()
        if key == "description":
            paras = [" ".join(p.split()) for p in re.split(r"\n\s*\n", value)]
            info.description = [p for p in paras if p]
        else:
            setattr(info, key, " ".join(value.split()))

    missing = [f for f in ("series", "title", "scripture") if not getattr(info, f)]
    if not info.description:
        missing.append("description")
    if missing:
        raise ValueError("Email is missing: " + ", ".join(missing))
    return info
