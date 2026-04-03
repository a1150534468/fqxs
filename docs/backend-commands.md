# Backend Management Commands

## Create Initial Admin User

Run the following command from the `backend/` directory to create the initial admin account:

```bash
.venv/bin/python manage.py create_admin
```

Default credentials:

- Username: `admin`
- Password: `admin123`
- Email: `admin@example.com`

The command is idempotent. If the admin user already exists, it will not create a duplicate account.
