import os
import sys
import django
import decimal
import math
import numbers
import pandas as pd


cur_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(cur_dir, '..'))  # NOQA
sys.path.append(os.path.join(cur_dir, '..', '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')  # NOQA
django.setup()  # NOQA

from zruser.models import Bank

# input_file = os.path.join(cur_dir, 'NON-DMT DEFAULT COMMISSION STRUCTURE new.xls')
input_file = os.path.join(cur_dir, 'Bank_list_TILL11APR.xlsx')


if not os.path.exists(input_file):
    print('No Input file found')
    exit(0)

exl = pd.read_excel(
    input_file,
    sheetname='Sheet1',
    skiprows=0
)


for index, df in exl.iterrows():
    print('-->' + str(index + 1))
    bank_id = df[0]
    bank_name = df[1].encode('utf-8').strip()
    bank_code = str(df[2]).encode('utf-8').strip()

    if bank_id and not isinstance(bank_id, numbers.Number):
        print('input - bank_id should be an Integer')
        continue

    if bank_name == '':
        print('input - No bank_name Found')
        continue

    if bank_code == '':
        print('input - No bank_code Found')
        continue

    print bank_id, '|', bank_name, '|', bank_code

    if bank_id and bank_name and bank_code:

        if Bank.objects.filter(
            eko_bank_id=bank_id
        ).count() == 0:
            print 'Bank id NOT found in records. adding..'
            Bank.objects.create(
                eko_bank_id=bank_id,
                bank_name=bank_name,
                bank_code=bank_code
            )
        else:
            print 'Bank id found in records. updating..'
            Bank.objects.filter(
                eko_bank_id=bank_id
            ).update(
                bank_name=bank_name,
                bank_code=bank_code
            )
    else:
        print 'input bank data incomplete'
        continue
