#!/usr/bin/python
#
# Copyright 2012 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Converts a file to TXF for import into tax software.

Does not handle:
* dividends

Docs:
* TXF standard: http://turbotax.intuit.com/txf/
"""

from decimal import Decimal
from datetime import datetime, date
import sys
from utils import txfDate
from brokers import GetBroker


def ConvertTxnListToTxf(txn_list, tax_year, date):
    lines = []
    lines.append('V042')  # Version
    lines.append('Acsv2txf')  # Program name/version
    if date is None:
        date = txfDate(datetime.today())
    lines.append('D%s' % date)  # Export date
    lines.append('^')
    for txn in txn_list:
        lines.append('TD')
        lines.append('N%d' % txn.entryCode)
        lines.append('C1')
        lines.append('L1')
        lines.append('P%s' % txn.desc)
        lines.append('D%s' % txn.buyDateStr)
        lines.append('D%s' % txn.sellDateStr)
        lines.append('$%.2f' % txn.costBasis)
        lines.append('$%.2f' % txn.saleProceeds)
        if txn.adjustment:
            lines.append('$%.2f' % txn.adjustment)
        else:
            lines.append('$')
        lines.append('^')
    return lines


def RunConverter(broker_name, filename, tax_year, date):
    broker = GetBroker(broker_name, filename)
    txn_list = broker.parseFileToTxnList(filename, tax_year)
    return ConvertTxnListToTxf(txn_list, tax_year, date)


def GetSummary(broker_name, filename, tax_year, date_begin=None, date_end=None):
    if date_begin is None:
        date_begin = date(tax_year, 1, 1)
    if date_end is None:
        date_end = date(tax_year, 12, 31)
    broker = GetBroker(broker_name, filename)
    total_cost = Decimal(0)
    total_sales = Decimal(0)
    total_adjustment = Decimal(0)
    txn_list = [txn for txn in broker.parseFileToTxnList(filename, tax_year)
                if date_begin <= txn.sellDate.date() <= date_end]
    for txn in txn_list:
        total_cost += txn.costBasis
        total_sales += txn.saleProceeds
        if txn.adjustment:
            total_adjustment += txn.adjustment

    return '\n'.join([
        '%s summary report for %d' % (broker.name(), tax_year),
        'Num sale txns:  %d' % len(txn_list),
        'Total cost:     $%.2f' % total_cost,
        'Total proceeds: $%.2f' % total_sales,
        'Total adjustment: $%.2f' % total_adjustment,
        'Net gain/loss:  $%.2f' % (total_sales +
                                   total_adjustment - total_cost),
    ])


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("-f", "--file", dest="filename",
                        required=True, help="input file")
    parser.add_argument("--broker", dest="broker", help="broker name")
    parser.add_argument("-o", "--outfile", dest="out_filename",
                        help="output file, leave empty for stdout")
    parser.add_argument("--outfmt", dest="out_format",
                        help="output format: `txf` or `summary`")
    parser.add_argument("--year", dest="year", help="tax year", type=int)
    parser.add_argument("--date", dest="date", help="date to output")

    def string_to_date(s):
        return datetime.strptime(s, "%m/%d/%Y").date()

    parser.add_argument("--begin-date", dest="begin_date",
                        help="begin date to filter summary data",
                        type=string_to_date)
    parser.add_argument("--end-date", dest="end_date",
                        help="end date to filter summary data",
                        type=string_to_date)

    args = parser.parse_args()

    if args.year is None:
        args.year = datetime.today().year - 1

    output = None
    if args.out_format == 'summary':
        output = GetSummary(args.broker, args.filename,
                            args.year, args.begin_date, args.end_date)
    else:
        txf_lines = RunConverter(args.broker, args.filename, args.year,
                                 args.date)
        output = '\n'.join(txf_lines)

    if args.out_filename is None:
        print(output)
    else:
        with open(args.out_filename, 'w') as out:
            out.write(output)


if __name__ == '__main__':
    main()
