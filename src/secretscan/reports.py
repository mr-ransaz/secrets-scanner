"""Serialize only masked Finding data; HTML has no remote resources."""

import html
from collections import Counter
from urllib.parse import quote

from secretscan.rules import RULES
from secretscan.scanner import Result


def sarif(result: Result) -> dict:
    levels = {"high": "error", "medium": "warning", "low": "note"}
    rules = [
        {
            "id": r.id,
            "shortDescription": {"text": r.description},
            "defaultConfiguration": {"level": levels[r.severity]},
        }
        for r in RULES
    ]
    findings = []
    for f in result.findings:
        findings.append(
            {
                "ruleId": f.rule_id,
                "level": levels[f.severity],
                "message": {"text": f"Likely secret: {f.masked_preview}"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": quote(f.file, safe="/")},
                            "region": {
                                "startLine": f.line,
                                "startColumn": f.column_start,
                                "endColumn": f.column_end,
                            },
                        }
                    }
                ],
                "partialFingerprints": {"secretscan/v1": f.fingerprint},
                "properties": {"commit": f.commit, "severity": f.severity},
            }
        )
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "secretscan",
                        "version": result.version,
                        "rules": rules,
                    }
                },
                "results": findings,
                "properties": {
                    "rootName": result.root_name,
                    "time": result.time,
                    "gitHistory": result.git_history,
                    "skipped": result.skipped,
                },
            }
        ],
    }


def html_report(result: Result) -> str:
    def escape(value: object) -> str:
        return html.escape(str(value), quote=True)

    counts = Counter(f.severity for f in result.findings)
    cards = f'<div class="card">Files scanned <b>{result.files_scanned}</b></div>'
    cards += "".join(
        f'<div class="card">{s.title()} <b>{counts[s]}</b></div>'
        for s in ("high", "medium", "low")
    )
    rows = []
    for f in sorted(result.findings, key=lambda f: (f.file, f.line, f.rule_id)):
        cells = (
            f.file,
            f.line,
            f"{f.column_start}–{f.column_end}",
            f.severity,
            f.rule_id,
            f.masked_preview,
            f.fingerprint[:12],
            (f.commit or "")[:12],
        )
        rows.append("<tr>" + "".join(f"<td>{escape(c)}</td>" for c in cells) + "</tr>")
    metadata = (
        f"Version {escape(result.version)} · {escape(result.time)} · "
        f"Root {escape(result.root_name)} · Git history "
        f"{'yes' if result.git_history else 'no'}"
    )
    return (
        """<!doctype html>
<html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none';
 style-src 'unsafe-inline'; script-src 'unsafe-inline'">
<title>secretscan report</title>
<style>
body{background:#111827;color:#e5e7eb;font:15px system-ui;margin:2rem}
h1{color:#93c5fd}.cards{display:flex;gap:1rem;flex-wrap:wrap}
.card{background:#1f2937;padding:1rem;border-radius:8px;min-width:100px}
b{display:block;font-size:2rem}input{margin:1.5rem 0;padding:.6rem;
background:#1f2937;color:white;border:1px solid #64748b}
.scroll{overflow:auto}table{border-collapse:collapse;width:100%}
td,th{text-align:left;padding:.7rem;border-bottom:1px solid #374151}
td{overflow-wrap:anywhere}th{color:#93c5fd}tr:hover{background:#1f2937}
</style><h1>secretscan report</h1><p>"""
        + metadata
        + """</p>
<div class="cards">"""
        + cards
        + """</div>
<label for="filter">Filter by file, severity or rule</label>
<input id="filter" type="search" autocomplete="off">
<p>Grouped by file. Column ends are exclusive. Previews are masked.
Files scanned includes historical file revisions when history is enabled.</p>
<div class="scroll"><table><thead><tr><th>File</th><th>Line</th><th>Columns</th>
<th>Severity</th><th>Rule</th><th>Masked preview</th><th>Fingerprint</th>
<th>Commit</th></tr></thead><tbody>"""
        + "".join(rows)
        + """</tbody></table></div>
<script>
document.getElementById('filter').addEventListener('input',function(){
 const query=this.value.toLowerCase();
 document.querySelectorAll('tbody tr').forEach(function(row){
  row.hidden=!row.textContent.toLowerCase().includes(query);
 });
});
</script></html>
"""
    )
