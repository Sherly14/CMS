import decimal

from django.db import transaction as dj_transaction

from zrtransaction import models as zr_transaction_models
from zrmapping import models as zr_mapping_models
from zrcommission import models as zr_commission_models


def get_sub_distributor(distributor):
    mapping = zr_mapping_models.DistributorSubDistributor.objects.filter(
        distributor=distributor
    ).last()
    if mapping:
        return mapping.sub_distributor
    else:
        return None


def is_sub_distributor(distributor):
    mapping = zr_mapping_models.DistributorSubDistributor.objects.filter(
        sub_distributor=distributor
    ).last()
    if mapping:
        return True
    else:
        return False


def get_main_distributor_from_merchant(merchant):
    mapping = zr_mapping_models.DistributorMerchant.objects.filter(
        merchant=merchant
    ).last()
    if not mapping:
        raise Exception("Invalid merchant (%s)" % (merchant.pk))

    main_distr = None
    if is_sub_distributor(mapping.distributor):
        dist_sub_dist_map = zr_mapping_models.DistributorSubDistributor.objects.filter(
            sub_distributor=mapping.distributor
        ).last()
        main_distr = dist_sub_dist_map.distributor
    else:
        main_distr = mapping.distributor

    return main_distr


def get_sub_distributor_from_merchant(merchant):
    mapping = zr_mapping_models.DistributorMerchant.objects.filter(
        merchant=merchant
    ).last()
    if not mapping:
        raise Exception("Invalid merchant (%s)" % (merchant.pk))

    sub_distr = None
    if is_sub_distributor(mapping.distributor):
        dist_sub_dist_map = zr_mapping_models.DistributorSubDistributor.objects.filter(
            sub_distributor=mapping.distributor
        ).last()
        sub_distr = dist_sub_dist_map.distributor

    return sub_distr


