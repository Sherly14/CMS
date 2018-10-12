import requests

from zrcms.env_vars import BHASHSMS_BASE_URL, BHASHSMS_USERNAME, BHASHSMS_PASSWORD

BHASHSMS_PRIORITY = {
    'ndnd': 'ndnd',
    'dnd': 'dnd'
}
BHASHSMS_SERVICE = {
    'sendmsg': 'sendmsg',
    'schedulemsg': 'schedulemsg',
    'checkbalance': 'checkbalance',
    'getsenderids': 'getsenderids',
    'addsenderid': 'addsenderid',
    'recdlr': 'recdlr'
}


def send_sms(sender='ZRUPEE', phone='', text='', priority='', stype='normal'):
    if phone == '' or text == '' or priority == '':
        print 'Incomplete parameters'
        return
    sms_url = BHASHSMS_BASE_URL + BHASHSMS_SERVICE['sendmsg'] + '.php?' + 'user=' + BHASHSMS_USERNAME \
        + '&pass=' + BHASHSMS_PASSWORD \
        + '&sender=' + sender + '&phone=' + phone \
        + '&text=' + text + '&priority=' + priority + '&stype=' + stype

    try:
        sms_req = requests.get(url=sms_url)
        print 'sms_req response' + sms_req.content
    except requests.RequestException as e:
        print 'error - ', e


def wallet(wallet_transaction):
    if not wallet_transaction:
        print 'SMS: wallet_transaction is None'
        return

    phone = wallet_transaction.wallet.merchant.mobile_no  # prod
    amount = wallet_transaction.dmt_balance + wallet_transaction.non_dmt_balance
    balance = wallet_transaction.dmt_closing_balance + wallet_transaction.non_dmt_closing_balance
    accounting_entry = "credited" if amount >= 0 else "debited"
    text = 'Hi ' + str(wallet_transaction.wallet.merchant.first_name).title() + ' ' + \
           str(wallet_transaction.wallet.merchant.last_name).title() + \
           ', your Zrupee Wallet is ' + accounting_entry + ' with Rs. ' + \
           str(abs(amount)) + '. Wallet Balance - Rs. ' + \
           str(balance)
    try:
        send_sms(sender='ZRUPEE', phone=str(phone),
                 text=text, priority=BHASHSMS_PRIORITY['ndnd'], stype='normal')
    except Exception as e:
        print 'Error - ', e

