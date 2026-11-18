# Persistence choice

Owner decision (2026-11-18): use **free Render web + free Render Postgres**, matching Postgres in local Docker Compose. All previews are static files baked into the image. No participants, votes or statuses are stored on the ephemeral web disk.

The free database expires 30 days after creation. The current database was created 2026-11-18 and expires 2026-12-18; DATABASE_EXPIRES_AT is set from Render's receipt. An owner-only reminder appears seven days before expiry (day 23). Before expiry use Export all JSON (full restore format) and Export all CSV (spreadsheet format). Keep these files private: they contain reviewers' names and email addresses. There is no background paid backup service or paid resource.

To rotate: export JSON, create a fresh free Postgres database in the same region, replace DATABASE_URL and DATABASE_EXPIRES_AT in Render, redeploy, enter the owner code, then import the JSON. Import requires an empty board and runs in one transaction. Keep SESSION_SECRET unchanged so existing browser sessions can resume after restoring their session generation. Import deliberately restores those original session identities. CSV is for analysis; import takes JSON. Never delete the old database until you have downloaded and checked the JSON. Free accounts generally permit one free database: if recreation requires removing the old one first, retain and verify an offline export before that destructive step.

Free web sleeps after 15 minutes idle; first requests can take about a minute. Render owns the initial wake-up page before our HTML can load. Once the client is loaded it explains waking and gives requests a 90-second timeout; failed saves show a retry message and do not invent success. Do not promise the app can paint its own screen before Render serves any HTML.

Cost: $0/month within free-tier quotas. No persistent disk is provisioned. Alternative reviewed before the owner decision: paid 512 MB web ($7/month) plus 1 GB persistent disk ($0.25/month), approximately $7.25/month, no fixed database expiry, one instance and brief downtime on deploy; managed paid Postgres supports future scaling at extra cost. Do not upgrade or add billing automatically.

Sources checked 2026-11-18: [Render free tier](https://render.com/docs/free), [persistent disks](https://render.com/docs/disks), [Render's published hosting example and prices](https://render.com/hosting/ghost).
