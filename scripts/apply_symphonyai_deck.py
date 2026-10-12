#!/usr/bin/env python3
"""Fill the official SymphonyAI 2026 PowerPoint template with a leadership brief.

The deck keeps every template slide master and layout. Sample slides are removed
so only the briefing is shown. Retail division color is used for bullets.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape


TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "brand" / "SymphonyAI_PowerPoint_Template_2026.potx"
SLIDE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
LAYOUT_REL = "../slideLayouts/slideLayout3.xml"
MAX_WORDS = 9
MAX_BULLETS = 8


def brand_text(value: object) -> str:
    text = str(value or "").replace("&", "and")
    text = re.sub(r"\s+", " ", text).strip()
    return text.rstrip(".").strip()


def sentence_label(value: object) -> str:
    text = brand_text(value).replace("-", " ").replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "Not available"
    if text.isupper():
        return text[:1] + text[1:].lower()
    return text[:1].upper() + text[1:]


def visual_lines(value: object, limit: int = 6) -> list[str]:
    words = brand_text(value).split()
    if not words:
        return ["Not available"]
    lines = [" ".join(words[index:index + MAX_WORDS]) for index in range(0, len(words), MAX_WORDS)]
    if len(lines) > limit:
        lines = lines[:limit]
        lines[-1] = lines[-1].rstrip(".") + " …"
    return lines


def display_date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return datetime.now().strftime("%d %b %Y")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return visual_lines(text, 1)[0]
    return parsed.strftime("%d %b %Y")


def _runs(lines: list[str], size: str | None = None, ink: bool = False) -> str:
    size_attr = f' sz="{size}"' if size else ""
    color = "<a:solidFill><a:srgbClr val=\"121212\"/></a:solidFill>" if ink else ""
    run_props = f'<a:rPr lang="en-US"{size_attr} dirty="0">{color}<a:latin typeface="Arial"/></a:rPr>'
    parts = []
    for index, line in enumerate(lines):
        if index:
            parts.append("<a:br/>")
        parts.append(f"<a:r>{run_props}<a:t>{escape(line)}</a:t></a:r>")
    return "".join(parts)


def plain_paragraph(lines: list[str], size: str | None = None, ink: bool = False) -> str:
    return f"<a:p>{_runs(lines, size, ink)}</a:p>"


def bullet_paragraph(lines: list[str]) -> str:
    return (
        "<a:p><a:pPr>"
        '<a:lnSpc><a:spcPts val="1900"/></a:lnSpc>'
        '<a:buFont typeface="Arial"/>'
        '<a:buClr><a:srgbClr val="00EAC3"/></a:buClr>'
        '<a:buChar char="•"/>'
        "</a:pPr>"
        f"{_runs(lines, '1400', ink=True)}"
        "</a:p>"
    )


def chunk_bullets(items: list[list[str]]) -> list[list[list[str]]]:
    slides: list[list[list[str]]] = []
    current: list[list[str]] = []
    rows = 0
    for item in items:
        weight = len(item)
        if current and (len(current) >= MAX_BULLETS or rows + weight > 12):
            slides.append(current)
            current = []
            rows = 0
        current.append(item)
        rows += weight
    if current:
        slides.append(current)
    return slides or [[["Not available"]]]


def content_slides(brief: dict) -> list[dict]:
    verdict = sentence_label(brief.get("verdict"))
    confidence = sentence_label(brief.get("confidence"))
    slides = [{
        "title": "Decision",
        "subtitle": f"{verdict} · {confidence} confidence",
        "bullets": [visual_lines(brief.get("executive_summary"), 8)],
    }]

    evidence = []
    findings = brief.get("findings") or []
    if not findings:
        evidence.append(visual_lines(brief.get("executive_summary"), 2))
    for finding in findings[:8]:
        evidence.append(visual_lines(finding.get("title"), 2))
        evidence.append(visual_lines(finding.get("detail"), 3))
    for index, group in enumerate(chunk_bullets(evidence)):
        slides.append({
            "title": "Evidence",
            "subtitle": "Grounded dashboard findings" if index == 0 else "Continued",
            "bullets": group,
        })

    metrics = brief.get("metrics") or []
    if metrics:
        metric_lines = [visual_lines(f"{item.get('label')}: {item.get('value')}", 2) for item in metrics[:8]]
        for index, group in enumerate(chunk_bullets(metric_lines)):
            slides.append({
                "title": "Key metrics",
                "subtitle": "Values cited in the analysis" if index == 0 else "Continued",
                "bullets": group,
            })

    actions = brief.get("recommendations") or ["No leadership action was recommended"]
    action_lines = [visual_lines(item, 3) for item in actions[:8]]
    for index, group in enumerate(chunk_bullets(action_lines)):
        slides.append({
            "title": "Next actions",
            "subtitle": "Recommended leadership actions" if index == 0 else "Continued",
            "bullets": group,
        })

    sources = brief.get("sources") or []
    if sources:
        source_lines = [visual_lines(item, 2) for item in sources[:8]]
        for index, group in enumerate(chunk_bullets(source_lines)):
            slides.append({
                "title": "Sources",
                "subtitle": "Traceable evidence labels" if index == 0 else "Continued",
                "bullets": group,
            })
    return slides


def fill_title_slide(xml: str, brief: dict) -> str:
    title = visual_lines(brief.get("title"), 3)
    subtitle = visual_lines(brief.get("question"), 3)
    date = display_date(brief.get("generated_at"))
    xml = xml.replace(
        '<a:r><a:rPr lang="en-US" b="0" dirty="0"><a:latin typeface="+mj-lt"/></a:rPr><a:t>Title</a:t></a:r>',
        _runs(title),
        1,
    )
    xml = xml.replace(
        '<a:r><a:rPr lang="en-US" dirty="0"/><a:t>Date</a:t></a:r>',
        _runs([date], "1400"),
        1,
    )
    xml = xml.replace(
        '<a:r><a:rPr lang="en-US" sz="2400" b="0" dirty="0"><a:latin typeface="+mj-lt"/></a:rPr><a:t>Subtitle</a:t></a:r>',
        _runs(subtitle, "1400"),
        1,
    )
    return xml


def fill_content_slide(xml: str, number: int, slide: dict, seed: int) -> str:
    xml = xml.replace(">3</a:t>", f">{number}</a:t>", 1)
    title = plain_paragraph(visual_lines(slide["title"], 2), ink=True)
    subtitle = plain_paragraph(visual_lines(slide["subtitle"], 2), "1400", ink=True)
    body = "".join(bullet_paragraph(item) for item in slide["bullets"])
    xml = xml.replace('<a:p><a:endParaRPr lang="en-GB"/></a:p>', title, 1)
    xml = xml.replace('<a:p><a:endParaRPr lang="en-GB"/></a:p>', subtitle, 1)
    xml = xml.replace('<a:p><a:endParaRPr lang="en-GB" dirty="0"/></a:p>', body, 1)
    counter = {"value": 0}

    def unique_id(match: re.Match[str]) -> str:
        counter["value"] += 1
        return f'id="{{B{seed:07d}-{counter["value"]:04d}-4A11-9C22-{counter["value"]:012d}}}"'

    return re.sub(r'id="\{[0-9A-Fa-f-]+\}"', unique_id, xml)


def fill_closing_slide(xml: str, brief: dict) -> str:
    title = plain_paragraph(visual_lines(brief.get("title"), 2))
    detail = plain_paragraph([display_date(brief.get("generated_at"))], "1400")
    xml = xml.replace('<a:p><a:endParaRPr lang="en-GB" dirty="0"/></a:p>', title, 1)
    xml = xml.replace(
        '<a:p><a:endParaRPr lang="en-GB" dirty="0"><a:solidFill><a:schemeClr val="tx1"/></a:solidFill></a:endParaRPr></a:p>',
        detail,
        1,
    )
    return xml


def build_deck(brief: dict, output_path: Path) -> None:
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"SymphonyAI template is missing: {TEMPLATE}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="symphonyai-deck-") as temporary:
        root = Path(temporary)
        with zipfile.ZipFile(TEMPLATE) as archive:
            archive.extractall(root)

        content_types = root / "[Content_Types].xml"
        content_types.write_text(
            content_types.read_text(encoding="utf-8").replace(
                "presentationml.template.main+xml",
                "presentationml.presentation.main+xml",
            ),
            encoding="utf-8",
        )

        slides_dir = root / "ppt" / "slides"
        rels_dir = slides_dir / "_rels"
        template_xml = (slides_dir / "slide3.xml").read_text(encoding="utf-8")
        (slides_dir / "slide1.xml").write_text(fill_title_slide((slides_dir / "slide1.xml").read_text(encoding="utf-8"), brief), encoding="utf-8")
        (slides_dir / "slide14.xml").write_text(fill_closing_slide((slides_dir / "slide14.xml").read_text(encoding="utf-8"), brief), encoding="utf-8")

        kept = ["slides/slide1.xml"]
        new_ids = []
        for index, slide in enumerate(content_slides(brief), start=1):
            name = f"slide{14 + index}.xml"
            number = index + 1
            (slides_dir / name).write_text(fill_content_slide(template_xml, number, slide, 1400 + index), encoding="utf-8")
            (rels_dir / f"{name}.rels").write_text(
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="{LAYOUT_REL}"/>'
                "</Relationships>",
                encoding="utf-8",
            )
            relation_id = f"rId{40 + index}"
            kept.append(f"slides/{name}")
            new_ids.append((300 + index, relation_id, f"slides/{name}"))

        kept.append("slides/slide14.xml")
        presentation_rels = root / "ppt" / "_rels" / "presentation.xml.rels"
        rels_text = presentation_rels.read_text(encoding="utf-8")

        def keep_relation(match: re.Match[str]) -> str:
            target = re.search(r'Target="([^"]+)"', match.group(0))
            if target and target.group(1).startswith("slides/slide") and target.group(1) not in {"slides/slide1.xml", "slides/slide14.xml"}:
                return ""
            return match.group(0)

        rels_text = re.sub(r"<Relationship\b[^>]*/>", keep_relation, rels_text)
        inserted = "".join(
            f'<Relationship Id="{relation_id}" Type="{SLIDE_REL}" Target="{target}"/>'
            for _, relation_id, target in new_ids
        )
        rels_text = rels_text.replace("</Relationships>", inserted + "</Relationships>")
        presentation_rels.write_text(rels_text, encoding="utf-8")

        slide_ids = ['<p:sldId id="270" r:id="rId5"/>']
        slide_ids.extend(f'<p:sldId id="{slide_id}" r:id="{relation_id}"/>' for slide_id, relation_id, _ in new_ids)
        slide_ids.append('<p:sldId id="2147483646" r:id="rId18"/>')
        presentation = root / "ppt" / "presentation.xml"
        presentation_text = presentation.read_text(encoding="utf-8")
        updated, count = re.subn(
            r"<p:sldIdLst>.*?</p:sldIdLst>",
            "<p:sldIdLst>" + "".join(slide_ids) + "</p:sldIdLst>",
            presentation_text,
            count=1,
            flags=re.DOTALL,
        )
        if count != 1:
            raise RuntimeError("SymphonyAI template slide list could not be updated.")
        presentation.write_text(updated, encoding="utf-8")

        types_text = content_types.read_text(encoding="utf-8")
        for number in range(2, 14):
            override = f'<Override PartName="/ppt/slides/slide{number}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            types_text = types_text.replace(override, "")
            (slides_dir / f"slide{number}.xml").unlink(missing_ok=True)
            (rels_dir / f"slide{number}.xml.rels").unlink(missing_ok=True)
        additions = "".join(
            f'<Override PartName="/ppt/{target}" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            for _, _, target in new_ids
        )
        content_types.write_text(types_text.replace("</Types>", additions + "</Types>"), encoding="utf-8")

        core = root / "docProps" / "core.xml"
        if core.exists():
            title = escape(visual_lines(brief.get("title"), 2)[0])
            core_text = core.read_text(encoding="utf-8")
            core_text = re.sub(r"<dc:title>.*?</dc:title>", f"<dc:title>{title}</dc:title>", core_text, count=1)
            core.write_text(core_text, encoding="utf-8")

        if output_path.exists():
            output_path.unlink()
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(root).as_posix())


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: apply_symphonyai_deck.py <input.json> <output.pptx>", file=sys.stderr)
        return 2
    brief = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    build_deck(brief, Path(sys.argv[2]))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
