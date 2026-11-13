"""IndexNow: tells Bing, Yandex, Seznam, Naver and other IndexNow search engines which pages are new or changed.
Runs automatically in GitHub Actions — you never need to run it yourself.

    python tools/indexnow.py prepare   (after build.py)   -> finds new/changed pages
    python tools/indexnow.py submit    (after deploy)     -> sends them, then remembers what was sent

The verification key file (<key>.txt) is created at the site root by build.py.
A failure here never breaks the website build or deploy."""
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
WORK = ROOT / "_indexnow"
STATE = ROOT / "data" / "indexnow_state.json"
ENDPOINT = "https://api.indexnow.org/indexnow"

sys.path.insert(0, str(ROOT))


def site_url():
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    return (os.environ.get("SITE_URL") or cfg["site_url"]).rstrip("/")


def page_file(url, base):
    rel = url[len(base):].lstrip("/")
    if not rel or rel.endswith("/"):
        return SITE / rel / "index.html"
    return SITE / rel


def fingerprint(text):
    # ignore build dates so a page only counts as changed when its content changes
    text = re.sub(r"\d{4}-\d{2}-\d{2}(T[\d:.+Z-]+)?", "", text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def prepare():
    base = site_url()
    WORK.mkdir(exist_ok=True)
    keys = [p.stem for p in SITE.glob("*.txt") if re.fullmatch(r"[A-Za-z0-9-]{8,128}", p.stem) and p.read_text().strip() == p.stem]
    if not keys:
        print("IndexNow: no key file found, skipping."); return
    old = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    tree = ElementTree.parse(SITE / "sitemap.xml")
    locs = [e.text.strip() for e in tree.iter() if e.tag.endswith("loc") and e.text]
    new, changed = {}, []
    for url in locs:
        f = page_file(url, base)
        if not f.exists():
            continue
        h = fingerprint(f.read_text(encoding="utf-8", errors="ignore"))
        path = url[len(base):] or "/"
        new[path] = h
        if old.get(path) != h:
            changed.append(url)
    (WORK / "urls.txt").write_text("\n".join(changed), encoding="utf-8")
    (WORK / "state.json").write_text(json.dumps(new, indent=0, sort_keys=True), encoding="utf-8")
    (WORK / "meta.json").write_text(json.dumps({"base": base, "key": keys[0]}), encoding="utf-8")
    print(f"IndexNow: {len(changed)} new or changed pages out of {len(locs)}.")


def submit():
    meta_f = WORK / "meta.json"
    if not meta_f.exists():
        print("IndexNow: nothing prepared."); return
    meta = json.loads(meta_f.read_text(encoding="utf-8"))
    urls = [u for u in (WORK / "urls.txt").read_text(encoding="utf-8").splitlines() if u.strip()]
    base, key = meta["base"], meta["key"]
    host = re.sub(r"^https?://", "", base).split("/")[0]
    if not urls:
        print("IndexNow: no changes to send.")
    ok = True
    for i in range(0, len(urls), 10000):
        body = json.dumps({"host": host, "key": key, "keyLocation": f"{base}/{key}.txt", "urlList": urls[i:i + 10000]}).encode()
        req = urllib.request.Request(ENDPOINT, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                print(f"IndexNow: sent {len(urls[i:i + 10000])} URLs -> HTTP {r.status}")
                ok = ok and r.status in (200, 202)
        except Exception as e:  # never fail the workflow
            print(f"IndexNow: could not send ({e}). Will retry on the next update.")
            ok = False
    if ok:
        STATE.write_text((WORK / "state.json").read_text(encoding="utf-8"), encoding="utf-8")
        print("IndexNow: saved list of submitted pages.")


if __name__ == "__main__":
    try:
        {"prepare": prepare, "submit": submit}[sys.argv[1] if len(sys.argv) > 1 else "prepare"]()
    except Exception as e:
        print(f"IndexNow skipped: {e}")
