"""Review helper: print the visible text of selected slides of a built deck."""
import html, re, sys, pathlib

deck = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
kinds = set(sys.argv[2:])
for m in re.finditer(r"<section class='slide' data-kind='([^']+)'.*?</section>", deck, re.S):
    kind = m.group(1)
    if kinds and kind not in kinds:
        continue
    body = m.group(0)
    notes = re.search(r"<div class='notes'>(.*?)</div>", body, re.S)
    main = re.sub(r"<div class='notes'>.*?</div>", "", body, flags=re.S)
    main = re.sub(r"<div class='gap'>.*?</div>", "", main, flags=re.S)
    def txt(s):
        s = re.sub(r"<[^>]+>", " ", s)
        return " ".join(html.unescape(s).split())
    print(f"--- [{kind}] {txt(main)[:900]}")
    if notes:
        print(f"    NOTES (printed in Ctrl+P): {txt(notes.group(1))[:400]}")
