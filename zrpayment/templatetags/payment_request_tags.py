from django import template

from common_utils.user_utils import is_user_superuser
from zrpayment.models import PaymentRequest

register = template.Library()


@register.filter
def payment_req_cnt(request):
    pr_cnt = 0
    if is_user_superuser(request):
        pr_cnt = PaymentRequest.objects.filter(
            status=0,
            to_user__role__name='ADMINSTAFF',
        ).count()
    elif request.user.zr_admin_user.role.name in ['DISTRIBUTOR', 'SUBDISTRIBUTOR']:
        pr_cnt = PaymentRequest.objects.filter(
            to_user=request.user.zr_admin_user.zr_user,
            status=0
        ).exclude(from_user=request.user.zr_admin_user.zr_user).count()

    return pr_cnt
