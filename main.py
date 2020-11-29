import requests
from requests.auth import HTTPBasicAuth
import numpy as np
import datetime as dt
from calendar import monthrange
import math
import json
import argparse

parser = argparse.ArgumentParser(description='Create Earnings report for timesheet data from toggl')
parser.add_argument('-c', '--config', help='Earnings config file to use', required=True)
parser.add_argument('-uagent', '--user_agent', help="Set your Toggl API user agent", required=True)
parser.add_argument('-uid', '--user_id', help="Set your Toggl user id", required=True)
parser.add_argument('-wid', '--workspace_id', help="Set your Toggl workspace id", required=True)
parser.add_argument('-atoken', '--api_token', help="Set your Toggl workspace id", required=True)
parser.add_argument('-s', '--since', help='Start date for the report',
                    default=dt.date(dt.date.today().year, dt.date.today().month, 1))
parser.add_argument('-p', '--until', help="End date for the report", default=dt.date.today())
parser.add_argument('-g', '--goal', help="Set you goal earnings mark", default=0, type=float)
parser.add_argument('-cur', '--currency', help="Set your currency", default='$')


args = parser.parse_args()

# arguments
MINIMAL_EARNINGS = args.goal
CURRENCY = args.currency
START_DATE = args.since
END_DATE = args.until

print("Starting Toggl Earnings...")
print("----------------------------------------------------")

business_days = np.busday_count(START_DATE, END_DATE) + 1

total_earnings_per_client = {}
total_hours_per_client = {}

with open(args.config) as client_rates_fp:
    client_rates = json.load(client_rates_fp)

    for client in client_rates.keys():
        total_earnings_per_client[client] = 0
        total_hours_per_client[client] = 0


def getEarnings(name):
    params = {'user_agent': args.user_agent,
              'workspace_id': args.workspace_id,
              'since': START_DATE.isoformat(),
              'until': END_DATE.isoformat(),
              'user_ids': args.user_id,
              'page': 1}

    headers = {'content-type': 'application/json', 'user_agent': args.user_agent}

    r = requests.get('https://api.track.toggl.com/reports/api/v2/details',
                     auth=HTTPBasicAuth(args.api_token, 'api_token'),
                     params=params,
                     headers=headers)

    pages = r.json()['total_count'] / r.json()['per_page']

    for i in range(math.ceil(pages)):
        params['page'] = i + 1

        r = requests.get('https://api.track.toggl.com/reports/api/v2/details',
                         auth=HTTPBasicAuth(args.api_token, 'api_token'),
                         params=params,
                         headers=headers)

        for i in r.json()['data']:
            total_hours_per_client[i['client']] += (i['dur'] / 3600000)
            total_earnings_per_client[i['client']] += (i['dur'] / 3600000) * client_rates[i['client']]

    # TODO: PRINT THIS NICELY
    # print(total_hours_per_client)
    # print(total_paycheck_per_client)

    (billed_work_hours, billed_work_hours_per_business_day, total_earnings) = \
        (sum(total_hours_per_client.values()),
         sum(total_hours_per_client.values()) / business_days,
         sum(total_earnings_per_client.values())
         )
    total_minimal_earnings_diff = round(total_earnings - MINIMAL_EARNINGS, 2)

    print("Earnings for {} business days between: {} - {} are {} {}.".
          format(business_days, START_DATE.isoformat(), END_DATE.isoformat(), round(total_earnings, 2), CURRENCY))

    for client in client_rates.keys():
        if total_hours_per_client[client] > 0:
            print("\t Total of {} hours worked for client {} made {} {} earnings."
                  .format(round(total_hours_per_client[client], 2), client, round(total_earnings_per_client[client], 2),
                          CURRENCY))

    print("This is {} {} than minimal earnings mark of {} {}.".
          format(abs(total_minimal_earnings_diff), 'less' if total_minimal_earnings_diff < 0 else 'more',
                 MINIMAL_EARNINGS, CURRENCY))



    print("Billed work hours average per business day are {} for a total {} billed work hours in {} business days.".
          format(round(billed_work_hours_per_business_day, 2), round(billed_work_hours, 2), business_days))
    print("Average earnings per business day are {} {}.".
          format(round(total_earnings / business_days, 2), CURRENCY))

    if END_DATE.month == dt.date.today().month:
        print("Projected earnings till end of month: {} {}.".format(
            total_earnings + np.busday_count(END_DATE, dt.date(END_DATE.year, END_DATE.month,
                                                               monthrange(END_DATE.year, END_DATE.month)[1] + 1)) * (
                    total_earnings / business_days), CURRENCY))

    print("-------------------------------------------------")


if __name__ == '__main__':
    getEarnings('PyCharm')
