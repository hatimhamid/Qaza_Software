# Umoor Qaza Software

Responsive web case management for a community mediation center, backed directly by SQLite and served through Python.

Full documentation is available in [DOCUMENTATION.md](./DOCUMENTATION.md).

## Run

```powershell
python app.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Seed Credentials

- `admin / admin123`
- `editor / editor123`
- `viewer / viewer123`

## Notes

- The SQLite database is created automatically at `data/umoor_qaza.db`.
- CSV export excludes comments, subtasks, and the summary/description field.
