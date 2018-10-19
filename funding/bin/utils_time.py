from datetime import datetime, date
from dateutil import parser
import math
import calendar


class TimeMagic():
    def __init__(self):
        self.now = datetime.now()
        self.weekdays_en = {
            0: 'monday',
            1: 'tuesday',
            2: 'wednesday',
            3: 'thursday',
            4: 'friday',
            5: 'saturday',
            6: 'sunday'
        }
        self.months_en = {
            0: 'january',
            1: 'february',
            2: 'march',
            3: 'april',
            4: 'may',
            5: 'june',
            6: 'july',
            7: 'august',
            8: 'september',
            9: 'october',
            10: 'november',
            11: 'december'
        }

    def get_weekday_from_datetime(self, dt):
        n = dt.today().weekday()
        return n

    def week_number_get(self):
        now = datetime.now()
        return int(now.strftime("%V"))

    def week_number_verify(self, week_nr):
        if week_nr > 0 or week_nr <= 53:
            return True

    def get_weeknr_from_date(self, date):
        return date.strftime("%V")

    def year_verify(self, year):
        if isinstance(year, str):
            try:
                year = int(year)
            except Exception as ex:
                return False

        if 2000 <= year <= 2030:
            return True

    def get_day_number(self):
        dt = datetime.now()
        return dt.today().weekday()

    def get_month_nr(self):
        return datetime.now().strftime("%m")

    def get_daynr_from_weekday(self, weekday):
        for k, v in self.weekdays_en.items():
            if v == weekday:
                return k

    def get_day_from_daynr(self, nr):
        return self.weekdays_en[nr]

    def get_month_from_weeknr(self, nr):
        nr = float(nr) / float(4)
        if nr.is_integer():
            nr -= 1
        else:
            nr = math.floor(nr)
        if nr < 0:
            nr = 0

        return self.months_en[nr]

    def get_month_nr_from_month(self, month):
        for k, v in self.months_en.items():
            if v == month:
                return k

    def get_year(self):
        return date.today().year

    def get_month(self):
        return date.today().month

    def get_amount_of_days_from_month_nr(self, month_nr):
        try:
            max_days = calendar.monthrange(self.get_year(), int(month_nr))[1]
            return max_days
        except Exception as e:
            pass

    def from_till(self):
        m = self.get_month()
        d = self.get_amount_of_days_from_month_nr(m)
        y = self.get_year()

        if len(str(d)) == 1:
            d = '0' + str(d)
        else:
            d = str(d)

        if len(str(m)) == 1:
            m = '0' + str(m)
        else:
            m = str(m)

        f = '%s/01/%s' % (m, y)
        t = '%s/%s/%s' % (m, d, y)

        return {'date_from': f, 'date_till': t}

    def ago_dt(self, datetime):
        return self.ago(datetime)

    def ago_str(self, date_str):
        date = parser.parse(date_str)
        return self.ago(date)

    def ago(self, datetime=None, epoch=None):
        import math

        if epoch:
            td = int(epoch)
        else:
            if datetime:
                td = (self.now - datetime).total_seconds()
            else:
                return None

        if td < 60:
            if td == 1:
                return '%s second ago'
            else:
                return 'Just now'
        elif 60 <= td < 3600:
            if 60 <= td < 120:
                return '1 minute ago'
            else:
                return '%s minutes ago' % str(int(math.floor(td / 60)))
        elif 3600 <= td < 86400:
            if 3600 <= td < 7200:
                return '1 hour ago'
            else:
                return '%s hours ago' % str(int(math.floor(td / 60 / 60)))
        elif td >= 86400:
            if td <= 86400 < 172800:
                return '1 day ago'
            else:
                x = int(math.floor(td / 24 / 60 / 60))
                if x == 1:
                    return '1 day ago'
                return '%s days ago' % str(x)
