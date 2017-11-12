from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from django.utils import timezone

from zrpayment.models import PaymentRequest
from zruser.models import ZrUser
from zrwallet.models import Passbook, Wallet


def passbook_open_script():
    """
    This script is to create first passbook entry for all users
    :return: 
    """
    user_objs = ZrUser.objects.all()

    for user in user_objs:
        is_exist_passbook_entry = Passbook.objects.filter(user=user).exists()
        if is_exist_passbook_entry:
            continue

        try:
            wallet = Wallet.objects.get(merchant=user)
        except ObjectDoesNotExist:
            continue

        Passbook.objects.create(
            user=user,
            non_dmt_opening_balance=wallet.non_dmt_balance,
            dmt_opening_balance=wallet.dmt_balance,
            non_dmt_opening_wallet_balance=wallet.non_dmt_balance,
            dmt_opening_wallet_balance=wallet.dmt_balance,
        )


def daily_passbook_script():
    user_objs = ZrUser.objects.all()

    for user in user_objs:

        try:
            wallet = Wallet.objects.get(merchant=user)
        except ObjectDoesNotExist:
            continue

        passbook_last_entry = Passbook.objects.filter(user=user).last()
        if passbook_last_entry:
            # On next day this entry will be updated
            nw = timezone.now()

            # datetime.datetime(2017, 11, 12, 0, 0)
            min_day = timezone.datetime.combine(nw - timezone.timedelta(1), timezone.datetime.min.time())

            # datetime.datetime(2017, 11, 12, 23, 59, 59, 999999)
            max_day = timezone.datetime.combine(nw - timezone.timedelta(1), timezone.datetime.max.time())

            # TODO: here needs approve date instead of modified for precise information
            dmt_wallet_credit = PaymentRequest.objects.filter(from_user=user, at_modified__range=(min_day, max_day)).aggregate(Sum('dmt_amount')).get('dmt_amount__sum')
            non_dmt_wallet_credit = PaymentRequest.objects.filter(from_user=user, at_modified__range=(min_day, max_day)).aggregate(Sum('non_dmt_amount')).get('non_dmt_amount__sum')

            # TODO: Need to update
            dmt_wallet_debit = 0
            non_dmt_wallet_debit = 0

            passbook_last_entry.dmt_wallet_credit = dmt_wallet_credit
            passbook_last_entry.non_dmt_wallet_credit = non_dmt_wallet_credit

            passbook_last_entry.dmt_wallet_debit = dmt_wallet_debit
            passbook_last_entry.non_dmt_wallet_debit = non_dmt_wallet_debit

            passbook_last_entry.dmt_closing_balance = passbook_last_entry.dmt_opening_balance + dmt_wallet_credit - dmt_wallet_debit
            passbook_last_entry.non_dmt_closing_balance = passbook_last_entry.non_dmt_closing_balance + non_dmt_wallet_credit - non_dmt_wallet_debit

            passbook_last_entry.dmt_closing_wallet_balance = wallet.dmt_balance
            passbook_last_entry.non_dmt_closing_wallet_balance = wallet.non_dmt_balance
            passbook_last_entry.save()

            # Every day balance status in passbook
            # create a new entry for this day with
            # opening_balance = closing_balance & opening_wallet_balance = current wallet balance.
            Passbook.objects.create(
                user=user,
                non_dmt_opening_balance=passbook_last_entry.non_dmt_closing_balance,
                dmt_opening_balance=passbook_last_entry.dmt_closing_balance,
                non_dmt_opening_wallet_balance=wallet.non_dmt_balance,
                dmt_opening_wallet_balance=wallet.dmt_balance,
            )


'''
wallet_credit =(sum of all credit requests approved for the user on previous day
                + sum of all refunds on previous day)
i.e. sum of positive credit in wallet log on previous day

wallet_debit = (sum of amount of all successful transactions done on previous day 
                    + sum of all pending/refund pending transactions done on previous day)
i.e. sum of negative credit in wallet log on previous day

closing_balance = opening_balance + wallet_credit - wallet_debit

# closing_wallet_balance = current wallet balance
'''
