"""Create a reviewable Markdown index and contact sheets from actual captures."""
import argparse
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="evidence/local")
    parser.add_argument("--output", default="evidence/visual-comparisons.md")
    args = parser.parse_args()
    folder = ROOT / args.input
    data = json.loads((folder / "results.json").read_text())
    assert data.get("finished_at"), "Wait for the matrix to finish before publishing its index"
    results = data["comparisons"]
    owner_edits = bool(data.get('expected_owner_edits'))
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Matched visual verification", "", f"Source: {data['source']}", "",
             f"Target: `{data['target']}`", "", f"Browser: Chromium {data['browser']}; device scale factor 1; locale en-US; UTC.", "",
             f"Finished: {data['finished_at']}", "", f"**{sum(r['exact_pixels'] for r in results)}/{len(results)} comparisons have identical pixels against {'source with the requested owner edits' if owner_edits else 'the source'}.** "
             f"Network errors: {len(data['network_errors'])}; browser JavaScript errors: {len(data['console_errors'])}.", "",
             "These are full-page screenshots from actual browser visits. Pixel equality applies to the tested stable states and viewports only.", "",
             "| Viewport | Dimensions | Route | State | Source capture | Target capture | Difference |", "| --- | --- | --- | --- | --- | --- | --- |"]
    if owner_edits:
        lines[0:0] = ["<!-- The original Webflow site is unchanged. Adjusted source screenshots apply only the two authorised removals in the browser DOM. -->", ""]
        lines[14:14] = ["Requested owner edits: remove the TRA sponsor anchor while preserving its layout wrapper; remove Antony Ede's complete About profile. Original-source and adjusted-source screenshots are retained. Nothing is masked in pixel comparison.", ""]
    relative = os.path.relpath(folder, output.parent)
    for result in results:
        w, h = data["viewports"][result["viewport"]]
        difference = "Identical" if result["exact_pixels"] else f"{result['different_percent']}% / {result['different_pixels']} pixels"
        reference = f"[original]({relative}/{result['source_screenshot']})"
        if owner_edits:
            reference += f" · [with owner edits]({relative}/{result['expected_screenshot']})"
        lines.append(f"| {result['viewport']} | {w} × {h} | `{result['route']}` | {result['state']} | {reference} | [target]({relative}/{result['target_screenshot']}) | {difference} |")
    lines.extend(["", "## Overview sheets", "", "The thumbnails below are fitted previews; full-resolution captures are linked above.", ""])
    for viewport in data["viewports"]:
        rows = [r for r in results if r["viewport"] == viewport and r["state"] == "default"]
        sheet = Image.new("RGB", (960, len(rows) * 360 + 40), "#ffffff")
        draw = ImageDraw.Draw(sheet)
        draw.text((20, 12), f"{viewport}: {'expected source with owner edits' if owner_edits else 'source'} (left) and target (right)", fill="black")
        for index, result in enumerate(rows):
            top = index * 360 + 40
            draw.text((20, top), f"{result['route']} — {result['different_percent']}% different", fill="black")
            for side, left in [("source", 15), ("target", 495)]:
                key = 'expected_screenshot' if side == 'source' and owner_edits else side + '_screenshot'
                source = Image.open(folder / result[key]).convert("RGB")
                thumb = ImageOps.contain(source, (450, 325))
                sheet.paste(thumb, (left, top + 25))
        filename = f"overview-{viewport}.jpg"
        sheet.save(folder / filename, quality=88)
        lines.append(f"![{viewport} overview]({relative}/{filename})")
        lines.append("")
    output.write_text("\n".join(lines).rstrip() + "\n")
    print(f"Created {output.relative_to(ROOT)} and three overview sheets")


if __name__ == "__main__":
    main()
