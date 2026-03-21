import functools
import re
import utilitz.regex as rex


@functools.total_ordering
class Time:

    _FACTORS = {'hours': 3600, 'minutes': 60, 'seconds': 1, 'milis': 0.001}

    def __init__(self, value=0, unit='seconds'):
        self._unit = unit
        if isinstance(value, (int, float)):
            self._magnitude = float(value) * self._FACTORS[self._unit]
        elif isinstance(value, str):
            parsed_time = Time.read(value)
            self._magnitude = parsed_time._magnitude
        elif isinstance(value, Time):
            self._magnitude = value._magnitude
        else:
            raise ValueError(f"Invalid time format: {value}")

    @property
    def hours(self):
        return self._magnitude / 3600

    @property
    def minutes(self):
        return self._magnitude / 60

    @property
    def seconds(self):
        return self._magnitude

    @property
    def milis(self):
        return self._magnitude * 1000

    @property
    def time(self):
        seconds_time = abs(self._magnitude)
        sng = -1 if self._magnitude < 0 else 1
        hours = seconds_time // 3600
        minutes = (seconds_time - hours * 3600) // 60
        seconds = (seconds_time - hours * 3600 - minutes * 60)//1
        milis = (seconds_time - hours * 3600 - minutes * 60 - seconds) * 1000
        return sng, int(hours), int(minutes), int(seconds), milis

    @property
    def unit(self):
        return self._unit

    # Comparación

    def _get_magnitude(self, other):
        if isinstance(other, Time):
            return other._magnitude
        if isinstance(other, (int, float)):
            return float(other) * self._FACTORS[self._unit]
        return NotImplemented

    def __eq__(self, other):
        sec = self._get_magnitude(other)
        if sec is NotImplemented:
            return False
        return self._magnitude == sec

    def __lt__(self, other):
        sec = self._get_magnitude(other)
        if sec is NotImplemented:
            return NotImplemented
        return self._magnitude < sec

    # Operaciones aritméticas

    def __neg__(self):
        return Time(-self._magnitude / self._FACTORS[self._unit], self._unit)

    def __pos__(self):
        return self

    def __abs__(self):
        return Time(abs(self._magnitude) / self._FACTORS[self._unit], self._unit)

    def __add__(self, other):
        sec = self._get_magnitude(other)
        if sec is NotImplemented:
            return NotImplemented
        return Time((self._magnitude + sec) / self._FACTORS[self._unit], self._unit)

    def __radd__(self, other):
        sec = self._get_magnitude(other)
        if sec is NotImplemented:
            return NotImplemented
        return Time((sec + self._magnitude) / self._FACTORS[self._unit], self._unit)

    def __sub__(self, other):
        sec = self._get_magnitude(other)
        if sec is NotImplemented:
            return NotImplemented
        return Time((self._magnitude - sec) / self._FACTORS[self._unit], self._unit)

    def __rsub__(self, other):
        sec = self._get_magnitude(other)
        if sec is NotImplemented:
            return NotImplemented
        return Time((sec - self._magnitude) / self._FACTORS[self._unit], self._unit)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return Time((self._magnitude * other) / self._FACTORS[self._unit], self._unit)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, (int, float)):
            return Time((self._magnitude / other) / self._FACTORS[self._unit], self._unit)
        return NotImplemented

    def __rtruediv__(self, other):
        return NotImplemented

    # Conversión

    def __float__(self):
        return self._magnitude / self._FACTORS[self._unit]

    def __int__(self):
        return int(self._magnitude / self._FACTORS[self._unit])

    # Representación

    def __str__(self):
        sgn, hours, minutes, seconds, milis = self.time
        sgn_str = '-' if sgn == -1 else ''

        # Consistent millisecond rounding
        rounded_milis = int(round(milis))
        if rounded_milis >= 1000:
            seconds += 1
            rounded_milis -= 1000
            if seconds >= 60:
                seconds -= 60
                minutes += 1
                if minutes >= 60:
                    minutes -= 60
                    hours += 1

        milis_str = f'.{rounded_milis:03d}' if rounded_milis > 0 else ''

        if hours > 0:
            return f'{sgn_str}{hours}:{minutes:02d}:{seconds:02d}{milis_str}'
        if minutes > 0:
            return f'{sgn_str}{minutes}:{seconds:02d}{milis_str}'

        return f'{sgn_str}0:{seconds:02d}{milis_str}'

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
            total = sgn * (hours * 3600 + minutes * 60 + seconds)
            return Time(total, 'seconds')
        raise ValueError(f"Invalid time format: {string}")


@functools.total_ordering
class Distance:

    _FACTORS = {'kilometers': 1000, 'meters': 1}

    def __init__(self, value=0, unit='meters'):
        self._unit = unit
        if isinstance(value, (int, float)):
            self._magnitude = float(value) * self._FACTORS[self._unit]
        elif isinstance(value, str):
            parsed_distance = Distance.read(value)
            self._magnitude = parsed_distance._magnitude
        elif isinstance(value, Distance):
            self._magnitude = value._magnitude
        else:
            raise ValueError(f"Invalid distance format: {value}")

    @property
    def kilometers(self):
        return self._magnitude / 1000

    @property
    def meters(self):
        return self._magnitude

    @property
    def distance(self):
        meters_distance = abs(self._magnitude)
        sgn = -1 if self._magnitude < 0 else 1
        kilometers = meters_distance // 1000
        meters = meters_distance - kilometers * 1000
        return sgn, int(kilometers), meters

    @property
    def unit(self):
        return self._unit

    # Comparación

    def _get_magnitude(self, other):
        if isinstance(other, Distance):
            return other._magnitude
        if isinstance(other, (int, float)):
            return float(other) * self._FACTORS[self._unit]
        return NotImplemented

    def __eq__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented:
            return False
        return self._magnitude == m

    def __lt__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented:
            return NotImplemented
        return self._magnitude < m

    # Operaciones aritméticas

    def __neg__(self):
        return Distance(-self._magnitude / self._FACTORS[self._unit], self._unit)

    def __pos__(self):
        return self

    def __abs__(self):
        return Distance(abs(self._magnitude) / self._FACTORS[self._unit], self._unit)

    def __add__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented:
            return NotImplemented
        return Distance((self._magnitude + m) / self._FACTORS[self._unit], self._unit)

    def __radd__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented:
            return NotImplemented
        return Distance((m + self._magnitude) / self._FACTORS[self._unit], self._unit)

    def __sub__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented:
            return NotImplemented
        return Distance((self._magnitude - m) / self._FACTORS[self._unit], self._unit)

    def __rsub__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented:
            return NotImplemented
        return Distance((m - self._magnitude) / self._FACTORS[self._unit], self._unit)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return Distance((self._magnitude * other) / self._FACTORS[self._unit], self._unit)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, (int, float)):
            return Distance((self._magnitude / other) / self._FACTORS[self._unit], self._unit)
        return NotImplemented

    def __rtruediv__(self, other):
        return NotImplemented

    # Conversión

    def __float__(self):
        return self._magnitude / self._FACTORS[self._unit]

    def __int__(self):
        return int(self._magnitude / self._FACTORS[self._unit])

    # Representación

    def __str__(self):
        sgn, km, m = self.distance
        sgn_str = '-' if sgn == -1 else ''
        if km > 0:
            total_km = abs(self._magnitude) / 1000
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
            Distance._regex = r'(?:' + str(sgn) + r')?(?:' + \
                str(val) + r')\s?(?:' + str(unit) + r')'
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
            val = sgn * value
            return Distance(val, 'kilometers' if unit == 'km' else 'meters')
        raise ValueError(f"Invalid distance format: {string}")
