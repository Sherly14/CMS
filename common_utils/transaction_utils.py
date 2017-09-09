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


def get_merchants_from_distributor(distributor):
    mapping = zr_mapping_models.DistributorMerchant.objects.filter(
        distributor=distributor
    )
    return mapping.values('merchant', flat=True)


TRANSACTION_TYPE_DMT = 'DMT'


@dj_transaction.atomic
def calculate_commission():
    for transaction in zr_transaction_models.Transaction.objects.filter(
        is_commission_created=False
    ):
        merchant = transaction.user
        bill_pay_comm = None
        dmt_commission_struct = None
        distributor = get_main_distributor_from_merchant(merchant)
        if not transaction.type.name == TRANSACTION_TYPE_DMT:
            sp = transaction.service_provider
            bill_pay_comm = zr_commission_models.BillPayCommissionStructure.objects.filter(
                distributor=distributor,
                service_provider=sp,
                is_enabled=True
            ).last()
            if not bill_pay_comm:
                bill_pay_comm = zr_commission_models.BillPayCommissionStructure.objects.filter(
                    is_default=True,
                    is_enabled=True
                ).last()
            if not bill_pay_comm:
                raise Exception("CommissionStructure not found for transaction (%s)" % transaction.pk)
        else:
            dmt_commission_struct = zr_commission_models.DMTCommissionStructure.objects.filter(
                is_enabled=True, is_default=True, distributor=distributor,
                minimum_amount__gte=transaction.amount,
                maximum_amount__lte=transaction.amount
            ).last()

            if not dmt_commission_struct:
                dmt_commission_struct = zr_commission_models.DMTCommissionStructure.objects.filter(
                    minimum_amount__gte=transaction.amount,
                    maximum_amount__lte=transaction.amount,
                    is_enabled=True, is_default=True
                ).last()
            if not dmt_commission_struct:
                raise Exception("DMT structure not found")

            customer_fee = (transaction.amount * dmt_commission_struct.customer_fee) / 100
            if customer_fee < dmt_commission_struct.min_charge:
                customer_fee = dmt_commission_struct.customer_fee

        # For merchant
        distributor = get_main_distributor_from_merchant(merchant)
        if not transaction.type.name == TRANSACTION_TYPE_DMT:
            commission_amt = 0
            tds_value = 0
            user_gst = 0
            if bill_pay_comm.commission_type == 'P':
                if bill_pay_comm.is_chargable:
                    commission_amt = transaction.additional_charges

                commission_amt = (bill_pay_comm.commission_for_merchant * commission_amt) / 100
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
            elif bill_pay_comm.commission_type == 'F':
                commission_amt = bill_pay_comm.commission_for_merchant
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
        else:
            commission_amt = (customer_fee * dmt_commission_struct.commission_for_merchant) / 100
            tds_value = (commission_amt * dmt_commission_struct.tds_value) / 100
            user_gst = (commission_amt * dmt_commission_struct.gst_value) / 100

        zr_commission_models.Commission.objects.get_or_create(
            transaction=transaction,
            commission_user=merchant,
            defaults={
                "user_tds": tds_value,
                "user_gst": user_gst,
                "net_commission": commission_amt,
                "bill_payment_comm_structure": bill_pay_comm,
                "dmt_comm_structure": dmt_commission_struct
            }
        )

        # For distributor
        sub_distr = get_sub_distributor_from_merchant(merchant)
        commission_amt = 0
        tds_value = 0
        user_gst = 0
        commission_for_distributor = 0

        if not transaction.type.name == TRANSACTION_TYPE_DMT:
            if sub_distr:
                commission_for_distributor += bill_pay_comm.commission_for_sub_distributor

            if bill_pay_comm.commission_type == 'P':
                if bill_pay_comm.is_chargable:
                    commission_amt = transaction.additional_charges

                commission_amt = (bill_pay_comm.commission_for_distributor * commission_amt) / 100
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
            elif bill_pay_comm.commission_type == 'F':
                commission_amt = bill_pay_comm.commission_for_distributor
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
        else:
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
                "net_commission": commission_amt,
                "bill_payment_comm_structure": bill_pay_comm,
                "dmt_comm_structure": dmt_commission_struct
            }
        )

        # For subdistributor
        if sub_distr:
            if not transaction.type.name == TRANSACTION_TYPE_DMT:
                commission_amt = 0
                tds_value = 0
                user_gst = 0
                if bill_pay_comm.commission_type == 'P':
                    if bill_pay_comm.is_chargable:
                        commission_amt = transaction.additional_charges

                    commission_amt = (bill_pay_comm.commission_for_sub_distributor * commission_amt) / 100
                    tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                    user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
                elif bill_pay_comm.commission_type == 'F':
                    commission_amt = bill_pay_comm.commission_for_sub_distributor
                    tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                    user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
            else:
                commission_amt = (customer_fee * dmt_commission_struct.commission_for_sub_distributor) / 100
                tds_value = (commission_amt * dmt_commission_struct.tds_value) / 100
                user_gst = (commission_amt * dmt_commission_struct.gst_value) / 100

            zr_commission_models.Commission.objects.get_or_create(
                transaction=transaction,
                commission_user=sub_distr,
                defaults={
                    "user_tds": tds_value,
                    "user_gst": user_gst,
                    "net_commission": commission_amt,
                    "bill_payment_comm_structure": bill_pay_comm,
                    "dmt_comm_structure": dmt_commission_struct
                }
            )

        # For zrupee
        commission_amt = 0
        tds_value = 0
        user_gst = 0
        if not transaction.type.name == TRANSACTION_TYPE_DMT:
            if bill_pay_comm.commission_type == 'P':
                if bill_pay_comm.is_chargable:
                    commission_amt = transaction.additional_charges

                commission_amt = (bill_pay_comm.commission_for_sub_distributor * commission_amt) / 100
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
            elif bill_pay_comm.commission_type == 'F':
                commission_amt = bill_pay_comm.commission_for_sub_distributor
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
        else:
            commission_amt = (customer_fee * dmt_commission_struct.commission_for_zrupee) / 100
            tds_value = (commission_amt * dmt_commission_struct.tds_value) / 100
            user_gst = (commission_amt * dmt_commission_struct.gst_value) / 100

        zr_commission_models.Commission.objects.get_or_create(
            transaction=transaction,
            commission_user=None,
            defaults={
                "user_tds": tds_value,
                "user_gst": user_gst,
                "net_commission": commission_amt,
                "bill_payment_comm_structure": bill_pay_comm,
                "dmt_comm_structure": dmt_commission_struct
            }
        )

        transaction.is_commission_created = True
        transaction.save(update_fields=['is_commission_created'])
        print(transaction)
