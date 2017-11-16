import copy
import hashlib

import requests

url = 'http://114.143.22.139/'

params = {
    "apiPassword": "EE560B75E235E2180107D0160",
}


def get_payment_status(tran_id):
    req_param = copy.copy(params)
    req_param['transactionId'] = tran_id
    req_param['PayProMID'] = '1263'
    checksum = ''.join(params.values())
    params['checksum'] = hashlib.sha512(checksum).hexdigest()
    try:
        response = requests.post(
            '{}/PayProUPI/live/upi/statusCall?partnerId={}&request=JSON_String'.format(
                url,
                "P1263",
            ), req_param
        )
        return response.json()
    except:
        return {}
