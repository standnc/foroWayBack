import os
import re

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

LOG_FILES = {
    "gunicorn-error": "/var/log/gunicorn/error.log",
    "gunicorn-access": "/var/log/gunicorn/access.log",
}

def parse_gunicorn_level(line):
    if "CRITICAL" in line or "FATAL" in line:
        return "CRITICAL"
    if " ERROR " in line or "ERROR " in line or "Traceback (most recent call last)" in line:
        return "ERROR"
    if " WARNING " in line or "WARN " in line:
        return "WARNING"
    if " INFO " in line:
        return "INFO"
    if " DEBUG " in line:
        return "DEBUG"
    return "INFO"

def parse_log(lines, level_filter=None, max_lines=500, search=None):
    levels_order = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2, "INFO": 3, "DEBUG": 4}
    entries = []
    current = None
    for line in lines:
        stripped = line.rstrip("\n")
        if re.match(r"^\[?\d{4}-\d{2}-\d{2}", stripped):
            if current:
                entries.append(current)
            current = {"raw": stripped, "level": parse_gunicorn_level(stripped), "lines": [stripped]}
        else:
            if current:
                current["lines"].append(stripped)
                current["raw"] += "\n" + stripped
                nl = parse_gunicorn_level(stripped)
                if nl in ("ERROR", "CRITICAL") and current["level"] not in ("ERROR", "CRITICAL"):
                    current["level"] = nl
            else:
                entries.append({"raw": stripped, "level": parse_gunicorn_level(stripped), "lines": [stripped]})
    if current:
        entries.append(current)
    if level_filter and level_filter in levels_order:
        min_p = levels_order[level_filter]
        entries = [e for e in entries if levels_order.get(e["level"], 99) <= min_p]
    if search:
        s = search.lower()
        entries = [e for e in entries if s in e["raw"].lower()]
    entries.reverse()
    return entries[:max_lines]


@staff_member_required
def log_view(request):
    source = request.GET.get("source", "gunicorn-error")
    level = request.GET.get("level", "INFO")
    search = request.GET.get("q", "")
    # ?max=abc daba un 500; además hace falta un techo para no renderizar
    # el log entero desde la query string.
    try:
        max_lines = min(max(int(request.GET.get("max", 500)), 1), 2000)
    except (TypeError, ValueError):
        max_lines = 500
    log_path = LOG_FILES.get(source)
    entries = []
    error_msg = None
    file_size = 0
    if log_path and os.path.exists(log_path):
        file_size = os.path.getsize(log_path)
        try:
            with open(log_path, errors="replace") as f:
                all_lines = f.readlines()
                if len(all_lines) > 2000:
                    all_lines = all_lines[-2000:]
            entries = parse_log(all_lines, level_filter=level, max_lines=max_lines, search=search or None)
        except Exception as e:
            error_msg = str(e)
    else:
        error_msg = f"Log file not found: {log_path}"
    context = {
        "title": f"Visor de logs — {source}",
        "entries": entries,
        "source": source,
        "level": level,
        "search": search,
        "max_lines": max_lines,
        "error": error_msg,
        "file_size": file_size,
        "sources": LOG_FILES.keys(),
        "levels": ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        "is_popup": False,
        "has_permission": True,
    }
    return render(request, "admin/log_viewer.html", context)
