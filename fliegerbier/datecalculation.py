from datetime import datetime


_months = [
    'Januar', 'Februar', 'März', 'April',
    'Mai', 'Juni', 'Juli', 'August',
    'September', 'Oktober', 'November', 'Dezember'
]


class Month:
    def __init__(
        self,
        year: int,
        month: int,
        start_ts: int,
        end_ts: int,
    ):
        self.year = year
        self.month = month
        self.month_name = _months[month - 1]
        self.start_ts = start_ts
        self.end_ts = end_ts

    def __str__(self):
        return '{}/{} {} {}-{}'.format(
            self.year, self.month,
            self.month_name, self.start_ts, self.end_ts
        )


def get_month(n_backwards: int = 0):
    now = datetime.now()

    month_start = datetime(
        year=now.year,
        month=now.month,
        day=1,
        hour=0,
    )

    for _ in range(n_backwards):
        if month_start.month == 1:
            # go to previos month
            month_start = datetime(
                year=month_start.year - 1,
                month=12,
                day=1,
                hour=0,
            )
        else:
            month_start = datetime(
                year=month_start.year,
                month=month_start.month - 1,
                day=1,
                hour=0,
            )

    if month_start.month == 12:
        month_end = datetime(
            year=month_start.year + 1,
            month=1,
            day=1
        )
    else:
        month_end = datetime(
            year=month_start.year,
            month=month_start.month + 1,
            day=1,
            hour=0,
        )

    return Month(
        year=month_start.year,
        month=month_start.month,
        start_ts=month_start.timestamp(),
        end_ts=month_end.timestamp(),
    )
