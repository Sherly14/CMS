from common_utils.upi_status_check import get_payment_status
from zrpayment.models import Payments


def poll_payments_for_lastest_status():
    payments = Payments.objects.filter(status__in=['P'])
    # TODO: define status field in Payments model
    print 'polling payments status for queryset ', payments

    for payment_obj in payments:
        response = get_payment_status(payment_obj.txn_id)
        if response:
            try:
                if response['status'] != payment_obj.status:
                    payment_obj.status = response['status']
                    if payment_obj.transaction_response_json:
                        payment_obj.transaction_response_json.append(response)
                    else:
                        payment_obj.transaction_response_json = [response]
                    payment_obj.save()
            except:
                pass
