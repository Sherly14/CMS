from __future__ import print_function

import datetime
import string
from decimal import Decimal
from io import BytesIO

import xlsxwriter
from django.utils.translation import ugettext


class incrementClass():
    def __init__(self, val=0):
        "Value initialization"
        self.val = val

    def increment(self):
        "To increment value"
        self.val += 1

    def get_val(self):
        "To get value"
        return self.val

    def get_inc_val(self):
        "To get incremented value"
        self.val += 1
        return self.val


def get_excel_doc(request, obj, heading, header_dsiplay):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet_s = workbook.add_worksheet("Summary")

    # excel styles
    title = workbook.add_format({
        'bold': True,
        'font_size': 10,
        'align': 'center',
        'valign': 'vcenter'
    })
    header = workbook.add_format({
        'bg_color': 'white',
        'bold': True,
        'color': 'black',
        'align': 'center',
        'font_size': 10,
        'valign': 'top',
        'border': 1
    })
    cell = workbook.add_format({
        'align': 'center',
        'valign': 'top',
        'text_wrap': True,
        'border': 1
    })
    number_cell = workbook.add_format({
        'align': 'right',
        'valign': 'top',
        'text_wrap': True,
        'border': 1
    })
    date_format = workbook.add_format({
        'num_format': 'dd/mm/yyyy',
        'align': 'center',
        'valign': 'top',
        'border': 1
    })

    worksheet_s.merge_range('G1:J1', 'Merchant', title)
    worksheet_s.merge_range('K1:O1', 'Distributor', title)
    worksheet_s.merge_range('P1:R1', 'Sub-Distributor', title)
    worksheet_s.write(0, 9, 'Zrupee', cell)

    i = incrementClass(val=-1)
    for key, value in header_dsiplay:
        worksheet_s.write(1, i.get_inc_val(), ugettext(key), header)

    inc_cls = incrementClass(val=-1)
    for idx, data in enumerate(obj):
        inc_cls = incrementClass(val=-1)
        row = 2 + idx
        for key, value in header_dsiplay:
            if str(value).endswith("()"):
                temp = data.__getattribute__(value.split("(")[0])() or "N/A"
            # elif str(value).startswith("self."):
            #     temp = self.__getattribute__(value.split("self.")[1])(data) or "N/A"
            else:
                value = value.split('.')
                temp = data
                for val in value:
                    temp = temp.__getattribute__(val)
            if type(temp) == datetime.datetime:
                temp = temp.replace(tzinfo=None)
                worksheet_s.write(row, inc_cls.get_inc_val(), temp.date(), date_format)
            elif type(temp) in [int, float, Decimal]:
                worksheet_s.write(row, inc_cls.get_inc_val(), temp, number_cell)
            else:
                worksheet_s.write(row, inc_cls.get_inc_val(), temp, cell)

    for index in range(inc_cls.get_inc_val()):
        worksheet_s.set_column("{0}:{0}".format(string.uppercase[index]), 20)

    workbook.close()
    return output.getvalue()
