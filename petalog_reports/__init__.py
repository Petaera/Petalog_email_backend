"""PetaLog daily report service.

Package layout:

    config.py       settings read from the environment
    timeutil.py     IST business-day helpers
    formatting.py   money / number / date formatting for emails
    auth.py         caller authentication for the HTTP API
    repository.py   all Supabase reads and writes
    models.py       plain data objects shared by the modules below
    metrics.py      daily figures, using the same rules as the PetaLog app
    builder.py      turns raw data into an owner's report
    render/         HTML + plain-text email rendering (Jinja2)
    exports.py      Excel / CSV attachments
    mailer.py       MIME building and AWS SES delivery
    deliveries.py   send history and duplicate protection (report_deliveries)
    scheduler.py    who is due for a report, and for which day
    service.py      orchestration used by the API
    api.py          Flask routes
"""

__version__ = "2.0.0"
