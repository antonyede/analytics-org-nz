"""Create a reviewable Markdown index and contact sheets from actual captures."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="evidence/local")
    args = parser.parse_args()
    folder = ROOT / args.input
    data = json.loads((folder / "results.json").read_text())
    assert data.get("finished_at"), "Wait for the matrix to finish before publishing its index"
    results = data["comparisons"]
    lines = ["# Matched visual verification", "", f"Source: {data['source']}", "",
             f"Target: `{data['target']}`", "", f"Browser: Chromium {data['browser']}; device scale factor 1; locale en-US; UTC.", "",
             f"Finished: {data['finished_at']}", "", f"**{sum(r['exact_pixels'] for r in results)}/{len(results)} comparisons have identical pixels.** "
             f"Network errors: {len(data['network_errors'])}; browser JavaScript errors: {len(data['console_errors'])}.", "",
             "These are full-page screenshots from actual browser visits. Pixel equality applies to the tested stable states and viewports only. Local target verification does not establish deployed GitHub Pages behaviour.", "",
             "| Viewport | Dimensions | Route | State | Source capture | Target capture | Difference |", "| --- | --- | --- | --- | --- | --- | --- |"]
    relative = folder.relative_to(ROOT / "evidence")
    for result in results:
        w, h = data["viewports"][result["viewport"]]
        difference = "Identical" if result["exact_pixels"] else f"{result['different_percent']}% / {result['different_pixels']} pixels"
        lines.append(f"| {result['viewport']} | {w} × {h} | `{result['route']}` | {result['state']} | [source]({relative}/{result['source_screenshot']}) | [target]({relative}/{result['target_screenshot']}) | {difference} |")
    lines.extend(["", "## Overview sheets", "", "The thumbnails below are fitted previews; full-resolution captures are linked above.", ""])
    for viewport in data["viewports"]:
        rows = [r for r in results if r["viewport"] == viewport and r["state"] == "default"]
        sheet = Image.new("RGB", (960, len(rows) * 360 + 40), "#ffffff")
        draw = ImageDraw.Draw(sheet)
        draw.text((20, 12), f"{viewport}: actual source captures (left) and local target captures (right)", fill="black")
        for index, result in enumerate(rows):
            top = index * 360 + 40
            draw.text((20, top), f"{result['route']} — {result['different_percent']}% different", fill="black")
            for side, left in [("source", 15), ("target", 495)]:
                source = Image.open(folder / result[side + "_screenshot"]).convert("RGB")
                thumb = ImageOps.contain(source, (450, 325))
                sheet.paste(thumb, (left, top + 25))
        filename = f"overview-{viewport}.jpg"
        sheet.save(folder / filename, quality=88)
        lines.append(f"![{viewport} overview]({relative}/{filename})")
        lines.append("")
    (ROOT / "evidence" / "visual-comparisons.md").write_text("\n".join(lines) + "\n")
    print("Created evidence/visual-comparisons.md and three overview sheets")


if __name__ == "__main__":
    main()
