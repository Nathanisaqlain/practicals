JOILE FIZZ ERP — SECURE LOGIN IMPLEMENTATION PACKAGE

This package adds a server-side login gate and employee account-management UI to the existing ERP, plus a Flask backend with hashed passwords, HTTP-only sessions, Admin-only user management, role checks, and a version-checked protected data API.

IMPORTANT IMPLEMENTATION STATUS
The login and employee-management UI calls the protected server API. However, the existing ERP's business forms still use browser localStorage for their business records. They are NOT yet wired to /api/data. Therefore this is an authentication integration starter, not a complete shared-database migration. Do not enter real financial data or assume all modules are protected by roles until that migration and per-module authorization are completed. The legacy Google Sheets sync controls were removed from the page so the old public endpoint is not used by this package.

DEPLOYMENT
1. Use a Python web host that supports Flask and persistent disk. For multiple application instances, change SQLite to managed PostgreSQL before production.
2. Upload index.html, server.py, requirements.txt.
3. Configure environment variable JOILE_SECRET_KEY as a long random secret in the host's secret settings. Keep COOKIE_SECURE=1 on HTTPS.
4. Start command: gunicorn server:app
5. Visit /api/setup once with a JSON POST body such as {"username":"your-admin-name","password":"use-a-unique-password-at-least-14-chars"}. Use an API client or host console; do not put the password into a public link.
6. After creating the admin, disable/remove the /api/setup route and redeploy.
7. Sign in through the website. Admin can create employee users with a long unique password and roles Accountant, Sales, Stock/Warehouse, or Viewer.

ROLE RULES
Admin: account management and all sections.
Accountant: finance/accounting-related sections.
Sales: customer, item, sales invoice and delivery challan sections.
Stock/Warehouse: items, delivery challan and stock movements.
Viewer: limited read-only section list.

BEFORE REAL USE
- Wire all ERP reads/writes from localStorage to authenticated /api/data or preferably normalized per-module API routes.
- Enforce permissions per module and per record on the server; hiding navigation is not security.
- Add CSRF protection, login rate limiting, password reset, audit logs, backups/restore tests, and managed PostgreSQL for multi-instance deployments.
- Test using dummy records. No live website has been deployed from this package; deployment requires your hosting account.
