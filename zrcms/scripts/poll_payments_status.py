from common_utils.upi_status_check import get_payment_status
from zrpayment.models import Payments


def poll_transaction_status_for_refund():
    payments = Payments.objects.all()
    # TODO: define status field in Payments model
    # payments = Payments.objects.filter(status='P')
    print 'polling payments status for queryset ', payments

    for payment_obj in payments:
        response = get_payment_status(payment_obj.txn_id)
        if response:
            try:
                payment_obj.status = response['status']
                payment_obj.save()
            except:
                pass
