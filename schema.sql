CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT,
    last_name TEXT,
    notes TEXT,
    score REAL DEFAULT 0.0,
    UNIQUE(first_name, last_name)
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS person_tags (
    person_id INTEGER,
    tag_id INTEGER,
    PRIMARY KEY (person_id, tag_id),
    FOREIGN KEY (person_id) REFERENCES people(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

CREATE TABLE IF NOT EXISTS encounters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER,
    date TEXT,
    intensity INTEGER,
    FOREIGN KEY (person_id) REFERENCES people(id)
);