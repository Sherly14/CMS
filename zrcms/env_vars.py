import os

ENVIRONMENT = os.getenv('APP_ENVIRONMENT', 'local')

LOCAL_SECRET_KEY = ')cgcw7ffq2&_zbcj-icg5dym7tzsum5#=nf4e5ay4snjp6hl_b'
SECRET_KEY = os.getenv('APP_SECRET_KEY', LOCAL_SECRET_KEY)
