import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from django.utils import timezone

from zrtransaction.utils import constants
from zruser.models import ZrUser
from zrwallet import models as zw_models
from zrwallet.models import Passbook, Wallet

logger = logging.getLogger(__name__)


def passbook_open_script():
    """
    This script is to create first passbook entry for all users
    :return: 
    """
#    user_objs = ZrUser.objects.all()
    for wallet in zw_models.Wallet.objects.filter():
        user = wallet.merchant
        is_exist_passbook_entry = Passbook.objects.filter(user=user).exists()
        if is_exist_passbook_entry:
            continue

        try:
            wallet = Wallet.objects.get(merchant=user)
        except ObjectDoesNotExist:
            logger.warning(
                "Wallet not found for user(%s)" % user.pk
            )
            continue

        passbook = Passbook.objects.create(
            user=user,
            non_dmt_opening_balance=wallet.non_dmt_balance,
            dmt_opening_balance=wallet.dmt_balance,
            non_dmt_opening_wallet_balance=wallet.non_dmt_balance,
            dmt_opening_wallet_balance=wallet.dmt_balance,
        )
        logger.info("PassbookInitialize: Passport(%s) created for user_id(%s)" % (
            passbook.pk, user.pk
        ))


def daily_passbook_script():
    for wallet in zw_models.Wallet.objects.all():
        user = wallet.merchant
        passbook_last_entry = Passbook.objects.filter(user=user).last()
        if passbook_last_entry:
            # On next day this entry will be updated
            nw = timezone.now()

            # datetime.datetime(2017, 11, 12, 0, 0)
            min_day = timezone.datetime.combine(nw - timezone.timedelta(1), timezone.datetime.min.time())

            # datetime.datetime(2017, 11, 12, 23, 59, 59, 999999)
            max_day = timezone.datetime.combine(nw - timezone.timedelta(1), timezone.datetime.max.time())

            # dmt_wallet_credit
            dmt_wallet_credit = zw_models.WalletTransactions.objects.filter(
                payment_request__from_user=user,
                payment_request__at_created__range=(min_day, max_day),
                transaction__status__in=[
                    constants.TRANSACTION_STATUS_SUCCESS,
                    constants.TRANSACTION_STATUS_PENDING,
                    constants.TRANSACTION_STATUS_REFUNDED,
                    constants.TRANSACTION_STATUS_REFUND_PENDING
                ]
            ).aggregate(
                Sum('dmt_balance')
            ).get('dmt_balance__sum')
            if not dmt_wallet_credit:
                dmt_wallet_credit = 0

            # non_dmt_wallet_credit
            non_dmt_wallet_credit = zw_models.WalletTransactions.objects.filter(
                payment_request__from_user=user,
                payment_request__at_created__range=(min_day, max_day),
                transaction__status__in=[
                    constants.TRANSACTION_STATUS_SUCCESS,
                    constants.TRANSACTION_STATUS_PENDING,
                    constants.TRANSACTION_STATUS_REFUNDED,
                    constants.TRANSACTION_STATUS_REFUND_PENDING
                ]
            ).aggregate(
                Sum('non_dmt_balance')
            ).get('non_dmt_balance__sum')
            if not non_dmt_wallet_credit:
                non_dmt_wallet_credit = 0

            # dmt_wallet_debit
            dmt_wallet_debit = zw_models.WalletTransactions.objects.filter(
                transaction__status__in=[
                    constants.TRANSACTION_STATUS_SUCCESS,
                    constants.TRANSACTION_STATUS_PENDING,
                    constants.TRANSACTION_STATUS_REFUNDED,
                    constants.TRANSACTION_STATUS_REFUND_PENDING
                ],
                transaction__user=user,
                transaction__at_created__range=(min_day, max_day)
            ).aggregate(
                Sum('dmt_balance')
            ).get('dmt_balance__sum')
            if not dmt_wallet_debit:
                dmt_wallet_debit = 0

            # non_dmt_wallet_debit
            non_dmt_wallet_debit = zw_models.WalletTransactions.objects.filter(
                transaction__status__in=[
                    constants.TRANSACTION_STATUS_SUCCESS,
                    constants.TRANSACTION_STATUS_PENDING,
                    constants.TRANSACTION_STATUS_REFUNDED,
                    constants.TRANSACTION_STATUS_REFUND_PENDING
                ],
                transaction__user=user,
                transaction__at_created__range=(min_day, max_day)
            ).aggregate(
                Sum('non_dmt_balance')
            ).get('non_dmt_balance__sum')
            if not non_dmt_wallet_debit:
                non_dmt_wallet_debit = 0

            passbook_last_entry.dmt_wallet_credit = dmt_wallet_credit
            passbook_last_entry.non_dmt_wallet_credit = non_dmt_wallet_credit

            passbook_last_entry.dmt_wallet_debit = dmt_wallet_debit
            passbook_last_entry.non_dmt_wallet_debit = non_dmt_wallet_debit

            passbook_last_entry.dmt_closing_balance = passbook_last_entry.dmt_opening_balance + dmt_wallet_credit - dmt_wallet_debit
            passbook_last_entry.non_dmt_closing_balance = passbook_last_entry.dmt_opening_balance + non_dmt_wallet_credit - non_dmt_wallet_debit

            passbook_last_entry.dmt_closing_wallet_balance = wallet.dmt_balance
            passbook_last_entry.non_dmt_closing_wallet_balance = wallet.non_dmt_balance
            passbook_last_entry.save()

            # Every day balance status in passbook
            # create a new entry for this day with
            # opening_balance = closing_balance & opening_wallet_balance = current wallet balance.
            passbook = Passbook.objects.create(
                user=user,
                non_dmt_opening_balance=passbook_last_entry.non_dmt_closing_balance,
                dmt_opening_balance=passbook_last_entry.dmt_closing_balance,
                non_dmt_opening_wallet_balance=wallet.non_dmt_balance,
                dmt_opening_wallet_balance=wallet.dmt_balance,
            )
            logger.info("Dailycron: Passport(%s) created for user_id(%s)" % (
                passbook.pk, user.pk
            ))
