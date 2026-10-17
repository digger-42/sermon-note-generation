"""Write a Sermon Notes .odt matching the 2026 house layout."""

import zipfile
from xml.sax.saxutils import escape

FONT = "AvenirNext LT Pro Regular"
QR_NAME = "Pictures/connect-card-qr.png"
# Frame size used for the QR code in every 2026 notes file.
QR_WIDTH, QR_HEIGHT = "1.6346in", "1.6575in"

CONNECT_CARD = (
    "One of the ways you can take your next step in faith is by filling "
    "out the Connect Card. Scan the QR code and let us know how we can help."
)

MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">
 <manifest:file-entry manifest:full-path="/" manifest:version="1.3" manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="%s" manifest:media-type="image/png"/>
</manifest:manifest>
""" % QR_NAME

NS = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
    'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
    'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
    'xmlns:xlink="http://www.w3.org/1999/xlink" '
    'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
    'xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'office:version="1.3"'
)

FONT_DECL = (
    '<office:font-face-decls><style:font-face style:name="%s" '
    'svg:font-family="&apos;%s&apos;" style:font-pitch="variable"/>'
    "</office:font-face-decls>" % (FONT, FONT)
)


def _para_style(name, size, align="start", bold=False, space_after="0in"):
    weight = ' fo:font-weight="bold"' if bold else ""
    return (
        '<style:style style:name="%s" style:family="paragraph">'
        '<style:paragraph-properties fo:text-align="%s" fo:margin-top="0in" '
        'fo:margin-bottom="%s"/>'
        '<style:text-properties style:font-name="%s" fo:font-size="%s"%s/>'
        "</style:style>" % (name, align, space_after, FONT, size, weight)
    )


STYLES = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles %s>%s
<office:styles>
<style:default-style style:family="paragraph"><style:text-properties style:font-name="%s" fo:font-size="16pt"/></style:default-style>
<style:style style:name="Standard" style:family="paragraph"/>
</office:styles>
<office:automatic-styles>
<style:page-layout style:name="pm1"><style:page-layout-properties fo:page-width="8.5in" fo:page-height="11in" style:print-orientation="portrait" fo:margin-top="0.7874in" fo:margin-bottom="0.7874in" fo:margin-left="0.7874in" fo:margin-right="0.7874in"/></style:page-layout>
</office:automatic-styles>
<office:master-styles><style:master-page style:name="Standard" style:page-layout-name="pm1"/></office:master-styles>
</office:document-styles>
""" % (NS, FONT_DECL, FONT)

AUTO_STYLES = "".join([
    _para_style("SNTitle", "28pt", "center", space_after="0.1in"),
    _para_style("SNSpeaker", "20pt", "center", space_after="0.08in"),
    _para_style("SNScripture", "16pt", "center"),
    _para_style("SNHeading", "16pt", bold=True),
    _para_style("SNBody", "16pt"),
    _para_style("SNQR", "16pt", "center"),
    '<style:style style:name="fr1" style:family="graphic">'
    '<style:graphic-properties style:wrap="none" style:vertical-pos="top" '
    'style:vertical-rel="paragraph" style:horizontal-pos="center" '
    'style:horizontal-rel="paragraph"/></style:style>',
])


def _p(style, text=""):
    return '<text:p text:style-name="%s">%s</text:p>' % (style, escape(text))


def build_content(info, speaker_line):
    blank = _p("SNBody")
    parts = [
        '<text:p text:style-name="SNTitle">%s<text:line-break/>%s</text:p>'
        % (escape(info.series), escape(info.title)),
        _p("SNSpeaker", speaker_line),
        _p("SNScripture", info.scripture),
        blank,
        _p("SNHeading", "Description:"),
    ]
    for para in info.description:
        parts += [_p("SNBody", para), blank]
    parts += [
        _p("SNBody", CONNECT_CARD),
        blank,
        '<text:p text:style-name="SNQR"><draw:frame draw:style-name="fr1" '
        'draw:name="ConnectCardQR" text:anchor-type="as-char" svg:width="%s" '
        'svg:height="%s" draw:z-index="0"><draw:image xlink:href="%s" '
        'xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad" '
        'draw:mime-type="image/png"/></draw:frame></text:p>'
        % (QR_WIDTH, QR_HEIGHT, QR_NAME),
    ]
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<office:document-content %s>%s<office:automatic-styles>%s"
        "</office:automatic-styles><office:body><office:text>%s"
        "</office:text></office:body></office:document-content>\n"
        % (NS, FONT_DECL, AUTO_STYLES, "".join(parts))
    )


def build_meta(title):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<office:document-meta %s>'
        "<office:meta><dc:title>%s</dc:title></office:meta>"
        "</office:document-meta>\n" % (NS, escape(title))
    )


def write_odt(path, info, speaker_line, qr_bytes):
    with zipfile.ZipFile(path, "w") as z:
        # The mimetype entry must be first and uncompressed.
        z.writestr("mimetype", "application/vnd.oasis.opendocument.text",
                   compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/manifest.xml", MANIFEST, zipfile.ZIP_DEFLATED)
        z.writestr("styles.xml", STYLES, zipfile.ZIP_DEFLATED)
        z.writestr("meta.xml", build_meta(info.title), zipfile.ZIP_DEFLATED)
        z.writestr("content.xml", build_content(info, speaker_line),
                   zipfile.ZIP_DEFLATED)
        # Stored, not recompressed: the QR image goes in byte for byte.
        z.writestr(QR_NAME, qr_bytes, compress_type=zipfile.ZIP_STORED)
