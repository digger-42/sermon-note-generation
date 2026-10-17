"""Extract sermon details from Katie's "Sunday Morning Sermon Information" email."""

import email
import email.policy
import html
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
    # Katie's signature starts at a "-- " separator line, or at her name on a
    # line by itself when the separator is missing. Without it nothing is cut.
    return re.split(r"^(?:--\s*|\s*Katie Winstanley\s*)$", text,
                    maxsplit=1, flags=re.M)[0]


def _html_to_text(markup):
    markup = re.sub(r"(?is)<(script|style).*?</\1>", "", markup)
    markup = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d)>", "\n", markup)
    return html.unescape(re.sub(r"<[^>]+>", "", markup)).replace("\xa0", " ")


def read_email(raw):
    """Return the body text of an email given as bytes.

    Accepts a saved message (.eml, as Thunderbird writes it) or plain text
    pasted from the message body.
    """
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    if not (msg["From"] or msg["Subject"]):
        return raw.decode("utf-8", errors="replace")
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        raise ValueError("Email has no readable body")
    body = part.get_content()
    return _html_to_text(body) if part.get_content_type() == "text/html" else body


def parse_email(text):
    text = _strip_signature(text.replace("\r\n", "\n"))
    info = SermonInfo()

    # HTML mail often uses a curly apostrophe ("Steve’s message").
    m = re.search(r"for\s+([A-Z][\w.\-]*(?:\s+[A-Z][\w.\-]*)*?)['’]s\s+message", text)
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
