import os
import sys
import django
import datetime

cur_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(cur_dir, '..'))  # NOQA
sys.path.append(os.path.join(cur_dir, '..', '..'))
sys.path.append(os.path.join(cur_dir, '..', '..', 'zrcms'))
# import settings  # NOQA
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')  # NOQA
# from django.conf import settings
# settings.configure()
django.setup()  # NOQA


from loan.views import get_repayments


get_repayments(date=datetime.datetime.today().strftime("%Y-%m-%d"))
