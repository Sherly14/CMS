web: NEW_RELIC_CONFIG_FILE=newrelic_staging.ini newrelic-admin run-program gunicorn zrcms.wsgi --max-requests 500 --max-requests-jitter 20 --timeout 30 --graceful-timeout 10 --log-file -
worker: SETUP=heroku python manage.py celery worker --loglevel=info
