# flask-xampp-openai-db-generator

# Flask + XAMPP MySQL + OpenAI (DB Generator)

A Flask web app that generates a complete database project output (strict JSON), optionally applies the DDL to a local XAMPP MySQL/MariaDB instance, and runs sample reporting queries.

## Features
- Flask UI (`templates/`) and static assets (`static/`)
- OpenAI API integration via environment variable (`OPENAI_API_KEY`)
- MySQL/MariaDB support (XAMPP)
- Applies DDL safely using `CREATE TABLE IF NOT EXISTS`

## Project Structure
```text
.
├── app.py
├── db_xampp.py
├── requirements.txt
├── static/
│   └── style.css
└── templates/
    ├── index.html
    └── results.html


Setup
pip install -r requirements.txt

Create a .env file (do not commit it):
OPENAI_API_KEY=YOUR_KEY_HERE
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=bonus_social_db

Run XAMPP (MySQL) and start the app:
python app.py

Open:
http://127.0.0.1:5000

Author
Ebubekir Taskiran

