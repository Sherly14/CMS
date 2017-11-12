import copy
import hashlib

import requests

url = 'http://114.143.22.139/'

params = {
    "apiPassword": "EE560B75E235E2180107D0160",
}


def get_payment_status(tran_id):
    '''
    {
    " status ": "CONFIRMED ",
    " message ": "Transaction Successful",
    " transId ":”78790”,
    “checksum”: "BwYx7tYV6uLQNImyQ45MoMgi50+QKitDwBojBWv9E9I+wRCtAGmeTeiNbJ4fk1gJFmgcRvEqXryzi\/u\/tihyyxhaEyNm9281Elb+Da+JyvS8UqU9PEabg2”
    }

    '''
    req_param = copy.copy(params)
    req_param['transactionId'] = tran_id
    checksum = ''.join(params.values())
    params['checksum'] = hashlib.sha512(checksum).hexdigest()
    try:
        response = requests.post('{}/PayProUPI/live/upi/statusCall'.format(url), req_param)
        return response.json
    except:
        return {}
