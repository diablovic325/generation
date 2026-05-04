# Generation Justice

This folder contains a Python/FastAPI membership site.

## Files

- `main.py` - the website backend and API routes.
- `templates/` - HTML pages.
- `static/css/styles.css` - website styles.
- `static/js/app.js` - button behavior and API calls.
- `generation_justice.db` - SQLite database created automatically after launch.
- `requirements.txt` - Python packages required to run the site.
- `run_site.bat` - Windows launch script.

## How to Run

1. Double-click `run_site.bat`.
2. Wait until the terminal shows the local address.
3. Open the address shown in the terminal, usually `http://127.0.0.1:8000`.

The first launch may install packages. After that, the site starts faster.

If port `8000` is already busy, `run_site.bat` automatically starts the site on `8001`.

## Demo Login

- Email: `demo@generationjustice.org`
- Password: `demo123`

You can also create a new member on the Membership page.
