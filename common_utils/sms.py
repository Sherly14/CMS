import requests
import locale
from datetime import datetime

from zrcms.env_vars import BHASHSMS_BASE_URL, BHASHSMS_USERNAME, BHASHSMS_PASSWORD, ENVIRONMENT

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
        if ENVIRONMENT == 'PRODUCTION':
            sms_req = requests.get(url=sms_url, timeout=5)
            print str(datetime.now()), 'sms_req response' + sms_req.content
        else:
            print "ENVIRONMENT not PRODUCTION"
            print "sms text - \n", text
            pass
    except requests.RequestException as e:
        print str(datetime.now()), 'error - ', e


def wallet(wallet_transaction):
    if not wallet_transaction:
        print 'SMS: wallet_transaction is None'
        return

    locale.setlocale(locale.LC_NUMERIC, '')

    phone = wallet_transaction.wallet.merchant.mobile_no  # prod

    accounting_entry = "is credited with" if (wallet_transaction.dmt_balance + wallet_transaction.non_dmt_balance) >= 0 else "has been debited for"

    amount = locale.format("%.2f", abs(wallet_transaction.dmt_balance + wallet_transaction.non_dmt_balance), grouping=True)
    balance = locale.format("%.2f", wallet_transaction.dmt_closing_balance + wallet_transaction.non_dmt_closing_balance, grouping=True)

    text = 'Hi ' + str(wallet_transaction.wallet.merchant.first_name).title() + ' ' + \
           str(wallet_transaction.wallet.merchant.last_name).title() + \
           ', your Zrupee Wallet ' + accounting_entry + ' INR ' + \
           str(amount) + '.\nWallet Balance - INR ' + \
           str(balance) + '\nKeep up the Balance!'
    try:
        send_sms(sender='ZRUPEE', phone=str(phone),
                 text=text, priority=BHASHSMS_PRIORITY['ndnd'], stype='normal')
    except Exception as e:
        print 'Error - ', e

