import functools
import re
import utilitz.regex as rex


@functools.total_ordering
class Time:

    def __init__(self, value=None, sgn=1, hours=0, minutes=0, seconds=0, milis=0):
        if value is None:
            self._secondstime = sgn * \
                (hours * 3600 + minutes * 60 + seconds + milis / 1000)
        elif isinstance(value, (int, float)):
            self._secondstime = float(value)
        elif isinstance(value, str):
            parsed_time = Time.read(value)
            self._secondstime = parsed_time._secondstime
        elif isinstance(value, Time):
            self._secondstime = value._secondstime
        else:
            raise ValueError(f"Invalid time format: {value}")

    @property
    def hours(self):
        return self._secondstime / 3600

    @property
    def minutes(self):
        return self._secondstime / 60

    @property
    def seconds(self):
        return self._secondstime

    @property
    def milis(self):
        return self._secondstime * 1000

    @property
    def time(self):
        seconds_time = abs(self._secondstime)
        sng = -1 if self._secondstime < 0 else 1
        hours = seconds_time // 3600
        minutes = (seconds_time - hours * 3600) // 60
        seconds = (seconds_time - hours * 3600 - minutes * 60)//1
        milis = (seconds_time - hours * 3600 - minutes * 60 - seconds) * 1000
        return sng, int(hours), int(minutes), int(seconds), milis

    # Comparación

    def __eq__(self, other):
        if isinstance(other, Time):
            return self._secondstime == other._secondstime
        return self._secondstime == other

    def __lt__(self, other):
        if isinstance(other, Time):
            return self._secondstime < other._secondstime
        return self._secondstime < other

    # Operaciones aritméticas

    def __add__(self, other):
        if isinstance(other, Time):
            return Time(seconds=self._secondstime + other._secondstime)
        return Time(seconds=self._secondstime + other)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, Time):
            return Time(seconds=self._secondstime - other._secondstime)
        return Time(seconds=self._secondstime - other)

    def __rsub__(self, other):
        if isinstance(other, Time):
            return Time(seconds=other._secondstime - self._secondstime)
        return Time(seconds=other - self._secondstime)

    def __mul__(self, other):
        return Time(seconds=self._secondstime * other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        return Time(seconds=self._secondstime / other)

    # Conversión
    def __float__(self):
        return self._secondstime

    def __int__(self):
        return int(self._secondstime)

    # Representación

    def __str__(self):
        sgn, hours, minutes, seconds, milis = self.time
        sgn = '-' if sgn == -1 else ''
        if hours > 0:
            return f'{sgn}{hours}:{minutes:02d}:{seconds:02d}'
        if minutes > 0:
            return f'{sgn}{minutes}:{seconds:02d}'
        if seconds > 0:
            return f'{sgn}0:{seconds:02d}'
        fseconds = seconds + milis / 1000
        if fseconds < 0.001:
            return f'{sgn}0:00'
        return f'{sgn}0:{fseconds:.3f}'

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def regex():
        if not hasattr(Time, '_regex'):
            sgn = rex.Pattern(regex=r'-', name='sgn')
            h = rex.Number(name='hours', signum=False)
            m = rex.Number(name='minutes', signum=False)
            s = rex.Number(name='seconds', signum=False)
            Time._regex = r'(?:' + str(sgn) + r')?(?:' + str(h) + \
                r':)?(?:' + str(m) + r':)(?:' + str(s) + r')'
        return Time._regex

    @staticmethod
    def read(string):
        regex_str = Time.regex()
        match = re.fullmatch(regex_str, string)
        if match:
            decoded = rex.decode(regex_str, string, kind='first')
            sgn = -1 if decoded.get('sgn') else 1
            hours = decoded.get('hours') or 0
            minutes = decoded.get('minutes') or 0
            seconds = decoded.get('seconds') or 0
            return Time(sgn=sgn, hours=hours, minutes=minutes, seconds=seconds)
        raise ValueError(f"Invalid time format: {string}")


@functools.total_ordering
class Distance:

    def __init__(self, value=None, sgn=1, kilometers=0, meters=0):
        if value is None:
            self._metersdistance = sgn * \
                (kilometers * 1000 + meters)
        elif isinstance(value, (int, float)):
            self._metersdistance = float(value)
        elif isinstance(value, str):
            parsed_distance = Distance.read(value)
            self._metersdistance = parsed_distance._metersdistance
        elif isinstance(value, Distance):
            self._metersdistance = value._metersdistance
        else:
            raise ValueError(f"Invalid distance format: {value}")

    @property
    def kilometers(self):
        return self._metersdistance / 1000

    @property
    def meters(self):
        return self._metersdistance

    @property
    def distance(self):
        meters_distance = abs(self._metersdistance)
        sgn = -1 if self._metersdistance < 0 else 1
        kilometers = meters_distance // 1000
        meters = meters_distance - kilometers * 1000
        return sgn, int(kilometers), meters

    # Comparación

    def __eq__(self, other):
        if isinstance(other, Distance):
            return self._metersdistance == other._metersdistance
        return self._metersdistance == other

    def __lt__(self, other):
        if isinstance(other, Distance):
            return self._metersdistance < other._metersdistance
        return self._metersdistance < other

    # Operaciones aritméticas

    def __add__(self, other):
        if isinstance(other, Distance):
            return Distance(meters=self._metersdistance + other._metersdistance)
        return Distance(meters=self._metersdistance + other)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, Distance):
            return Distance(meters=self._metersdistance - other._metersdistance)
        return Distance(meters=self._metersdistance - other)

    def __rsub__(self, other):
        if isinstance(other, Distance):
            return Distance(meters=other._metersdistance - self._metersdistance)
        return Distance(meters=other - self._metersdistance)

    def __mul__(self, other):
        return Distance(meters=self._metersdistance * other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        return Distance(meters=self._metersdistance / other)

    # Conversión
    def __float__(self):
        return self._metersdistance

    def __int__(self):
        return int(self._metersdistance)

    # Representación

    def __str__(self):
        sgn, km, m = self.distance
        sgn_str = '-' if sgn == -1 else ''
        if km > 0:
            total_km = abs(self._metersdistance) / 1000
            if total_km.is_integer():
                return f'{sgn_str}{int(total_km)}km'
            return f'{sgn_str}{total_km:.2f}km'.rstrip('0').rstrip('.')
        
        if m.is_integer():
            return f'{sgn_str}{int(m)}m'
        return f'{sgn_str}{m:.2f}m'.rstrip('0').rstrip('.')

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def regex():
        if not hasattr(Distance, '_regex'):
            sgn = rex.Pattern(regex=r'-', name='sgn')
            val = rex.Number(name='value', signum=False)
            unit = rex.Pattern(regex=r'km|m', name='unit')
            Distance._regex = r'(?:' + str(sgn) + r')?(?:' + str(val) + r')\s?(?:' + str(unit) + r')'
        return Distance._regex

    @staticmethod
    def read(string):
        regex_str = Distance.regex()
        match = re.fullmatch(regex_str, string)
        if match:
            decoded = rex.decode(regex_str, string, kind='first')
            sgn = -1 if decoded.get('sgn') else 1
            value = decoded.get('value') or 0
            unit = decoded.get('unit') or 'm'
            if unit == 'km':
                return Distance(sgn=sgn, kilometers=value)
            return Distance(sgn=sgn, meters=value)
        raise ValueError(f"Invalid distance format: {string}")
