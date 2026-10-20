JOILE FIZZ ERP — ACCOUNT REGISTRATION UPDATE

Files: index.html, server.py, requirements.txt

New feature:
- Sign-in page has a “Create a new account” option.
- New accounts are inserted into the server SQLite users table.
- Passwords are stored as secure password hashes, not plain text.
- Public self-registration assigns Viewer (read-only) role. An Admin must assign appropriate access; public users cannot register themselves as Admin.
- Existing Admin can continue creating employee accounts and assigning roles from the Employee account management panel.

Deploy to Render:
1. Replace index.html and server.py in your GitHub repository with these versions.
2. Keep requirements.txt and the existing Render start command: gunicorn server:app
3. Render should redeploy automatically after the GitHub commit. Wait for deployment to finish, then refresh the website.
4. Test “Create a new account” using a new username and a password at least 14 characters long.

IMPORTANT STORAGE NOTE:
The app uses SQLite. On Render, a local SQLite file may be lost when the service is redeployed/restarted unless a persistent disk is attached and JOILE_DB_PATH points to that disk. Before using real company data, configure persistent storage (or a managed database) and verify backups. This update adds server-side account creation, but does not by itself migrate all ERP business records from browser localStorage into the server database.
