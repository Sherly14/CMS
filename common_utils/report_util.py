

import datetime
from decimal import Decimal

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


def get_excel_doc(obj, header_dsiplay,report_file_path, has_next=False, user_type=None):
    # output = BytesIO()
    workbook = xlsxwriter.Workbook(report_file_path)
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

    worksheet_s.merge_range('Q1:U1', 'Merchant', title)
    worksheet_s.merge_range('V1:Y1', 'Distributor', title)
    worksheet_s.merge_range('Z1:AC1', 'Sub-Distributor', title)
    if user_type == 'SU':
        worksheet_s.merge_range('AD1:AE1', 'Zrupee', cell)

    i = incrementClass(val=-1)
    for key, value in header_dsiplay:
        worksheet_s.write(1, i.get_inc_val(), ugettext(key), header)

    row = 2
    for idx, data in enumerate(obj):
        inc_cls = incrementClass(val=-1)
        row = 2 + idx
        for key, value in header_dsiplay:
            try:
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
            except:
                worksheet_s.write(row, inc_cls.get_inc_val(), "N/A", cell)

    # To set size of all columns to 20
    # for index in range(inc_cls.get_inc_val()):
    #     worksheet_s.set_column("{0}:{0}".format(string.uppercase[index]), 20)

    if has_next:
        return workbook, worksheet_s, row + 1
    workbook.close()
    return workbook, worksheet_s, row + 1


def update_excel_doc(obj, header_dsiplay, workbook, worksheet_s, last_row, has_next=False):
    # excel styles
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

    for idx, data in enumerate(obj):
        inc_cls = incrementClass(val=-1)
        row = last_row + idx
        for key, value in header_dsiplay:
            try:
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
            except:
                worksheet_s.write(row, inc_cls.get_inc_val(), "N/A", cell)

    # To set size of all columns to 20
    # for index in range(inc_cls.get_inc_val()):
    #     worksheet_s.set_column("{0}:{0}".format(string.uppercase[index]), 20)

    if has_next:
        return workbook, worksheet_s, row + 1
    workbook.close()
    return workbook, worksheet_s, row + 1
