#!/usr/bin/env python3
"""
generate_devlog.py -- Weekly dev log automation for playinstigator.com

Reads new Obsidian vault dev logs, summarizes via Ollama phi4,
injects generated HTML into blog.html, commits and pushes.

Run manually:  python scripts/generate_devlog.py
Scheduled:     via scripts/run_devlog_update.ps1 (Windows Task Scheduler)
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

VAULT_PATH = Path(r"C:\Users\ReconUnPro\Documents\GitHub\playinstigator_docs\Our Game Dev Process\Dev Log")
WEBSITE_PATH = Path(r"C:\Users\ReconUnPro\Documents\GitHub\playinstigator-website")
STATE_FILE  = WEBSITE_PATH / "scripts" / "devlog_state.json"
MUSINGS_FILE = WEBSITE_PATH / "scripts" / "musings.json"
BLOG_HTML   = WEBSITE_PATH / "blog.html"
OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL       = "phi4"
GH_ACCOUNT  = "playinstigator"

SUMMARY_PROMPT = """\
You are writing a dev log summary for the Play Instigator blog.
Play Instigator is a solo indie dev making Ritual & Ruin, a dark kawaii 2v2 party game on Steam.

Summarize this dev session in 2-3 short paragraphs (~150 words total).
Write in a casual, honest tone -- like a developer talking to fans.
Focus on what changed in the GAME (what players would care about), not implementation details.
Do not use bullet points. Do not use technical jargon. Start with what was worked on.
Do not claim "this week" or "recently" -- just describe what changed and why it matters.
If the work is bug fixes or infrastructure, say so honestly: the game is getting more stable.
Each paragraph should be a complete thought. No trailing "stay tuned" lines.

