from celery import task

from zruser.views import get_report_excel
from common_utils.user_utils import push_file_to_s3
from common_utils import email_utils


@task
def send_dashboard_report(report_params):
    report_file_path = get_report_excel(report_params)
    file_name = report_file_path.split('/')[-1]
    report_link = push_file_to_s3(report_file_path, file_name, "zrupee-reports")

    email_utils.send_email_multiple(
        'Your dashboard Report is ready',
        report_params.get('email_list'),
        'report_email',
        {
            'report_link': report_link
        },
        is_html=True
    )