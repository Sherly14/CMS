import decimal

from django.contrib.auth import get_user_model
from django.db import transaction as dj_transaction

from zrmapping import models as zr_mapping_models
from zrcommission import models as zr_commission_models
from zrmapping import models as zr_mapping_models
from zrtransaction import models as zr_transaction_models


def get_sub_distributor(distributor):
    mapping = zr_mapping_models.DistributorSubDistributor.objects.filter(
        distributor=distributor
    ).last()
    if mapping:
        return mapping.sub_distributor
    else:
        return None


def get_merchant_id_list_from_distributor(distributor):
    return list(zr_mapping_models.DistributorMerchant.objects.filter(distributor=distributor).values_list(
        'merchant_id', flat=True))


def get_sub_distributor_id_list_from_distributor(distributor):
    return list(zr_mapping_models.DistributorSubDistributor.objects.filter(distributor=distributor).values_list(
        'sub_distributor_id', flat=True))


def get_sub_distributor_merchant_id_list_from_distributor(distributor):
    return list(zr_mapping_models.SubDistributorMerchant.objects.filter(
        sub_distributor_id__in=get_sub_distributor_id_list_from_distributor(distributor)).values_list(
        'sub_distributor_id', flat=True))


def get_sub_distributor_merchant_id_list_from_sub_distributor(sub_distributor):
    return list(zr_mapping_models.SubDistributorMerchant.objects.filter(sub_distributor=sub_distributor).values_list(
        'sub_distributor_id', flat=True))


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

    main_distr = None
    if mapping:
        main_distr = mapping.distributor
    else:
        dist_sub_dist_map = zr_mapping_models.SubDistributorMerchant.objects.filter(
            merchant=merchant
        ).last()
        if dist_sub_dist_map:
            distr_sub_distr = zr_mapping_models.DistributorSubDistributor.objects.filter(
                sub_distributor=dist_sub_dist_map.sub_distributor
            ).last()
            if distr_sub_distr:
                main_distr = distr_sub_distr.distributor

    return main_distr


def get_sub_distributor_from_merchant(merchant):
    mappings = zr_mapping_models.SubDistributorMerchant.objects.filter(
        merchant=merchant
    ).last()
    sub_distr = None
    if mappings:
        sub_distr = mappings.sub_distributor

    return sub_distr


def get_merchants_from_distributor(distributor):
    mapping = zr_mapping_models.DistributorMerchant.objects.filter(
        distributor=distributor
    )
    return mapping.values_list('merchant', flat=True)


def get_distributor_from_sub_distributor(sub_distributor):
    mapping = zr_mapping_models.DistributorSubDistributor.objects.filter(
        sub_distributor=sub_distributor
    ).last()
    if mapping:
        return mapping.distributor
    else:
        return None


def get_main_admin():
    # This is to get main admin means zrupee admin user object
    # Note: On creation of main admin need to assign zr_user details with it
    from zruser import models as zu
    user_instance = zu.ZrUser.objects.filter(
        mobile_no='9999999911'
    ).last()
    return user_instance


TRANSACTION_TYPE_DMT = 'DMT'


