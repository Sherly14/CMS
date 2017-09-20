import calendar
import datetime

import pytz
IST = pytz.timezone('Asia/Kolkata')


def last_week_range():
    date = datetime.date.today()
    year, week, dow = date.isocalendar()

    # Find the first day of the week.
    if dow == 7:
        # Since we want to start with Sunday, let's test for that condition.
        start_date = date
    else:
        # Otherwise, subtract `dow` number days to get the first day
        start_date = date - datetime.timedelta(dow)

    # Now, add 6 for the last day of the week (i.e., count up to Saturday)
    end_date = start_date + datetime.timedelta(6)

    start_date = start_date - datetime.timedelta(7)
    end_date = end_date - datetime.timedelta(7)

    start_date = start_date + datetime.timedelta(days=1)
    end_date = end_date + datetime.timedelta(days=1)
    return (start_date, end_date)


def last_month():
    today_date = datetime.date.today()
    current_month = today_date.month
    current_year = today_date.year
    if current_month == 1:
        current_month = 12
        current_year = current_year - 1
    else:
        current_month -= 1

    start_date, end_date = calendar.monthrange(current_year, current_month)
    start_date = datetime.date(day=start_date, month=current_month, year=current_year)
    end_date = datetime.date(day=end_date, month=current_month, year=current_year)

    return start_date, end_date


def utc_to_ist(dt):
    return dt.astimezone(IST)
