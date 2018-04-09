import os

ENVIRONMENT = os.getenv('APP_ENVIRONMENT', 'local')

LOCAL_SECRET_KEY = ')cgcw7ffq2&_zbcj-icg5dym7tzsum5#=nf4e5ay4snjp6hl_b'
SECRET_KEY = os.getenv('APP_SECRET_KEY', LOCAL_SECRET_KEY)

# EKO credentials
# Trying to get the credentials from environment Variables, falling back to sandbox environment
EKO_INITIATOR_ID = os.getenv('EKO_INITIATOR_ID', '9910028267')
EKO_DEVELOPER_KEY = os.getenv('EKO_DEVELOPER_KEY', 'becbbce45f79c6f5109f848acd540567')
EKO_TRANSACTION_ENQUIRY_URL = os.getenv('EKO_TRANSACTION_ENQUIRY_URL',
                                        'https://staging.eko.co.in:25004/ekoapi/v1/transactions/')


QUICKWALLET_ZR_PARTERNERID = os.getenv('QUICKWALLET_ZR_PARTERNERID', '293')
QUICKWALLET_SECRET = os.getenv('QUICKWALLET_SECRET', '2z9WyZ823Q78kER')
# SET URL IF NEEDED
QUICKWALLET_URL = os.getenv('QUICKWALLET_URL', 'https://uat.quikwallet.com')
QUICKWALLET_API_CRUD_URL = os.getenv('QUICKWALLET_API_CRUD_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/merchants/crud'.format(QUICKWALLET_ZR_PARTERNERID))
QUICKWALLET_API_CARD_URL = os.getenv('QUICKWALLET_API_CARD_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/loyaltycards/create'.format(QUICKWALLET_ZR_PARTERNERID))
QUICKWALLET_API_LISTCARD_URL = os.getenv('QUICKWALLET_API_LISTCARD_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/loyaltycards'.format(QUICKWALLET_ZR_PARTERNERID))
QUICKWALLET_API_LISTCARD_ACTIVATED_URL = os.getenv('QUICKWALLET_API_LISTCARD_ACTIVATED_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/loyaltycards/listactivations'.format(QUICKWALLET_ZR_PARTERNERID))
QUICKWALLET_API_GENERATEOTP_URL = os.getenv('QUICKWALLET_API_GENERATEOTP_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/loyaltycards/generateotp'.format(QUICKWALLET_ZR_PARTERNERID))
QUICKWALLET_API_ISSUE_MOBILE_URL = os.getenv('QUICKWALLET_API_ISSUE_MOBILE_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/loyaltycards/issue'.format(QUICKWALLET_ZR_PARTERNERID))
QUICKWALLET_API_ACTIVATE_CARD_URL = os.getenv('QUICKWALLET_API_ACTIVATE_CARD_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/loyaltycards/activate'.format(QUICKWALLET_ZR_PARTERNERID))
QUICKWALLET_API_RECHARGE_CARD_URL = os.getenv('QUICKWALLET_API_RECHARGE_CARD_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/loyaltycards/recharge'.format(QUICKWALLET_ZR_PARTERNERID))
QUICKWALLET_API_PAY_URL = os.getenv('QUICKWALLET_API_PAY_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/loyaltycards/pay'.format(QUICKWALLET_ZR_PARTERNERID))
QUICKWALLET_API_DEACTIVATE_CARD_URL = os.getenv('QUICKWALLET_API_DEACTIVATE_CARD_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/loyaltycards/deactivate'.format(QUICKWALLET_ZR_PARTERNERID))
QUICKWALLET_PAYMENT_HISTORY_URL = os.getenv('QUICKWALLET_PAYMENT_HISTORY_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/paymenthistory'.format(QUICKWALLET_ZR_PARTERNERID))
QUICKWALLET_CREATE_OFFER_URL = os.getenv('QUICKWALLET_CREATE_OFFER_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/offers/create'.format(QUICKWALLET_ZR_PARTERNERID))
QUICKWALLET_OFFER_LIST_URL = os.getenv('QUICKWALLET_OFFER_LIST_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/offers'.format(QUICKWALLET_ZR_PARTERNERID))
QUICKWALLET_OFFER_ASSIGN_TO_RETAILER_URL = os.getenv('QUICKWALLET_OFFER_ASSIGN_TO_RETAILER_URL',
                                        'https://uat.quikwallet.com/api/partner/{0}/offers/addforoutlet'.format(QUICKWALLET_ZR_PARTERNERID))