@dj_transaction.atomic
def calculate_commission():
    print 'running calculate commissions job'
    for transaction in zr_transaction_models.Transaction.objects.filter(
        is_commission_created=False,
        status='S'
    ):
        merchant = transaction.user
        bill_pay_comm = None
        dmt_commission_struct = None
        distributor = get_main_distributor_from_merchant(merchant)

        if not distributor:
            continue

        if not transaction.type.name == TRANSACTION_TYPE_DMT:
            sp = transaction.service_provider
            if not sp
                continue
            bill_pay_comm = zr_commission_models.BillPayCommissionStructure.objects.filter(
                distributor=distributor,
                service_provider=sp,
                is_enabled=True,
                is_default=False
            ).last()
            if not bill_pay_comm:
                bill_pay_comm = zr_commission_models.BillPayCommissionStructure.objects.filter(
                    is_default=True,
                    is_enabled=True,
                    service_provider=sp,
                ).last()
            if not bill_pay_comm:
                raise Exception("CommissionStructure not found for transaction (%s)" % transaction.pk)
        else:
            dmt_commission_struct = zr_commission_models.DMTCommissionStructure.objects.filter(
                transaction_vendor=transaction.vendor,
                is_enabled=True,
                is_default=False,
                distributor=distributor,
                minimum_amount__lte=transaction.amount,
                maximum_amount__gte=transaction.amount
            ).last()

            if not dmt_commission_struct:
                dmt_commission_struct = zr_commission_models.DMTCommissionStructure.objects.filter(
                    transaction_vendor=transaction.vendor,
                    minimum_amount__lte=transaction.amount,
                    maximum_amount__gte=transaction.amount,
                    is_enabled=True,
                    is_default=True
                ).last()
            if not dmt_commission_struct:
                raise Exception("DMT structure not found for transaction(%s)")

            customer_fee = 0
            if dmt_commission_struct.commission_type == 'P':
                customer_fee = (transaction.amount * dmt_commission_struct.customer_fee) / 100
            elif dmt_commission_struct.commission_type == 'F':
                customer_fee = dmt_commission_struct.customer_fee
            if customer_fee < dmt_commission_struct.min_charge:
                customer_fee = dmt_commission_struct.min_charge

        # For merchant
        if not transaction.type.name == TRANSACTION_TYPE_DMT:
            commission_amt = 0
            tds_value = 0
            user_gst = 0
            if bill_pay_comm.commission_type == 'P':
                if bill_pay_comm.is_chargable:
                    commission_amt = transaction.additional_charges
                else:
                    commission_amt = (transaction.amount * bill_pay_comm.net_margin) / 100

                commission_amt = (bill_pay_comm.commission_for_merchant * commission_amt) / 100
                commission_amt = (commission_amt * decimal.Decimal(84.745)) / 100
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
            elif bill_pay_comm.commission_type == 'F':
                commission_amt = bill_pay_comm.commission_for_merchant
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
        else:
            commission_amt = (customer_fee * dmt_commission_struct.commission_for_merchant) / 100
            commission_amt = (commission_amt * decimal.Decimal(84.745)) / 100
            tds_value = (commission_amt * dmt_commission_struct.tds_value) / 100
            user_gst = (commission_amt * dmt_commission_struct.gst_value) / 100

        zr_commission_models.Commission.objects.get_or_create(
            transaction=transaction,
            commission_user=merchant,
            defaults={
                "user_tds": tds_value,
                "user_gst": user_gst,
                "net_commission": (commission_amt + user_gst) - tds_value,
                "bill_payment_comm_structure": bill_pay_comm,
                "dmt_comm_structure": dmt_commission_struct,
                "user_commission": commission_amt
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
                commission_for_distributor = bill_pay_comm.commission_for_distributor
            else:
                commission_for_distributor = bill_pay_comm.commission_for_distributor + bill_pay_comm.commission_for_sub_distributor

            if bill_pay_comm.commission_type == 'P':
                if bill_pay_comm.is_chargable:
                    commission_amt = transaction.additional_charges
                else:
                    commission_amt = (transaction.amount * bill_pay_comm.net_margin) / 100

                commission_amt = (commission_for_distributor * commission_amt) / 100
                commission_amt = (commission_amt * decimal.Decimal(84.745)) / 100
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
            elif bill_pay_comm.commission_type == 'F':
                commission_amt = commission_for_distributor
                commission_amt = (commission_amt * decimal.Decimal(84.745)) / 100
                tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
        else:
            if sub_distr:
                commission_for_distributor = dmt_commission_struct.commission_for_distributor
            else:
                commission_for_distributor = dmt_commission_struct.commission_for_distributor + dmt_commission_struct.commission_for_sub_distributor

            commission_amt = (customer_fee * commission_for_distributor) / 100
            commission_amt = (commission_amt * decimal.Decimal(84.745)) / 100
            tds_value = (commission_amt * dmt_commission_struct.tds_value) / 100
            user_gst = (commission_amt * dmt_commission_struct.gst_value) / 100

        zr_commission_models.Commission.objects.get_or_create(
            transaction=transaction,
            commission_user=distributor,
            defaults={
                "user_tds": tds_value,
                "user_gst": user_gst,
                "net_commission": (commission_amt + user_gst) - tds_value,
                "bill_payment_comm_structure": bill_pay_comm,
                "dmt_comm_structure": dmt_commission_struct,
                "user_commission": commission_amt
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
                    else:
                        commission_amt = (transaction.amount * bill_pay_comm.net_margin) / 100

                    commission_amt = (bill_pay_comm.commission_for_sub_distributor * commission_amt) / 100
                    commission_amt = (commission_amt * decimal.Decimal(84.745)) / 100
                    tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                    user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
                elif bill_pay_comm.commission_type == 'F':
                    commission_amt = bill_pay_comm.commission_for_sub_distributor
                    commission_amt = (commission_amt * decimal.Decimal(84.745)) / 100
                    tds_value = (commission_amt * bill_pay_comm.tds_value) / 100
                    user_gst = (commission_amt * bill_pay_comm.gst_value) / 100
            else:
                commission_amt = (customer_fee * dmt_commission_struct.commission_for_sub_distributor) / 100
                commission_amt = (commission_amt * decimal.Decimal(84.745)) / 100
                tds_value = (commission_amt * dmt_commission_struct.tds_value) / 100
                user_gst = (commission_amt * dmt_commission_struct.gst_value) / 100

            zr_commission_models.Commission.objects.get_or_create(
                transaction=transaction,
                commission_user=sub_distr,
                defaults={
                    "user_tds": tds_value,
                    "user_gst": user_gst,
                    "net_commission": (commission_amt + user_gst) - tds_value,
                    "bill_payment_comm_structure": bill_pay_comm,
                    "dmt_comm_structure": dmt_commission_struct,
                    "user_commission": commission_amt
                }
            )

        # For zrupee
        commission_amt = 0
        if not transaction.type.name == TRANSACTION_TYPE_DMT:
            if bill_pay_comm.commission_type == 'P':
                if bill_pay_comm.is_chargable:
                    commission_amt = transaction.additional_charges
                else:
                    commission_amt = (transaction.amount * bill_pay_comm.net_margin) / 100

                commission_amt = (bill_pay_comm.commission_for_zrupee * commission_amt) / 100
            elif bill_pay_comm.commission_type == 'F':
                commission_amt = bill_pay_comm.commission_for_zrupee
        else:
            commission_amt = (customer_fee * dmt_commission_struct.commission_for_zrupee) / 100

        zr_commission_models.Commission.objects.get_or_create(
            transaction=transaction,
            commission_user=None,
            defaults={
                "user_tds": 0,
                "user_gst": 0,
                "net_commission": commission_amt,
                "bill_payment_comm_structure": bill_pay_comm,
                "dmt_comm_structure": dmt_commission_struct,
                "user_commission": commission_amt
            }
        )

        transaction.is_commission_created = True
        transaction.save(update_fields=['is_commission_created'])
        print(transaction)
