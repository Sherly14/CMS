import os

from django.core.mail import send_mail
from django.conf import settings as dj_settings
from django.template import Context, Template


cur_dir = os.path.dirname(os.path.realpath(__file__))
email_templates = os.path.join(cur_dir, '..', 'email_templates')


def send_email(
    subject, to_email, template_name, context
):
    tmpl_path = os.path.join(email_templates, template_name)
    if not os.path.isfile(tmpl_path):
        raise Exception("Invalid email template (%s)" % template_name)

    rendered_context = None
    with open(tmpl_path) as f:
        file_content = f.read()
        template = Template(file_content)
        c = Context(context)

        rendered_context = template.render(c)

    send_mail(
        subject,
        rendered_context,
        dj_settings.FROM_EMAIL,
        [to_email],
        fail_silently=False,
    )
