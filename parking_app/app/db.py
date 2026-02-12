from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "parking.sqlite3"


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def migrate() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS spots (
              id INTEGER PRIMARY KEY,
              name TEXT NOT NULL UNIQUE,
              owner_code TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS offers (
              id INTEGER PRIMARY KEY,
              spot_id INTEGER NOT NULL,
              day TEXT NOT NULL, -- YYYY-MM-DD Europe/Berlin
              created_at TEXT NOT NULL,
              UNIQUE(spot_id, day),
              FOREIGN KEY(spot_id) REFERENCES spots(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS bookings (
              id INTEGER PRIMARY KEY,
              spot_id INTEGER NOT NULL,
              day TEXT NOT NULL,
              booker_email TEXT NOT NULL,
              status TEXT NOT NULL, -- active|cancelled_by_owner|cancelled_by_booker
              created_at TEXT NOT NULL,
              cancelled_at TEXT,
              cancel_reason TEXT,
              manage_token TEXT NOT NULL,
              UNIQUE(spot_id, day),
              FOREIGN KEY(spot_id) REFERENCES spots(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_offers_day ON offers(day);
            CREATE INDEX IF NOT EXISTS idx_bookings_day ON bookings(day);
            CREATE INDEX IF NOT EXISTS idx_bookings_email ON bookings(booker_email);
            """
        )
