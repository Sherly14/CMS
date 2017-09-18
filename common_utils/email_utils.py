import os

from django.core.mail import send_mail
from django.conf import settings as dj_settings
from django.template import Context, Template


cur_dir = os.path.dirname(os.path.realpath(__file__))
email_templates = os.path.join(cur_dir, '..', 'email_templates')


def send_email(
    subject, to_email, template_name, context, is_html=False
):
    tmpl_path = os.path.join(email_templates, template_name)
    if not os.path.isfile(tmpl_path):
        raise Exception("Invalid email template (%s)" % template_name)

    rendered_context = None
    text_content = ''
    html_content = ''
    with open(tmpl_path) as f:
        file_content = f.read()
        template = Template(file_content)
        c = Context(context)
        rendered_context = template.render(c)

    if is_html:
        html_content = rendered_context
    else:
        text_content = rendered_context

    send_mail(
        subject,
        text_content,
        dj_settings.FROM_EMAIL,
        [to_email],
        html_message=html_content,
        fail_silently=False,
    )
