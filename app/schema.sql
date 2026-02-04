CREATE TABLE IF NOT EXISTS raw_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  device_id TEXT NOT NULL,
  line_id TEXT NOT NULL,
  station_id TEXT,
  event_type TEXT NOT NULL,
  unit_id TEXT,
  cycle_time REAL,
  defect_code TEXT,
  stop_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_ts ON raw_events(ts);
CREATE INDEX IF NOT EXISTS idx_raw_line_ts ON raw_events(line_id, ts);
CREATE INDEX IF NOT EXISTS idx_raw_unit ON raw_events(unit_id);

CREATE TABLE IF NOT EXISTS summary_shift (
  date TEXT NOT NULL,
  shift TEXT NOT NULL,              
  line_id TEXT NOT NULL,
  produced_count INTEGER NOT NULL DEFAULT 0,
  defect_count INTEGER NOT NULL DEFAULT 0,
  stop_minutes INTEGER NOT NULL DEFAULT 0,
  avg_cycle_time REAL,
  last_event_ts INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (date, shift, line_id)
);

CREATE INDEX IF NOT EXISTS idx_summary_date_line
ON summary_shift(date, line_id);
