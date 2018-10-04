import requests

BHASHSMS_BASE_URL = 'http://bhashsms.com/api/'
BHASHSMS_USERNAME = 'zrupee'
BHASHSMS_PASSWORD = 'lipl@1712'
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


def wallet_sms(payment_request, zr_wallet):
    if not payment_request or not zr_wallet:
        print 'payment_request or zr_wallet is None'
        return

    phone = payment_request.from_user.mobile_no  # prod
    accounting_entry = "credited" if payment_request.amount >= 0 else "debited"
    text = 'Hi ' + str(payment_request.from_user.first_name).title() + ' ' + \
           str(payment_request.from_user.last_name).title() + \
           ', your Zrupee Wallet is ' + accounting_entry + ' with Rs. ' + \
           str(abs(payment_request.amount)) + '. Your current Wallet Balance is Rs. ' + \
           str(zr_wallet.get_total_balance())
    try:
        send_sms(sender='ZRUPEE', phone=phone,
                 text=text, priority=BHASHSMS_PRIORITY['ndnd'], stype='normal')
    except Exception as e:
        print 'error - ', e
