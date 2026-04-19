# ⚙️ Installation

This guide explains how to install, configure, and run the **SEO Crawler Django project**, including how to start and use the API layer.

---

# 📦 1. Prerequisites

Make sure you have:

- Python 3.10+
- pip (latest version)
- Git
- Virtualenv (recommended)
- PostgreSQL  14.16
- Node is NOT required (backend only)

---

# 📥 2. Clone the Project
git clone https://github.com/your-username/seocrawler.git
cd seocrawler

# Create Virtual Environment
# 1.Windows
python -m venv venv
venv\Scripts\activate
# 2.Mac / Linux
python3 -m venv venv
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt

# Install Playwright Browsers
# Required for JS-rendered pages.
playwright install

# Configure Database
Default (SQLite)

No setup required.

PostgreSQL (optional)

Update settings.py:

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "seocrawler",
        "USER": "postgres",
        "PASSWORD": "yourpassword",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

# Run Migrations
python manage.py makemigrations
python manage.py migrate

# Run Django Server (API Backend)
python manage.py runserver

# Server will start at:

http://127.0.0.1:8000/

#Run Crawler via Command Line (Alternative)
python manage.py crawl https://example.com
