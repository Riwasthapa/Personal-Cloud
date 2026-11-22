# Personal Cloud

A self-hosted personal cloud storage application built with Django and Python.

## Features

- User registration and authentication
- Email-based login
- Password validation
- Protected user dashboard
- Single and bulk file uploads
- User-specific file listing
- File downloads
- Secure file deletion with ownership checks
- Local file storage

## Tech Stack

- Python 3.10
- Django 5.2
- SQLite
- HTML and CSS
- python-dotenv

## Project Structure

```text
Personal Cloud/
├── accounts/
├── config/
├── dashboard/
├── storage/
├── media/
├── manage.py
├── requirements.txt
└── README.md
```

## Installation

Clone the repository:

```bash
git clone https://github.com/Riwasthapa/Personal-Cloud.git
cd Personal-Cloud
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Configuration

Create a `.env` file in the project root:

```env
DJANGO_SECRET_KEY=your-secret-key
```

Generate a secret key using Django's `get_random_secret_key()` utility.

## Database Setup

```bash
python manage.py migrate
```

## Run the Application

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

## Storage

On macOS, uploads are stored in `~/Documents/Personal Cloud` by default. On
Android with Termux, the default is `~/storage/shared/Personal Cloud`, which is
shared with the phone's files and gallery apps. Set `ANDROID_MEDIA_ROOT` in
`.env` to use another directory.

## Run on an Android phone with Termux

The Django app must run on the phone to write uploads to its storage and report
the phone's available space. Install Termux from a supported source, open it,
and grant shared-storage access:

```bash
termux-setup-storage
pkg update
pkg install python git
```

Copy the current project to the phone (for example, clone the branch containing
your latest changes), then in Termux change into the project directory and run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Use the generated value to create a `.env` file in the project directory:

```env
DJANGO_SECRET_KEY=paste-generated-value-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

Then continue setup:

```bash
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Open http://127.0.0.1:8000/ in the phone's browser. The app will use
`~/storage/shared/Personal Cloud` for uploads and measure free space on the
phone's shared-storage volume. Register an account on the phone if this is a
fresh installation; its SQLite database is separate from the Mac's.

## Project Status

Under active development.

## Future Improvements

- Responsive cloud-drive interface
- File search and sorting
- Storage quotas
- File previews
- Remote persistent storage
- Production deployment
