PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS races (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    state TEXT NOT NULL,
    office TEXT NOT NULL,
    election_type TEXT NOT NULL,
    election_date TEXT,

    UNIQUE(year, state, office, election_type)
);

CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id INTEGER NOT NULL,
    fec_candidate_id TEXT,
    name TEXT NOT NULL,
    party TEXT NOT NULL,
    incumbent INTEGER NOT NULL DEFAULT 0,
    votes INTEGER,
    vote_share REAL,
    won INTEGER,

    FOREIGN KEY (race_id) REFERENCES races(id)
);

CREATE TABLE IF NOT EXISTS finance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    total_receipts REAL,
    total_disbursements REAL,
    cash_on_hand REAL,
    coverage_end_date TEXT,

    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);