@dj_transaction.atomic
def calculate_commission():
    for transaction in zr_transaction_models.Transaction.objects.filter(
        is_commission_created=False
    ):
        merchant = transaction.user
        if transaction.source == zr_transaction_models.Transaction.BP:
            distributor = get_main_distributor_from_merchant(merchant)
            sp = transaction.service_provider
            bill_pay_comm = zr_commission_models.BillPayCommissionStructure.objects.filter(
                distributor=distributor,
                service_provider=sp
            ).last()
            if not bill_pay_comm:
                bill_pay_comm = zr_commission_models.BillPayCommissionStructure.objects.filter(
                    service_provider=sp,
                    is_default=True
                ).last()
            if not bill_pay_comm:
                raise Exception("CommissionStructure not found for transaction (%s)" % transaction.pk)
        elif transaction.source == zr_transaction_models.Transaction.DMT:
            dmt_commission_struct = zr_commission_models.DMTCommissionStructure.objects.last()
            if not dmt_commission_struct:
                raise Exception("DMT structure not found")

            customer_fee = (transaction.amount * dmt_commission_struct.customer_fee) / 100

        # For merchant
        distributor = get_main_distributor_from_merchant(merchant)
        if transaction.source == zr_transaction_models.Transaction.BP:
            commission_amt = 0
            tds_value = 0
            user_gst = 0
            if bill_pay_comm.commission_type == 'P':
                commission_amt = (bill_pay_comm.commission_for_merchant * transaction.amount) / 100
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
            elif bill_pay_comm.commission_type == 'F':
                commission_amt = bill_pay_comm.commission_for_merchant
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
        elif transaction.source == zr_transaction_models.Transaction.DMT:
            commission_amt = (customer_fee * dmt_commission_struct.commission_for_merchant) / 100
            tds_value = (commission_amt * dmt_commission_struct.tds_value) / 100
            user_gst = (commission_amt * dmt_commission_struct.gst_value) / 100

        zr_commission_models.Commission.objects.get_or_create(
            transaction=transaction,
            commission_user=merchant,
            defaults={
                "user_tds": tds_value,
                "user_gst": user_gst,
                "net_commission": commission_amt
            }
        )

        # For distributor
        sub_distr = get_sub_distributor_from_merchant(merchant)
        commission_amt = 0
        tds_value = 0
        user_gst = 0
        commission_for_distributor = 0

        if transaction.source == zr_transaction_models.Transaction.BP:
            if sub_distr:
                commission_for_distributor += bill_pay_comm.commission_for_sub_distributor

            if bill_pay_comm.commission_type == 'P':
                commission_amt = (bill_pay_comm.commission_for_distributor * transaction.amount) / 100
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
            elif bill_pay_comm.commission_type == 'F':
                commission_amt = bill_pay_comm.commission_for_distributor
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
        elif transaction.source == zr_transaction_models.Transaction.DMT:
            commission_for_distributor = dmt_commission_struct.commission_for_distributor
            if sub_distr:
                commission_for_distributor += dmt_commission_struct.commission_for_sub_distributor

            commission_amt = (customer_fee * commission_for_distributor) / 100
            tds_value = (commission_amt * dmt_commission_struct.tds_value) / 100
            user_gst = (commission_amt * dmt_commission_struct.gst_value) / 100

        zr_commission_models.Commission.objects.get_or_create(
            transaction=transaction,
            commission_user=distributor,
            defaults={
                "user_tds": tds_value,
                "user_gst": user_gst,
                "net_commission": commission_amt
            }
        )

        # For subdistributor
        if sub_distr:
            if transaction.source == zr_transaction_models.Transaction.BP:
                commission_amt = 0
                tds_value = 0
                user_gst = 0
                if bill_pay_comm.commission_type == 'P':
                    commission_amt = (bill_pay_comm.commission_for_sub_distributor * transaction.amount) / 100
                    tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                    user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
                elif bill_pay_comm.commission_type == 'F':
                    commission_amt = bill_pay_comm.commission_for_sub_distributor
                    tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                    user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
            elif transaction.source == zr_transaction_models.Transaction.DMT:
                commission_amt = (customer_fee * dmt_commission_struct.commission_for_sub_distributor) / 100
                tds_value = (commission_amt * dmt_commission_struct.tds_value) / 100
                user_gst = (commission_amt * dmt_commission_struct.gst_value) / 100

            zr_commission_models.Commission.objects.get_or_create(
                transaction=transaction,
                commission_user=sub_distr,
                defaults={
                    "user_tds": tds_value,
                    "user_gst": user_gst,
                    "net_commission": commission_amt
                }
            )

        # For zrupee
        commission_amt = 0
        tds_value = 0
        user_gst = 0
        if transaction.source == zr_transaction_models.Transaction.BP:
            if bill_pay_comm.commission_type == 'P':
                commission_amt = (bill_pay_comm.commission_for_sub_distributor * transaction.amount) / 100
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
            elif bill_pay_comm.commission_type == 'F':
                commission_amt = bill_pay_comm.commission_for_sub_distributor
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
        elif transaction.source == zr_transaction_models.Transaction.DMT:
            commission_amt = (customer_fee * dmt_commission_struct.commission_for_zrupee) / 100
            tds_value = (commission_amt * dmt_commission_struct.tds_value) / 100
            user_gst = (commission_amt * dmt_commission_struct.gst_value) / 100

        zr_commission_models.Commission.objects.get_or_create(
            transaction=transaction,
            commission_user=None,
            defaults={
                "user_tds": tds_value,
                "user_gst": user_gst,
                "net_commission": commission_amt
            }
        )

        transaction.is_commission_created = True
        transaction.save(update_fields=['is_commission_created'])
        print(transaction)


def calculate_zrupee_user_commission():
    total_commission = decimal.Decimal(0.00)
    for transaction in zr_transaction_models.Transaction.objects.all():
        sp = transaction.service_provider
        merchant = transaction.user

        distributor = get_main_distributor_from_merchant(merchant)
        bill_pay_comm = zr_commission_models.BillPayCommissionStructure.objects.filter(
            distributor=distributor,
            service_provider=sp
        ).last()
        if not bill_pay_comm:
            raise Exception("CommissionStructure not found for transaction (%s)" % transaction.pk)

        commission_amt = 0
        tds_value = 0
        user_gst = 0
        if bill_pay_comm.commission_type == 'P':
            commission_amt = (bill_pay_comm.commission_for_zrupee * transaction.amount) / 100
        elif bill_pay_comm.commission_type == 'F':
            commission_amt = bill_pay_comm.commission_for_zrupee

        total_commission += commission_amt

    return '%.2f' % total_commission
