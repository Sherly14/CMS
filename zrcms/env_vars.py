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


QUICKWALLET_ZR_PARTERNERID = os.getenv('QUICKWALLET_ZR_PARTERNERID', '350')
QUICKWALLET_SECRET = os.getenv('QUICKWALLET_SECRET', 'YTPNg4RAC626AP86MyAG1wY3Bvgec70P')
# SET URL IF NEEDED
QUICKWALLET_URL = os.getenv('QUICKWALLET_URL', 'https://server.livquik.com/api/partner/{0}/'.format(QUICKWALLET_ZR_PARTERNERID))

QUICKWALLET_API_CRUD_URL = QUICKWALLET_URL + 'merchants/crud'
QUICKWALLET_API_CARD_URL = QUICKWALLET_URL + 'loyaltycards/create'
QUICKWALLET_API_LISTCARD_URL = QUICKWALLET_URL + 'loyaltycards'
QUICKWALLET_API_LISTCARD_ACTIVATED_URL = QUICKWALLET_URL + 'loyaltycards/listactivations'
QUICKWALLET_API_GENERATEOTP_URL = QUICKWALLET_URL + 'loyaltycards/generateotp'
QUICKWALLET_API_ISSUE_MOBILE_URL = QUICKWALLET_URL + 'loyaltycards/issue'
QUICKWALLET_API_ACTIVATE_CARD_URL = QUICKWALLET_URL + 'loyaltycards/activate'
QUICKWALLET_API_RECHARGE_CARD_URL = QUICKWALLET_URL + 'loyaltycards/recharge'
QUICKWALLET_API_PAY_URL = QUICKWALLET_URL + 'loyaltycards/pay'
QUICKWALLET_API_DEACTIVATE_CARD_URL = QUICKWALLET_URL + 'loyaltycards/deactivate'
QUICKWALLET_PAYMENT_HISTORY_URL = QUICKWALLET_URL + 'paymenthistory'
QUICKWALLET_CREATE_OFFER_URL = QUICKWALLET_URL + 'offers/create'
QUICKWALLET_OFFER_LIST_URL = QUICKWALLET_URL + 'offers'
QUICKWALLET_OFFER_ASSIGN_TO_RETAILER_URL = QUICKWALLET_URL + 'offers/addforoutlet'
QUICKWALLET_OFFER_ASSIGN_TO_OUTLETS_URL = QUICKWALLET_URL + 'offers/addforoutlets'
