# PostgreSQL: local ↔ Render

## Active connection (local)

Django reads `POSTGRES_*` from `.env`. **Local PostgreSQL is active**; Render block is commented out.

For Render: comment local block, uncomment Render block, set `POSTGRES_SSL=require`.

SSL for PostgreSQL is enabled only when `POSTGRES_SSL=require` is set in `.env`.
If you previously ran `pg_restore` with `$env:PGSSLMODE="require"`, clear it in PowerShell:
`Remove-Item Env:PGSSLMODE -ErrorAction SilentlyContinue`
(or use `run.bat`, which clears it automatically).

## Copy local data to Render (already done once)

Dump was saved as `local_beautydb.dump` (gitignored). To repeat:

```powershell
# 1) Dump local (use local password)
$env:PGPASSWORD="YOUR_LOCAL_PASSWORD"
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -h localhost -p 5433 -U postgres -d beautydb -Fc -f local_beautydb.dump

# 2) Restore to Render (use Render password from dashboard)
$env:PGPASSWORD="YOUR_RENDER_PASSWORD"
$env:PGSSLMODE="require"
& "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" `
  -h dpg-d8c7dpuq1p3s7381n7dg-a.oregon-postgres.render.com `
  -p 5432 -U root -d beautydb_32a8 `
  --clean --if-exists --no-owner --no-acl local_beautydb.dump
```

Alternative (schema only via Django, then data):

```powershell
python manage.py migrate
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 -o data.json
# switch .env to target DB
python manage.py loaddata data.json
```

## Verify

```powershell
python manage.py migrate --check
python manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.count())"
```
