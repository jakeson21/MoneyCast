#!/usr/bin/env python3
import argparse
from datetime import date, timedelta
import calendar
from enum import Enum, unique
from typing import NewType, List
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import json
import pdb


@unique
class CycleEnum(Enum):
    DAILY = 0
    WEEKLY = 1
    BIWEEKLY = 2
    MONTHLY = 3
    BIMONTHLY = 4
    QUARTERLY = 5
    YEARLY = 6


Cycle = NewType('Cycle', CycleEnum)


@unique
class DueDateType(Enum):
    WeekDay = 0
    DateNumber = 1
    Date = 2
    Daily = 3


@unique
class DayOfWeek(Enum):
    """  Matches date.isoweekday() = Monday=1, ..., Sunday=7 """
    Monday = 1
    Tuesday = 2
    Wednesday = 3
    Thursday = 4
    Friday = 5
    Saturday = 6
    Sunday = 7


def add_weeks(sourcedate, weeks):
    nextdate = sourcedate + timedelta(days=7*weeks)
    return nextdate


def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class BudgetItem:
    def __init__(self, name, amount, cycle: Cycle, due_date=None):
        self.name = name
        self.amount = amount
        self.cycle = cycle

        self.due_date_type = None
        if isinstance(due_date, int):
            self.due_date = due_date
            self.due_date_type = DueDateType.DateNumber
        elif isinstance(due_date, DayOfWeek):
            self.due_date = due_date
            self.due_date_type = DueDateType.WeekDay
        elif isinstance(due_date, date):
            self.due_date = due_date
            self.due_date_type = DueDateType.Date
            print(due_date)
        elif due_date is None:
            self.due_date = due_date
            self.due_date_type = DueDateType.Daily

    def __str__(self):
        if self.due_date_type == DueDateType.WeekDay:
            return '{}: {}, {}, {}'.format(self.name, self.amount, self.due_date.name, self.cycle.name)
        if self.due_date_type == DueDateType.Daily:
            return '{}: {}, {}'.format(self.name, self.amount, self.cycle.name)
        if self.due_date_type == DueDateType.DateNumber or self.due_date_type == DueDateType.Date:
            return '{}: {}, {}, {}'.format(self.name, self.amount, self.due_date, self.cycle.name)

    def __repr__(self):
        return self.__str__()


class BudgetItemEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BudgetItem):
            json_repr = {'name': obj.name,
                         'amount': obj.amount,
                         'cycle': obj.cycle.name}
            # Now encode due_date
            if isinstance(obj.due_date, int):
                due_date_type = DueDateType.DateNumber.name
                json_repr['due_date'] = obj.due_date
            elif isinstance(obj.due_date, DayOfWeek):
                due_date_type = DueDateType.WeekDay.name
                json_repr['due_date'] = obj.due_date.name
            elif isinstance(obj.due_date, date):
                due_date_type = DueDateType.Date.name
                json_repr['due_date'] = {'month': obj.due_date.month, 'day': obj.due_date.day, 'year': obj.due_date.year}
            elif obj.due_date is None:
                due_date_type = DueDateType.Daily.name
                # json_repr['due_date'] = None

            json_repr['due_date_type'] = due_date_type
            return json_repr
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class BudgetItemDecoder(json.JSONDecoder):
    def decode(self, obj):
        budget = list()
        json_obj = json.loads(obj)

        # These fields must be exist in every entry
        required_main_fields = ['name', 'amount', 'cycle', 'due_date_type']

        # Parse the json string into a BudgetItem list
        try:
            for item in json_obj:
                # Validate that the required fields exist
                for field in required_main_fields:
                    if field not in item:
                        raise ValueError('missing field \"{}\" while trying to parse:{}'.format(field, item))
                # Grab them locally
                name = item['name']
                amount = item['amount']
                cycle = CycleEnum[item['cycle']]
                due_date_type = DueDateType[item['due_date_type']]

                if due_date_type is DueDateType.Daily:
                    b = BudgetItem(name=name,
                                   amount=amount,
                                   cycle=cycle)
                else:
                    if 'due_date' not in item:
                        raise ValueError('missing field \"due_date\" while trying to parse:{}'.format(item))
                    if due_date_type is DueDateType.Date:
                        required_date_fields = ['day', 'month', 'year']
                        if type(item['due_date']) is not dict:
                            raise ValueError('due_date is not of type: "day", 1, "month", 2, "year", 3: while trying to parse:{}'.format(item))
                        for field in required_date_fields:
                            if field not in item['due_date']:
                                raise ValueError('missing field "{}" while trying to parse:{}'.format(field, item))
                        b = BudgetItem(name=name,
                                       amount=amount,
                                       cycle=cycle,
                                       due_date=date(**item['due_date']))
                    elif due_date_type is DueDateType.DateNumber:
                        due_date = item['due_date']
                        b = BudgetItem(name=name,
                                       amount=amount,
                                       cycle=cycle,
                                       due_date=due_date)
                    elif due_date_type is DueDateType.WeekDay:
                        try:
                            due_date = DayOfWeek[item['due_date']]
                        except KeyError:
                            raise ValueError('due_date is not of type DayOfWeek')
                        b = BudgetItem(name=name,
                                       amount=amount,
                                       cycle=cycle,
                                       due_date=due_date)
                budget.append(b)

        except KeyError:
            print('Error while trying to parse: {}'.format(item))
            raise

        return budget


