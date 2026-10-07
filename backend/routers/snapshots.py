from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

import snapshots as snap

router = APIRouter()


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


@router.get("/snapshots")
async def get_snapshots():
    return {"snapshots": snap.list_snapshots()}


@router.get("/snapshots/sources")
async def get_sources():
    return {"sources": snap.list_sources()}


@router.get("/snapshots/index", response_class=HTMLResponse)
async def snapshots_index():
    rows = snap.list_snapshots()
    row_html = "\n".join(
        f'<tr><td><a href="/snapshots/download/{r["filename"]}">{r["filename"]}</a></td>'
        f'<td align="right">{r["modified_at"][:16].replace("T", " ")}</td>'
        f'<td align="right">{_human_size(r["size_bytes"])}</td></tr>'
        for r in rows
    )
    html = f"""<!DOCTYPE html>
<html>
<head><title>Index of /snapshots/</title></head>
<body>
<h1>Index of /snapshots/</h1>
<table>
<tr><th align="left">Name</th><th>Last modified</th><th>Size</th></tr>
<tr><td colspan="3"><hr></td></tr>
<tr><td><a href="../">../</a></td><td>&nbsp;</td><td>&nbsp;</td></tr>
{row_html}
<tr><td colspan="3"><hr></td></tr>
</table>
</body>
</html>"""
    return HTMLResponse(html)


@router.get("/snapshots/download/{filename}")
async def download_snapshot(filename: str):
    path = snap.get_snapshot_path(filename)
    if path is None:
        raise HTTPException(404, f"Snapshot '{filename}' not found")
    return FileResponse(path, media_type="application/zip", filename=filename)

