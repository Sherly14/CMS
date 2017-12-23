import copy
import json
import hashlib
import logging

import requests

from django.conf import settings as dj_settings

logger = logging.getLogger(__name__)
url = dj_settings.UPI_URL

params = {
    "apiPassword": dj_settings.UPI_API_PASSWORD,
}


def get_payment_status(tran_id):
    req_param = copy.copy(params)
    req_param['transactionId'] = tran_id
    req_param['PayProMID'] = dj_settings.UPI_PAY_PRO_MID
    checksum = '%s%s%s%s' % (
        req_param['apiPassword'],
        req_param['PayProMID'],
        req_param['transactionId'],
        dj_settings.UPI_SECRET
    )
    req_param['checksum'] = hashlib.sha512(checksum).hexdigest()
    try:
        response = requests.post(
            '{}/PayProUPI/live/upi/statusCall?partnerId={}&request={}'.format(
                url,
                dj_settings.UPI_PARTNER_ID,
                json.dumps(req_param)
            ),
            data={},
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        return response.json()
    except:
        logger.error("Error occurred while doing request to mosambee API on transaction id(%s)" % (
            tran_id
        ), exc_info=True)
        return {}
