from celery import task

from common_utils import email_utils
from common_utils.user_utils import push_file_to_s3
from .views import get_passbook_report_csv


@task
def send_passbook_report(report_params):
    # set timeout for mail report download link
    minute = 60
    report_file_path = get_passbook_report_csv(report_params)
    file_name = report_file_path.split('/')[-1]
    bucket_name = "zrupee-reports"
    report_link = push_file_to_s3(report_file_path, file_name, bucket_name, minute * 60)

    email_utils.send_email_multiple(
        'Your Passbook Report is ready',
        report_params.get('email_list'),
        'payment_report_email',
        {
            'report_link': report_link,
            'minute': minute,
        },
        is_html=True
    )
