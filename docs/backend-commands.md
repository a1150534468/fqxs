# Backend Management Commands

## Environment Assumption

All commands below are intended to be run from the `backend/` directory with the local virtual environment available:

```bash
cd backend
```

## Create Initial Admin User

Create the initial admin superuser:

```bash
.venv/bin/python manage.py create_admin
```

Default credentials:

- Username: `admin`
- Password: `admin123`
- Email: `admin@example.com`

The command is idempotent. If the admin user already exists, it will not create a duplicate account.

## Django Migrations

Generate migrations:

```bash
.venv/bin/python manage.py makemigrations
```

Apply migrations:

```bash
.venv/bin/python manage.py migrate
```

Show migration status:

```bash
.venv/bin/python manage.py showmigrations
```

## Development Server

Run the Django development server:

```bash
.venv/bin/python manage.py runserver 0.0.0.0:8000
```

## Test Suite

Run all backend tests:

```bash
.venv/bin/python -m pytest -v
```

Run only user-related tests:

```bash
.venv/bin/python -m pytest apps/users/tests.py -v
```
