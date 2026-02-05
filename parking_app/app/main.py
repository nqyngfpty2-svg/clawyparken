from __future__ import annotations

import secrets
from datetime import datetime, timedelta, date
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import connect, migrate
from .owners import ensure_owner_codes
from .plan_labels import ensure_admin_token, load_labels, save_labels, render_annotated, PLAN_IMAGE
# anonym mode: no outbound email

app = FastAPI(title="Parkplatz-Share")

BASE_DIR = __import__("pathlib").Path(__file__).resolve().parents[1]
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))
TEMPLATES.env.globals["year"] = datetime.utcnow().year

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Booking/offer horizon. Previously 90 days; intentionally generous so owners can plan far ahead.
MAX_BOOK_AHEAD_DAYS = 3650  # ~10 years
OWNER_WITHDRAW_MIN_DAYS = 1  # owner must withdraw at least 1 day before


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def parse_day(s: str) -> date:
    y, m, d = map(int, s.split("-"))
    return date(y, m, d)


def berlin_day_list(start_day: str, days: int) -> list[str]:
    dt = parse_day(start_day)
    return [(dt + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]


def daterange(start: date, end: date):
    # inclusive
    cur = start
    while cur <= end:
        yield cur
        cur = cur + timedelta(days=1)


def init_spots() -> None:
    mapping = ensure_owner_codes()  # P01->CODE
    with connect() as con:
        for spot, code in mapping.items():
            con.execute(
                "INSERT OR IGNORE INTO spots(name, owner_code) VALUES(?, ?)",
                (spot, code),
            )
        con.commit()


@app.on_event("startup")
def _startup() -> None:
    migrate()
    init_spots()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return TEMPLATES.TemplateResponse("home.html", {"request": request})


@app.get("/series", response_class=HTMLResponse)
def series_form(request: Request, spot: str = "", start: str = "", end: str = ""):
    spots = [f"P{i:02d}" for i in range(1, 61)]
    return TEMPLATES.TemplateResponse(
        "series.html",
        {
            "request": request,
            "spots": spots,
            "prefill_spot": spot if spot in spots else "",
            "prefill_start": start,
            "prefill_end": end,
            "maxAhead": MAX_BOOK_AHEAD_DAYS,
        },
    )


@app.post("/series", response_class=HTMLResponse)
def series_book(
    request: Request,
    spot: str = Form(...),
    start_day: str = Form(...),
    end_day: str = Form(...),
    mode: str = Form(...),
    weekdays: Optional[list[str]] = Form(None),
):
    spot = spot.strip().upper()

    try:
        start = parse_day(start_day)
        end = parse_day(end_day)
    except Exception:
        return TEMPLATES.TemplateResponse(
            "series.html",
            {
                "request": request,
                "spots": [f"P{i:02d}" for i in range(1, 61)],
                "prefill_spot": spot,
                "prefill_start": start_day,
                "prefill_end": end_day,
                "maxAhead": MAX_BOOK_AHEAD_DAYS,
                "error": "Ungültiges Datum.",
            },
            status_code=400,
        )

    if end < start:
        return TEMPLATES.TemplateResponse(
            "series.html",
            {
                "request": request,
                "spots": [f"P{i:02d}" for i in range(1, 61)],
                "prefill_spot": spot,
                "prefill_start": start_day,
                "prefill_end": end_day,
                "maxAhead": MAX_BOOK_AHEAD_DAYS,
                "error": "Ende liegt vor Start.",
            },
            status_code=400,
        )

    if mode not in ("hard", "soft"):
        mode = "hard"

    allowed_wd = set()
    for w in (weekdays or []):
        try:
            wi = int(w)
        except Exception:
            continue
        if 0 <= wi <= 6:
            allowed_wd.add(wi)
    if not allowed_wd:
        return TEMPLATES.TemplateResponse(
            "series.html",
            {
                "request": request,
                "spots": [f"P{i:02d}" for i in range(1, 61)],
                "prefill_spot": spot,
                "prefill_start": start_day,
                "prefill_end": end_day,
                "maxAhead": MAX_BOOK_AHEAD_DAYS,
                "error": "Bitte mindestens einen Wochentag wählen.",
            },
            status_code=400,
        )

    today = date.today()
    max_day = today + timedelta(days=MAX_BOOK_AHEAD_DAYS)

    base = str(request.base_url).rstrip("/")

    def reason_for_day(d: date, spot_id: int) -> Optional[str]:
        day_s = d.strftime("%Y-%m-%d")
        if d < today:
            return "liegt in der Vergangenheit"
        if d > max_day:
            return "liegt außerhalb der 90-Tage-Grenze"
        # must have offer
        off = con.execute("SELECT 1 FROM offers WHERE spot_id=? AND day=?", (spot_id, day_s)).fetchone()
        if not off:
            return "nicht angeboten"
        # check booking collision
        existing = con.execute("SELECT status FROM bookings WHERE spot_id=? AND day=?", (spot_id, day_s)).fetchone()
        if existing and existing["status"] == "active":
            return "bereits gebucht"
        return None

    booked: list[dict] = []
    failed: list[dict] = []
    hard_failed = False

    with connect() as con:
        row = con.execute("SELECT id FROM spots WHERE name=?", (spot,)).fetchone()
        if not row:
            return PlainTextResponse("Unbekannter Parkplatz", status_code=400)
        spot_id = row["id"]

        # pre-check for hard mode
        targets: list[date] = [d for d in daterange(start, end) if d.weekday() in allowed_wd]

        if mode == "hard":
            for d in targets:
                r = reason_for_day(d, spot_id)
                if r:
                    failed.append({"day": d.strftime("%Y-%m-%d"), "reason": r})
            if failed:
                hard_failed = True
                # no changes
                return TEMPLATES.TemplateResponse(
                    "series_result.html",
                    {
                        "request": request,
                        "spot": spot,
                        "start_day": start_day,
                        "end_day": end_day,
                        "mode": mode,
                        "booked": [],
                        "failed": failed,
                        "hard_failed": True,
                    },
                    status_code=409,
                )

        # soft mode: attempt what we can
        for d in targets:
            day_s = d.strftime("%Y-%m-%d")
            r = reason_for_day(d, spot_id)
            if r:
                failed.append({"day": day_s, "reason": r})
                continue
            token = secrets.token_urlsafe(24)
            con.execute(
                "INSERT OR REPLACE INTO bookings(spot_id, day, booker_email, status, created_at, manage_token) VALUES(?,?,?,?,?,?)",
                (spot_id, day_s, "", "active", now_iso(), token),
            )
            booked.append({"day": day_s, "link": f"{base}/manage/{token}"})

        con.commit()

    return TEMPLATES.TemplateResponse(
        "series_result.html",
        {
            "request": request,
            "spot": spot,
            "start_day": start_day,
            "end_day": end_day,
            "mode": mode,
            "booked": booked,
            "failed": failed,
            "hard_failed": False,
        },
    )


@app.get("/plan/raw.png")
def plan_raw():
    return FileResponse(str(PLAN_IMAGE), media_type="image/png")


@app.get("/plan/annotated.png")
def plan_annotated():
    out = BASE_DIR / "static" / "plan_annotated.png"
    render_annotated(out)
    return FileResponse(str(out), media_type="image/png")


@app.get("/plan/labeler", response_class=HTMLResponse)
def plan_labeler(request: Request, k: str = ""):
    token = ensure_admin_token()
    if k != token:
        return PlainTextResponse("Forbidden", status_code=403)
    return TEMPLATES.TemplateResponse("plan_labeler.html", {"request": request, "token": token, "year": datetime.utcnow().year})


@app.get("/plan/api/labels")
def plan_labels(k: str = ""):
    token = ensure_admin_token()
    if k != token:
        return PlainTextResponse("Forbidden", status_code=403)
    return JSONResponse(load_labels())


@app.post("/plan/api/add")
def plan_add(payload: dict, k: str = ""):
    token = ensure_admin_token()
    if k != token:
        return PlainTextResponse("Forbidden", status_code=403)
    labels = load_labels()
    n = len(labels) + 1
    x = int(payload.get("x"))
    y = int(payload.get("y"))
    labels.append({"n": n, "x": x, "y": y})
    save_labels(labels)
    return JSONResponse(labels)


@app.post("/plan/api/undo")
def plan_undo(k: str = ""):
    token = ensure_admin_token()
    if k != token:
        return PlainTextResponse("Forbidden", status_code=403)
    labels = load_labels()
    if labels:
        labels.pop()
        save_labels(labels)
    return JSONResponse(labels)


@app.post("/plan/api/reset")
def plan_reset(k: str = ""):
    token = ensure_admin_token()
    if k != token:
        return PlainTextResponse("Forbidden", status_code=403)
    labels = []
    save_labels(labels)
    return JSONResponse(labels)


@app.get("/day/{day}", response_class=HTMLResponse)
def day_view(request: Request, day: str):
    # list offered spots + booking status
    with connect() as con:
        offers = con.execute(
            """
            SELECT s.name AS spot, s.id AS spot_id,
                   o.id AS offer_id,
                   b.status AS booking_status,
                   b.booker_email AS booker_email
            FROM offers o
            JOIN spots s ON s.id=o.spot_id
            LEFT JOIN bookings b ON b.spot_id=o.spot_id AND b.day=o.day
            WHERE o.day=?
            ORDER BY s.name
            """,
            (day,),
        ).fetchall()
    return TEMPLATES.TemplateResponse(
        "day.html",
        {"request": request, "day": day, "offers": offers, "maxAhead": MAX_BOOK_AHEAD_DAYS, "year": datetime.utcnow().year},
    )


@app.post("/book", response_class=HTMLResponse)
def book(
    request: Request,
    day: str = Form(...),
    spot: str = Form(...),
):
    token = secrets.token_urlsafe(24)
    with connect() as con:
        row = con.execute("SELECT id FROM spots WHERE name=?", (spot,)).fetchone()
        if not row:
            return PlainTextResponse("Unbekannter Parkplatz", status_code=400)
        spot_id = row["id"]
        # must have offer
        off = con.execute("SELECT 1 FROM offers WHERE spot_id=? AND day=?", (spot_id, day)).fetchone()
        if not off:
            return PlainTextResponse("Dieser Parkplatz ist an dem Tag nicht angeboten.", status_code=400)
        # check booking collision
        existing = con.execute("SELECT status FROM bookings WHERE spot_id=? AND day=?", (spot_id, day)).fetchone()
        if existing and existing["status"] == "active":
            return PlainTextResponse("Schon gebucht.", status_code=409)

        con.execute(
            "INSERT OR REPLACE INTO bookings(spot_id, day, booker_email, status, created_at, manage_token) VALUES(?,?,?,?,?,?)",
            (spot_id, day, "", "active", now_iso(), token),
        )
        con.commit()

    # No e-mail: show booking code immediately
    return RedirectResponse(url=f"/manage/{token}", status_code=303)


@app.get("/manage/{token}", response_class=HTMLResponse)
def manage(request: Request, token: str):
    with connect() as con:
        b = con.execute(
            """SELECT b.id, b.day, b.status, b.booker_email, s.name as spot
               FROM bookings b JOIN spots s ON s.id=b.spot_id
               WHERE b.manage_token=?""",
            (token,),
        ).fetchone()
    if not b:
        return PlainTextResponse("Ungültiger Link.", status_code=404)
    return TEMPLATES.TemplateResponse("manage.html", {"request": request, "b": b, "token": token, "year": datetime.utcnow().year})


@app.get("/manage/{token}/download")
def download_booking_link(request: Request, token: str):
    # Return a simple text file with the manage URL.
    with connect() as con:
        b = con.execute("SELECT 1 FROM bookings WHERE manage_token=?", (token,)).fetchone()
    if not b:
        return PlainTextResponse("Ungültiger Link.", status_code=404)
    base = str(request.base_url).rstrip("/")
    link = f"{base}/manage/{token}"
    content = f"Buchungslink (bitte speichern):\n{link}\n"
    headers = {"Content-Disposition": f"attachment; filename=booking-link-{token[:6]}.txt"}
    return PlainTextResponse(content, headers=headers)


@app.post("/manage/{token}/cancel")
def cancel_booking(request: Request, token: str, reason: str = Form("")):
    with connect() as con:
        b = con.execute(
            "SELECT id, status FROM bookings WHERE manage_token=?",
            (token,),
        ).fetchone()
        if not b:
            return PlainTextResponse("Ungültiger Link.", status_code=404)
        if b["status"] != "active":
            return RedirectResponse(url=f"/manage/{token}", status_code=303)
        con.execute(
            "UPDATE bookings SET status='cancelled_by_booker', cancelled_at=?, cancel_reason=? WHERE manage_token=?",
            (now_iso(), reason.strip()[:200], token),
        )
        con.commit()
    return RedirectResponse(url=f"/manage/{token}", status_code=303)


@app.get("/owner", response_class=HTMLResponse)
def owner_login(request: Request):
    return TEMPLATES.TemplateResponse("owner_login.html", {"request": request, "year": datetime.utcnow().year})


@app.get("/owner/portal", response_class=HTMLResponse)
def owner_portal_get(request: Request, code: str, p: int = 0):
    code = (code or "").strip().upper()
    if p < 0:
        p = 0

    page_size = 14

    with connect() as con:
        spot = con.execute("SELECT id, name FROM spots WHERE owner_code=?", (code,)).fetchone()
        if not spot:
            return RedirectResponse(url="/owner", status_code=303)

        today_d = date.today()
        max_day = today_d + timedelta(days=MAX_BOOK_AHEAD_DAYS)

        start_d = today_d + timedelta(days=p * page_size)
        if start_d > max_day:
            start_d = max_day

        start_s = start_d.strftime("%Y-%m-%d")
        # only show remaining days up to max_day
        remaining = (max_day - start_d).days + 1
        n_days = min(page_size, max(0, remaining))

        days = berlin_day_list(start_s, n_days)
        rows = []
        for day in days:
            off = con.execute("SELECT 1 FROM offers WHERE spot_id=? AND day=?", (spot["id"], day)).fetchone()
            bk = con.execute("SELECT status, booker_email FROM bookings WHERE spot_id=? AND day=?", (spot["id"], day)).fetchone()
            rows.append({
                "day": day,
                "offered": bool(off),
                "booking_status": (bk["status"] if bk else None),
                "booker_email": (bk["booker_email"] if bk else None),
            })

    page_start = days[0] if days else start_s
    page_end = days[-1] if days else start_s
    has_prev = p > 0
    has_next = (start_d + timedelta(days=page_size)) <= max_day

    return TEMPLATES.TemplateResponse(
        "owner.html",
        {
            "request": request,
            "spot": spot["name"],
            "code": code,
            "rows": rows,
            "p": p,
            "has_prev": has_prev,
            "has_next": has_next,
            "page_start": page_start,
            "page_end": page_end,
            "year": datetime.utcnow().year,
        },
    )


@app.get("/owner/bookings", response_class=HTMLResponse)
def owner_bookings(request: Request, code: str, p: int = 0, portal_p: int = 0):
    code = (code or "").strip().upper()
    if p < 0:
        p = 0
    if portal_p < 0:
        portal_p = 0

    page_size = 50
    offset = p * page_size

    with connect() as con:
        spot = con.execute("SELECT id, name FROM spots WHERE owner_code=?", (code,)).fetchone()
        if not spot:
            return RedirectResponse(url="/owner", status_code=303)

        total = con.execute("SELECT COUNT(*) AS c FROM bookings WHERE spot_id=?", (spot["id"],)).fetchone()["c"]
        rows = con.execute(
            """
            SELECT day, status, created_at, cancelled_at, cancel_reason
            FROM bookings
            WHERE spot_id=?
            ORDER BY day DESC
            LIMIT ? OFFSET ?
            """,
            (spot["id"], page_size, offset),
        ).fetchall()

    has_prev = p > 0
    has_next = (offset + page_size) < total

    return TEMPLATES.TemplateResponse(
        "owner_bookings.html",
        {
            "request": request,
            "spot": spot["name"],
            "code": code,
            "rows": rows,
            "p": p,
            "has_prev": has_prev,
            "has_next": has_next,
            "portal_p": portal_p,
            "year": datetime.utcnow().year,
        },
    )


@app.post("/owner", response_class=HTMLResponse)
def owner_portal(request: Request, code: str = Form(...)):
    code = code.strip().upper()
    with connect() as con:
        spot = con.execute("SELECT id, name FROM spots WHERE owner_code=?", (code,)).fetchone()
        if not spot:
            return TEMPLATES.TemplateResponse(
                "owner_login.html",
                {"request": request, "error": "Code unbekannt."},
                status_code=401,
            )

    return RedirectResponse(url=f"/owner/portal?code={code}&p=0", status_code=303)


@app.post("/owner/offer")
def owner_offer(code: str = Form(...), day: str = Form(...), p: int = Form(0)):
    code = code.strip().upper()
    with connect() as con:
        spot = con.execute("SELECT id, name FROM spots WHERE owner_code=?", (code,)).fetchone()
        if not spot:
            return PlainTextResponse("Code unbekannt", status_code=401)
        con.execute(
            "INSERT OR IGNORE INTO offers(spot_id, day, created_at) VALUES(?,?,?)",
            (spot["id"], day, now_iso()),
        )
        con.commit()
    return RedirectResponse(url=f"/owner/portal?code={code}&p={p}", status_code=303)


@app.post("/owner/offer_series")
def owner_offer_series(
    code: str = Form(...),
    start_day: str = Form(...),
    end_day: str = Form(...),
    weekdays: Optional[list[str]] = Form(None),
    p: int = Form(0),
):
    """Create offers for a date range on selected weekdays.

    weekdays: list of "0".."6" where 0=Mon.
    """
    code = code.strip().upper()

    try:
        start = parse_day(start_day)
        end = parse_day(end_day)
    except Exception:
        return PlainTextResponse("Ungültiges Datum.", status_code=400)

    if end < start:
        return PlainTextResponse("Ende liegt vor Start.", status_code=400)

    # Cap range to keep it sane.
    if (end - start).days > 366:
        return PlainTextResponse("Zeitraum zu groß (max 12 Monate).", status_code=400)

    allowed_wd = set()
    for w in (weekdays or []):
        try:
            wi = int(w)
        except Exception:
            continue
        if 0 <= wi <= 6:
            allowed_wd.add(wi)
    if not allowed_wd:
        return PlainTextResponse("Bitte mindestens einen Wochentag wählen.", status_code=400)

    today = date.today()
    max_day = today + timedelta(days=MAX_BOOK_AHEAD_DAYS)

    inserted = 0
    with connect() as con:
        spot = con.execute("SELECT id, name FROM spots WHERE owner_code=?", (code,)).fetchone()
        if not spot:
            return PlainTextResponse("Code unbekannt", status_code=401)

        for d in daterange(start, end):
            if d < today or d > max_day:
                continue
            if d.weekday() not in allowed_wd:
                continue
            con.execute(
                "INSERT OR IGNORE INTO offers(spot_id, day, created_at) VALUES(?,?,?)",
                (spot["id"], d.strftime("%Y-%m-%d"), now_iso()),
            )
            inserted += con.total_changes  # approximate
        con.commit()

    return RedirectResponse(url=f"/owner/portal?code={code}&p={p}", status_code=303)


@app.post("/owner/withdraw_series")
def owner_withdraw_series(
    request: Request,
    code: str = Form(...),
    start_day: str = Form(...),
    end_day: str = Form(...),
    weekdays: Optional[list[str]] = Form(None),
    reason: str = Form(""),
    p: int = Form(0),
):
    code = code.strip().upper()

    try:
        start = parse_day(start_day)
        end = parse_day(end_day)
    except Exception:
        return PlainTextResponse("Ungültiges Datum.", status_code=400)

    if end < start:
        return PlainTextResponse("Ende liegt vor Start.", status_code=400)

    if (end - start).days > 366:
        return PlainTextResponse("Zeitraum zu groß (max 12 Monate).", status_code=400)

    allowed_wd = set()
    for w in (weekdays or []):
        try:
            wi = int(w)
        except Exception:
            continue
        if 0 <= wi <= 6:
            allowed_wd.add(wi)
    if not allowed_wd:
        return PlainTextResponse("Bitte mindestens einen Wochentag wählen.", status_code=400)

    today = date.today()
    max_day = today + timedelta(days=MAX_BOOK_AHEAD_DAYS)

    with connect() as con:
        spot = con.execute("SELECT id, name FROM spots WHERE owner_code=?", (code,)).fetchone()
        if not spot:
            return PlainTextResponse("Code unbekannt", status_code=401)

        for d in daterange(start, end):
            if d < today or d > max_day:
                continue
            if d.weekday() not in allowed_wd:
                continue
            day = d.strftime("%Y-%m-%d")
            # enforce: at least 1 day before
            if day <= today.strftime("%Y-%m-%d"):
                continue
            con.execute("DELETE FROM offers WHERE spot_id=? AND day=?", (spot["id"], day))
            b = con.execute(
                "SELECT id, status FROM bookings WHERE spot_id=? AND day=?",
                (spot["id"], day),
            ).fetchone()
            if b and b["status"] == "active":
                con.execute(
                    "UPDATE bookings SET status='cancelled_by_owner', cancelled_at=?, cancel_reason=? WHERE id=?",
                    (now_iso(), (reason.strip() or "Owner hat die Serie zurückgezogen")[:200], b["id"]),
                )

        con.commit()

    return RedirectResponse(url=f"/owner/portal?code={code}&p={p}", status_code=303)


@app.post("/owner/withdraw_all")
def owner_withdraw_all(code: str = Form(...), reason: str = Form(""), p: int = Form(0)):
    """Withdraw all future offers for this owner spot and cancel active bookings.

    Anonym mode: no notifications.
    """
    code = code.strip().upper()
    today = date.today().strftime("%Y-%m-%d")
    with connect() as con:
        spot = con.execute("SELECT id, name FROM spots WHERE owner_code=?", (code,)).fetchone()
        if not spot:
            return PlainTextResponse("Code unbekannt", status_code=401)

        # Cancel active future bookings first
        con.execute(
            """
            UPDATE bookings
            SET status='cancelled_by_owner', cancelled_at=?, cancel_reason=?
            WHERE spot_id=? AND day>? AND status='active'
            """,
            (now_iso(), (reason.strip() or "Owner hat alle Freigaben zurückgezogen")[:200], spot["id"], today),
        )

        # Delete future offers
        con.execute(
            "DELETE FROM offers WHERE spot_id=? AND day>?",
            (spot["id"], today),
        )
        con.commit()

    return RedirectResponse(url=f"/owner/portal?code={code}&p={p}", status_code=303)


@app.post("/owner/withdraw")
def owner_withdraw(request: Request, code: str = Form(...), day: str = Form(...), reason: str = Form(""), p: int = Form(0)):
    code = code.strip().upper()
    with connect() as con:
        spot = con.execute("SELECT id, name FROM spots WHERE owner_code=?", (code,)).fetchone()
        if not spot:
            return PlainTextResponse("Code unbekannt", status_code=401)

        # enforce: at least 1 day before
        # (simple compare strings by date)
        today = datetime.now().strftime("%Y-%m-%d")
        if day <= today:
            return PlainTextResponse("Zu spät: Rückzug nur mindestens 1 Tag vorher.", status_code=400)

        con.execute("DELETE FROM offers WHERE spot_id=? AND day=?", (spot["id"], day))
        b = con.execute(
            "SELECT id, booker_email, manage_token, status FROM bookings WHERE spot_id=? AND day=?",
            (spot["id"], day),
        ).fetchone()
        if b and b["status"] == "active":
            con.execute(
                "UPDATE bookings SET status='cancelled_by_owner', cancelled_at=?, cancel_reason=? WHERE id=?",
                (now_iso(), (reason.strip() or "Owner hat das Angebot zurückgezogen")[:200], b["id"]),
            )
        con.commit()

    # No e-mail notifications in anonym mode.
    return RedirectResponse(url=f"/owner/portal?code={code}&p={p}", status_code=303)
