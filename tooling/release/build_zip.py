"""Package a patched plugin tree as a zip laid out like the original release.

usage: python rebuild_zip.py <original.zip> <patched web-design-suite dir> <out.zip>
Existing entries keep the original's order and permission bits; new files (tests/)
follow, sorted. Folder entries are stored, files deflated, Unix metadata — as the
original was built.
"""
import pathlib
import sys
import time
import zipfile

orig_zip, tree, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
top = "web-design-suite/"

with zipfile.ZipFile(orig_zip) as z:
    original = {i.filename: i for i in z.infolist()}
    order = [i.filename for i in z.infolist()]

wanted = [top]
for p in sorted(tree.rglob("*")):
    rel = p.relative_to(tree).as_posix()
    if "__pycache__" in rel:
        raise SystemExit(f"refusing to package bytecode: {rel}")
    wanted.append(top + rel + ("/" if p.is_dir() else ""))

gone = [n for n in order if n not in wanted]
if gone:
    raise SystemExit(f"entries in the original but not in the tree: {gone}")
names = order + [n for n in wanted if n not in original]

with zipfile.ZipFile(out, "x") as zout:
    for name in names:
        src = tree / name[len(top):]
        mtime = src.stat().st_mtime if src.exists() else time.time()
        info = zipfile.ZipInfo(name, date_time=time.localtime(mtime)[:6])
        info.create_system = 3
        if name.endswith("/"):
            info.external_attr = original[name].external_attr if name in original else (0o40755 << 16) | 0x10
            info.compress_type = zipfile.ZIP_STORED
            zout.writestr(info, b"")
        else:
            info.external_attr = original[name].external_attr if name in original else 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(info, src.read_bytes())

with zipfile.ZipFile(out) as z:
    bad = z.testzip()
    infos = z.infolist()
print(f"wrote {out} — {len(infos)} entries ({sum(i.is_dir() for i in infos)} folders, "
      f"{sum(not i.is_dir() for i in infos)} files), {out.stat().st_size} bytes, testzip: {bad or 'OK'}")
