web: gunicorn realtime_project.wsgi --log-file -
release: python manage.py migrate && python manage.py createsuperuser --noinput