def forecast(balance, start, duration, budget: List):
    print('From', start, 'To', start + timedelta(weeks=duration))
    date_list = [start + timedelta(days=x) for x in range(0, duration*7)]
    daily_balance = balance
    balance_list = list()
    daily_balance_list = list()
    # for item in budget:
    #     print(item)

    # Go through list and set all past due dates to the future as appropriate
    for item in budget:
        if item.due_date_type == DueDateType.Date:
            if item.due_date < date_list[0]:
                # if item.cycle == CycleEnum.WEEKLY:
                #     item.due_date += timedelta(weeks=1)
                # elif item.cycle == CycleEnum.MONTHLY:
                #     item.due_date = add_months(item.due_date, 1)
                if item.cycle == CycleEnum.BIWEEKLY:
                    while item.due_date < date_list[0]:
                        item.due_date = add_weeks(item.due_date, 2)
                elif item.cycle == CycleEnum.BIMONTHLY:
                    while item.due_date < date_list[0]:
                        item.due_date = add_months(item.due_date, 2)
                elif item.cycle == CycleEnum.QUARTERLY:
                    while item.due_date < date_list[0]:
                        item.due_date = add_months(item.due_date, 3)
                elif item.cycle == CycleEnum.YEARLY:
                    while item.due_date < date_list[0]:
                        item.due_date = add_months(item.due_date, 12)

    for t in date_list:
        trans = dict()
        for item in budget:
            if item.due_date_type == DueDateType.WeekDay:
                if item.due_date == DayOfWeek(t.isoweekday()):
                    daily_balance += item.amount
                    trans[item.name] = item.amount
            elif item.due_date_type == DueDateType.DateNumber:
                if item.due_date == t.day:
                    daily_balance += item.amount
                    trans[item.name] = item.amount
            elif item.due_date_type == DueDateType.Daily:
                daily_balance += item.amount
                trans[item.name] = item.amount
            elif item.due_date_type == DueDateType.Date:
                if item.due_date == t:
                    daily_balance += item.amount
                    trans[item.name] = item.amount
                    # if item.cycle == CycleEnum.WEEKLY:
                    #     item.due_date += timedelta(weeks=1)
                    # elif item.cycle == CycleEnum.MONTHLY:
                    #     item.due_date = add_months(item.due_date, 1)
                    if item.cycle == CycleEnum.BIWEEKLY:
                        item.due_date = add_weeks(item.due_date, 2)
                    elif item.cycle == CycleEnum.BIMONTHLY:
                        item.due_date = add_months(item.due_date, 2)
                    elif item.cycle == CycleEnum.QUARTERLY:
                        item.due_date = add_months(item.due_date, 3)
                    elif item.cycle == CycleEnum.YEARLY:
                        item.due_date = add_months(item.due_date, 12)

        balance_list.append([t, '${:,.2f}'.format(daily_balance), trans])
        daily_balance_list.append(daily_balance)

    print('\n\nDAILY BALANCE PROJECTION\n==================')

    for item in balance_list:
        print(item[0], '=', item[1], item[2])

    plt.style.use('dark_background')
    fig, ax = plt.subplots()
    # for ii, (ival, idate) in enumerate(zip(daily_balance_list, date_list)):
    #     ax.scatter(idate, ival, s=30, facecolor='g', edgecolor='k', zorder=9999, alpha=.5)
    ax.plot(date_list, daily_balance_list, 'go-', mec='w')
    z = np.polyfit(range(0, len(daily_balance_list)), daily_balance_list, 1)
    y = np.polyval(z, range(0, len(daily_balance_list)))
    ax.plot(date_list, y)
    ax.text(date_list[1], y[1]-100, '{}'.format(z), fontsize=8)

    ax.set(xlabel='Date', ylabel='End-of-Day Balance $', title='Daily Balance Projection')
    ax.grid()
    # Set the xticks formatting
    # format xaxis with 3 month intervals
    ax.get_xaxis().set_major_locator(mdates.DayLocator(interval=int(len(date_list)/8)))
    ax.get_xaxis().set_major_formatter(mdates.DateFormatter("%b %d, %Y"))
    fig.autofmt_xdate()
    plt.show()


