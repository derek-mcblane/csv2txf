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

"""Implements Robinhood1099PDFExtracted

Does not handle:
* dividends
"""

from csv import DictReader
from datetime import datetime
from decimal import Decimal
from utils import Transaction, EntryCode, Warning, isLongTerm, txfDate
from enum import StrEnum


class HeaderField(StrEnum):
    DESCRIPTION = "description"
    DATE_SOLD = "sold_date"
    QUANTITY = "quantity"
    PROCEEDS = "proceeds"
    DATE_ACQUIRED = "acquired_date"
    COST = "cost"
    WASH_SALES_LOSS = "wash_sales_loss"
    GAIN_OR_LOSS = "gain_loss"


FIRST_LINE = (',').join(HeaderField)
DATE_FORMAT = "%m/%d/%y"


def _generateEntryCode(transaction: Transaction):
    if isLongTerm(transaction.buyDate, transaction.sellDate):
        return EntryCode.LONG_A
    else:
        return EntryCode.SHORT_A


def _parseCurrencyString(value: str):
    try:
        return Decimal(value.replace(',', '').split()[0])
    except Exception:
        print(f"exception in _parseCurrencyString(value={value})")
        raise


class Robinhood1099PDFExtracted:

    @classmethod
    def name(cls):
        return 'Robinhood 1099 PDF Extracted'

    @ classmethod
    def isFileForBroker(cls, filename):
        with open(filename) as f:
            first_line = f.readline()
            return first_line.find(FIRST_LINE) == 0

    @ classmethod
    def parseFileToTxnList(cls, filename, tax_year):
        with open(filename, newline='') as csvfile:
            csv_transactions = DictReader(csvfile)
            transactions = []
            for row in csv_transactions:
                transaction = Transaction()
                transaction.desc = row[HeaderField.DESCRIPTION]
                transaction.buyDate = datetime.strptime(
                    row[HeaderField.DATE_ACQUIRED], DATE_FORMAT)
                transaction.buyDateStr = txfDate(transaction.buyDate)
                transaction.sellDate = datetime.strptime(
                    row[HeaderField.DATE_SOLD], DATE_FORMAT)
                transaction.sellDateStr = txfDate(transaction.sellDate)
                transaction.costBasis = _parseCurrencyString(
                    row[HeaderField.COST])
                transaction.saleProceeds = _parseCurrencyString(
                    row[HeaderField.PROCEEDS])
                if row[HeaderField.WASH_SALES_LOSS] != "":
                    transaction.adjustment = _parseCurrencyString(
                        row[HeaderField.WASH_SALES_LOSS])
                transaction.entryCode = _generateEntryCode(transaction)

                if tax_year and transaction.sellDate.year != tax_year:
                    Warning('ignoring txn: "%s" as the sale is not from %d\n' %
                            (transaction.desc, tax_year))
                else:
                    transactions.append(transaction)
            return transactions
