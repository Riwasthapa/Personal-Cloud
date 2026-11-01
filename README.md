# Personal Cloud

A self-hosted personal cloud storage application built with Django and Python.

## Features

- User registration and authentication
- Email-based login
- Password validation
- Protected user dashboard
- File uploads
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

Uploaded files are currently stored locally in the `media/uploads/` directory.

## Project Status

Under active development.

## Future Improvements

- Responsive cloud-drive interface
- File search and sorting
- Storage quotas
- File previews
- Remote persistent storage
- Production deployment
