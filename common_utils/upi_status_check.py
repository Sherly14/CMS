import copy
import hashlib

import requests

url = 'http://114.143.22.139/'

params = {
    "apiPassword": "EE560B75E235E2180107D0160",
}


def get_payment_status(tran_id):
    import ipdb; ipdb.set_trace()
    req_param = copy.copy(params)
    req_param['transactionId'] = tran_id
    req_param['PayProMID'] = '1263'
    checksum = '%s%s%s%s' % (
        req_param['apiPassword'],
        req_param['PayProMID'],
        params['transactionId'],
        "D22qbAyeMaY1MW6FX2+23Q=="
    )
    req_param['checksum'] = checksum
    try:
        response = requests.post(
            '{}/PayProUPI/live/upi/statusCall?partnerId={}&request=JSON_String'.format(
                url,
                "P1263",
            ),
            req_param,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        return response.json()
    except:
        return {}