Dev log:
{content}
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def md5_file(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def parse_date_from_filename(name: str):
    """Extract date from YYYY-MM-DD_... filename. Returns date or None."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", name)
    if m:
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            return None
    return None


def publication_week_key(d: date) -> str:
    """
    Returns 'YYYY-MM-DD' of the Sunday this file publishes on.
    Mon-Sat files -> coming Sunday (same slot).
    Sunday files -> the NEXT Sunday (script already ran at 9AM).
    """
    from datetime import timedelta
    days_until_sunday = (6 - d.weekday()) % 7  # 0 if today is Sunday
    if days_until_sunday == 0:
        days_until_sunday = 7  # Sunday files go to next slot
    return (d + timedelta(days=days_until_sunday)).isoformat()


def week_date_range_label(dates: list) -> tuple:
    """Return (week_tag, date_label) for an entry card header."""
    mn, mx = min(dates), max(dates)
    week_tag = f"Week of {mn.day} {mn.strftime('%b')}"
    if mn.month == mx.month:
        date_label = f"{mn.day} &ndash; {mx.day} {mx.strftime('%B %Y')}"
    else:
        date_label = (
            f"{mn.day} {mn.strftime('%b')} &ndash; {mx.day} {mx.strftime('%b %Y')}"
        )
    return week_tag, date_label


def md_to_raw_html(md_text: str) -> str:
    """Minimal markdown -> HTML for the collapsible raw notes block."""
    lines = md_text.splitlines()
    parts = []
    in_frontmatter = False
    frontmatter_done = False
    in_ul = False
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # Frontmatter fence
        if stripped == "---" and not frontmatter_done:
            if not in_frontmatter:
                in_frontmatter = True
            else:
                in_frontmatter = False
                frontmatter_done = True
            continue
        if in_frontmatter:
            continue

        # Code block fence -- skip content
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Headers -> h3
        if re.match(r"^#{1,6}\s+", stripped):
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            text = re.sub(r"^#{1,6}\s+", "", stripped)
            parts.append(f"<h3>{text}</h3>")

        # Bullet list
        elif re.match(r"^\s*[-*]\s+", line):
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            text = re.sub(r"^\s*[-*]\s+", "", line).strip()
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
            parts.append(f"  <li>{text}</li>")

        # Blank line
        elif not stripped:
            if in_ul:
                parts.append("</ul>")
                in_ul = False

        # Regular paragraph
        else:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
            text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
            parts.append(f"<p>{text}</p>")

    if in_ul:
        parts.append("</ul>")

    indent = "\n                  "
    return indent.join(parts)


def call_ollama(content: str) -> str:
    """POST to Ollama API, return response text. Raises on failure."""
    import urllib.request
    prompt = SUMMARY_PROMPT.format(content=content)
    payload = json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        result = json.loads(resp.read())
    return result.get("response", "").strip()


def paragraphs_to_html(text: str) -> str:
    """Wrap blank-line-separated paragraphs in <p> tags."""
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    indent = "\n                "
    return indent.join(f"<p>{p}</p>" for p in paras)


def render_devlog_entry(week_tag: str, date_label: str, summary_html: str, raw_html: str) -> str:
    return (
        f'          <article class="entry-card">\n'
        f'              <div class="entry-meta">\n'
        f'                <span class="entry-week-tag">{week_tag}</span>\n'
        f'                <span class="entry-date">{date_label}</span>\n'
        f'              </div>\n'
        f'              <div class="entry-body">\n'
        f'                {summary_html}\n'
        f'              </div>\n'
        f'              <details class="entry-raw">\n'
        f'                <summary>Raw session notes</summary>\n'
        f'                <div class="raw-content">\n'
        f'                  {raw_html}\n'
        f'                </div>\n'
        f'              </details>\n'
        f'            </article>'
    )


def render_musing_entry(entry: dict) -> str:
    d = datetime.strptime(entry["date"], "%Y-%m-%d")
    date_label = f"{d.day} {d.strftime('%B %Y')}"
    body = entry.get("body", "")
    tags_html = ""
    if entry.get("tags"):
        chips = "".join(
            f'<span class="entry-week-tag">{t}</span>' for t in entry["tags"]
        )
        tags_html = (
            f'\n              <div class="entry-meta" '
            f'style="margin-top:0.75rem;gap:0.4rem;flex-wrap:wrap;">'
            f'{chips}</div>'
        )
    return (
        f'            <article class="entry-card">\n'
        f'              <div class="entry-meta">\n'
        f'                <span class="entry-date">{date_label}</span>\n'
        f'              </div>\n'
        f'              <h3 class="musing-title">{entry["title"]}</h3>\n'
        f'              <div class="entry-body">\n'
        f'                {body}\n'
        f'              </div>{tags_html}\n'
        f'            </article>'
    )


def inject_between(html: str, start_marker: str, end_marker: str, content: str) -> str:
    """Replace everything between start_marker and end_marker with content."""
    pattern = re.escape(start_marker) + r".*?" + re.escape(end_marker)
    if content.strip():
        replacement = start_marker + "\n" + content + "\n          " + end_marker
    else:
        replacement = start_marker + "\n          " + end_marker
    result = re.sub(pattern, replacement, html, flags=re.DOTALL)
    if result == html and start_marker not in html:
        print(f"  WARNING: marker not found in blog.html: {start_marker!r}")
    return result


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"last_run": None, "processed_files": {}, "entries": []}


def save_state(state: dict):
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )


def git_commit_push(changed: bool):
    os.chdir(WEBSITE_PATH)
    subprocess.run(["gh", "auth", "switch", "-u", GH_ACCOUNT], check=True)
    subprocess.run(["gh", "auth", "setup-git"], check=True)
    subprocess.run(["git", "add", "blog.html", "scripts/devlog_state.json"], check=True)
    # Check if there's anything staged
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        print("Nothing staged to commit.")
        return
    today = date.today().isoformat()
    subprocess.run(
        ["git", "commit", "-m", f"Auto devlog update {today}"],
        check=True,
    )
    subprocess.run(["git", "push"], check=True)
    print(f"Pushed devlog update for {today}.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] devlog generation starting...")

    state = load_state()
    processed = state.get("processed_files", {})
    entries   = state.get("entries", [])  # [{id, date_sort, week_tag, date_label, summary_html, raw_html}]

    # 1. Find new/changed vault files (skip "catchup" entries -- covered by static HTML)
    vault_files = sorted(VAULT_PATH.glob("*.md"))
    new_by_week = {}  # week_key -> [{date, path, fname}]

    for vf in vault_files:
        fname = vf.name
        if fname in processed:
            info = processed[fname]
            if info.get("entry_id") == "catchup":
                continue  # static catch-up entry, never reprocess
            current_md5 = md5_file(vf)
            if info.get("md5") == current_md5:
                continue  # unchanged
            info["md5"] = current_md5  # mark updated
        else:
            processed[fname] = {"md5": md5_file(vf), "entry_id": None}

        d = parse_date_from_filename(fname)
        if d is None:
            print(f"  Skipping (no date in filename): {fname}")
            continue
        wk = publication_week_key(d)
        new_by_week.setdefault(wk, []).append({"date": d, "path": vf, "fname": fname})

    if not new_by_week:
        print("No new dev log files -- nothing to summarize.")
    else:
        total = sum(len(v) for v in new_by_week.values())
        print(f"Found {total} new/changed file(s) across {len(new_by_week)} week(s).")

    # 2. Generate entries for new weeks
    new_entries_added = bool(new_by_week)
    for wk, files in sorted(new_by_week.items()):
        files.sort(key=lambda x: x["date"])
        dates = [f["date"] for f in files]
        week_tag, date_label = week_date_range_label(dates)

        combined = "\n\n---\n\n".join(
            f["path"].read_text(encoding="utf-8") for f in files
        )
        raw_html = md_to_raw_html(combined)

        print(f"  Summarizing {wk} ({len(files)} file(s)) via Ollama {MODEL}...")
        try:
            summary_text = call_ollama(combined)
        except Exception as exc:
            print(f"  ERROR: Ollama call failed: {exc}")
            print("  Is Ollama running? Start with:  ollama serve")
            sys.exit(1)

        summary_html = paragraphs_to_html(summary_text)

        entry = {
            "id": wk,
            "date_sort": max(dates).isoformat(),
            "week_tag": week_tag,
            "date_label": date_label,
            "summary_html": summary_html,
            "raw_html": raw_html,
        }

        existing = next((e for e in entries if e["id"] == wk), None)
        if existing:
            existing.update(entry)
        else:
            entries.append(entry)

        for f in files:
            processed[f["fname"]]["entry_id"] = wk

    # 3. Sort entries newest first, save state
    entries.sort(key=lambda e: e["date_sort"], reverse=True)
    state["entries"]         = entries
    state["processed_files"] = processed
    state["last_run"]        = datetime.now().isoformat()
    save_state(state)

    # 4. Render devlog HTML block
    devlog_html = "\n".join(
        render_devlog_entry(
            e["week_tag"], e["date_label"], e["summary_html"], e["raw_html"]
        )
        for e in entries
    )

    # 5. Render musings HTML block
    musings_data = json.loads(MUSINGS_FILE.read_text(encoding="utf-8"))
    musings_data.sort(key=lambda m: m["date"], reverse=True)
    musings_html = "\n".join(render_musing_entry(m) for m in musings_data)

    # 6. Inject into blog.html
    blog_src = BLOG_HTML.read_text(encoding="utf-8")
    blog_src = inject_between(blog_src,
        "<!-- WEEKLY-GENERATED START -->",
        "<!-- WEEKLY-GENERATED END -->",
        devlog_html,
    )
    blog_src = inject_between(blog_src,
        "<!-- MUSINGS-GENERATED START -->",
        "<!-- MUSINGS-GENERATED END -->",
        musings_html,
    )
    BLOG_HTML.write_text(blog_src, encoding="utf-8", newline="\n")
    print("blog.html updated.")

    # 7. Git commit + push
    git_commit_push(new_entries_added)
    print("Done.")


if __name__ == "__main__":
    main()
