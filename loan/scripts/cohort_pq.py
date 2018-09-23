import os
import sys
import django


cur_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(cur_dir, '..'))  # NOQA
sys.path.append(os.path.join(cur_dir, '..', '..'))
sys.path.append(os.path.join(cur_dir, '..', '..', 'zrcms'))

# import settings  # NOQA
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')  # NOQA
django.setup()  # NOQA

from loan.views import cohort_pq


cohort_pq()