def run_example(balance, weeks):
    budget = list()
    budget.append(BudgetItem(name='Salary', amount=1000.00, cycle=CycleEnum.WEEKLY, due_date=DayOfWeek.Friday))

    budget.append(BudgetItem(name='Insurance', amount=-200.99, cycle=CycleEnum.MONTHLY, due_date=25))
    budget.append(BudgetItem(name='Food', amount=round(-250.00 / 7), cycle=CycleEnum.DAILY))
    budget.append(BudgetItem(name='Internet', amount=-90.99, cycle=CycleEnum.MONTHLY, due_date=15))
    budget.append(BudgetItem(name='Savings', amount=-100.00, cycle=CycleEnum.WEEKLY, due_date=DayOfWeek.Monday))
    budget.append(BudgetItem(name='Mortgage', amount=-876.54, cycle=CycleEnum.MONTHLY, due_date=15))
    budget.append(BudgetItem(name='Sewer', amount=-165.00, cycle=CycleEnum.QUARTERLY, due_date=date(year=2019, month=1, day=10)))
    budget.append(BudgetItem(name='Gas', amount=-40, cycle=CycleEnum.WEEKLY, due_date=DayOfWeek.Friday))
    budget.append(BudgetItem(name='Hair-do', amount=-60, cycle=CycleEnum.BIMONTHLY, due_date=date(year=2019, month=1, day=5)))
    budget.append(BudgetItem(name='TAXES', amount=-1000.00, cycle=CycleEnum.YEARLY, due_date=date(year=2019, month=4, day=14)))

    # Example of writing the budget to json string
    # j_str = json.dumps(budget, cls=BudgetItemEncoder, sort_keys=True, indent=4)
    # print('{}'.format(j_str))
    # Example of reading budget from json string
    # j_obj = json.loads(j_str, cls=BudgetItemDecoder)
    # print('{}'.format(j_obj))

    forecast(balance, date.today(), weeks, budget)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='moneycast', usage='%(prog)s balance weeks')
    parser.add_argument('balance', metavar='balance', type=float, help='how many weeks to forecast')
    parser.add_argument('length',  metavar='weeks', type=int, help='how many weeks to forecast')
    parser.add_argument('-f', '--file', type=str, help='json file with budget items to read in')
    args = parser.parse_args()

    print('Forecasting for', args.length, 'weeks')
    if args.file is not None:
        with open(args.file, 'r') as read_file:
            data = json.load(read_file, cls=BudgetItemDecoder)
        forecast(balance=args.balance, start=date.today(), duration=args.length, budget=data)
    else:
        run_example(balance=args.balance, weeks=args.length)


