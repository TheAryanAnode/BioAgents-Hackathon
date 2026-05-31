"""Generate a minimal but valid PDF with extractable text for upload testing."""

import sys
import zlib


def make_pdf(path: str, lines: list[str]) -> None:
    content_lines = ["BT", "/F1 12 Tf", "72 760 Td", "14 TL"]
    for ln in lines:
        safe = ln.replace("(", "\\(").replace(")", "\\)")
        content_lines.append(f"({safe}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    content = "\n".join(content_lines).encode("latin-1")
    stream = zlib.compress(content)

    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
    )
    objs.append(
        b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream)
        + stream
        + b"\nendstream"
    )
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objs) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objs) + 1)
    out += b"startxref\n%d\n%%%%EOF" % xref_pos

    with open(path, "wb") as f:
        f.write(out)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/test_paper.pdf"
    make_pdf(
        path,
        [
            "Title: SCN2A loss-of-function links GABAergic signaling to epilepsy in autism",
            "Abstract: We report that SCN2A variants reduce cortical excitability and",
            "disrupt GABAergic signaling, increasing seizure susceptibility in autism",
            "spectrum disorder. Our cohort shows epilepsy comorbidity tied to synaptic",
            "plasticity deficits, suggesting a shared mechanism between autism and epilepsy.",
            "DOI: 10.1234/synthesisos.test.2026",
        ],
    )
    print(f"wrote {path}")
