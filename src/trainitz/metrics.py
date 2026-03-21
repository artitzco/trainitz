import functools
import re
import utilitz.regex as rex


@functools.total_ordering
class Metric:
    """Base class for physical metrics like Time and Distance."""

    _FACTORS = {'unit': 1}

    # -------------------------------------------------------------------------
    # 1. CONSTRUCTOR Y PROPIEDADES
    # -------------------------------------------------------------------------

    def __init__(self, value=0, unit=None):
        self._unit = unit or 'unit'
        if isinstance(value, (int, float)):
            self._magnitude = float(value) * self._FACTORS[self._unit]
        elif isinstance(value, str):
            parsed = self.read(value)
            self._magnitude = parsed._magnitude
        elif isinstance(value, self.__class__):
            self._magnitude = value._magnitude
        else:
            raise ValueError(
                f"Invalid {self.__class__.__name__.lower()} format: {value}")

    @property
    def unit(self):
        return self._unit

    def to(self, unit):
        """Returns a new metric instance converted to the target unit."""
        if unit in self._FACTORS:
            calculated_value = self._magnitude / self._FACTORS[unit]
            return self.__class__(calculated_value, unit)
        raise ValueError(
            f"Unit '{unit}' is not supported by {self.__class__.__name__}")

    def get(self, unit):
        """Returns the float value of the metric in the target unit."""
        if unit in self._FACTORS:
            return self._magnitude / self._FACTORS[unit]
        raise ValueError(
            f"Unit '{unit}' is not supported by {self.__class__.__name__}")

    @property
    def values(self):
        """Generic decomposition of the magnitude based on _FACTORS order."""
        mag = abs(self._magnitude)
        sgn = -1 if self._magnitude < 0 else 1
        res = [sgn]
        items = list(self._FACTORS.items())
        for i, (name, factor) in enumerate(items):
            if i == len(items) - 1:  # Último factor (precisión decimal)
                res.append(mag / factor)
            else:
                val = mag // factor
                mag -= val * factor
                res.append(int(val))
        return tuple(res)

    # -------------------------------------------------------------------------
    # 2. CONVERSIÓN Y REPRESENTACIÓN
    # -------------------------------------------------------------------------

    def __float__(self):
        return self._magnitude / self._FACTORS[self._unit]

    def __int__(self):
        return int(self._magnitude / self._FACTORS[self._unit])

    def __str__(self):
        """Basic string representation for testing."""
        return f"{float(self)}u"

    def __repr__(self):
        return self.__str__()

    @classmethod
    def read(cls, string):
        """Dummy implementation for base class testing."""
        return cls(float(string), 'unit')

    # -------------------------------------------------------------------------
    # 3. MÉTODOS AUXILIARES
    # -------------------------------------------------------------------------

    def _get_magnitude(self, other):
        """Returns the internal magnitude for arithmetic/comparisons."""
        if isinstance(other, self.__class__):
            return other._magnitude
        if isinstance(other, (int, float)):
            return float(other) * self._FACTORS[self._unit]
        return NotImplemented

    # -------------------------------------------------------------------------
    # 4. COMPARACIÓN
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # 5. OPERACIONES UNARIAS
    # -------------------------------------------------------------------------

    def __neg__(self):
        return self.__class__(-self._magnitude / self._FACTORS[self._unit], self._unit)

    def __pos__(self):
        return self

    def __abs__(self):
        return self.__class__(abs(self._magnitude) / self._FACTORS[self._unit], self._unit)

    # -------------------------------------------------------------------------
    # 6. OPERACIONES BINARIAS
    # -------------------------------------------------------------------------

    def __add__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented:
            return NotImplemented
        return self.__class__((self._magnitude + m) / self._FACTORS[self._unit], self._unit)

    def __radd__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented:
            return NotImplemented
        return self.__class__((m + self._magnitude) / self._FACTORS[self._unit], self._unit)

    def __sub__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented:
            return NotImplemented
        return self.__class__((self._magnitude - m) / self._FACTORS[self._unit], self._unit)

    def __rsub__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented:
            return NotImplemented
        return self.__class__((m - self._magnitude) / self._FACTORS[self._unit], self._unit)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__((self._magnitude * other) / self._FACTORS[self._unit], self._unit)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, self.__class__):
            return self._magnitude / other._magnitude
        if isinstance(other, (int, float)):
            return self.__class__((self._magnitude / other) / self._FACTORS[self._unit], self._unit)
        return NotImplemented

    def __rtruediv__(self, other):
        return NotImplemented


class Time(Metric):

    _FACTORS = {'hours': 3600, 'minutes': 60, 'seconds': 1, 'milis': 0.001}

    def __init__(self, value=0, unit='seconds'):
        super().__init__(value, unit)

    def __str__(self):
        sgn, hours, minutes, seconds, milis = self.values
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

    @classmethod
    def regex(cls):
        if not hasattr(cls, '_regex'):
            sgn = rex.Pattern(regex=r'-', name='sgn')
            h = rex.Number(name='hours', signum=False)
            m = rex.Number(name='minutes', signum=False)
            s = rex.Number(name='seconds', signum=False)
            ms = rex.Pattern(regex=r'\d+', name='milis')
            cls._regex = r'(?:' + str(sgn) + r')?(?:' + str(h) + \
                r':)?(?:' + str(m) + r':)(?:' + \
                str(s) + r')(?:\.' + str(ms) + r')?'
        return cls._regex

    @classmethod
    def read(cls, string):
        regex_str = cls.regex()
        match = re.fullmatch(regex_str, string)
        if match:
            decoded = rex.decode(regex_str, string, kind='first')
            sgn = -1 if decoded.get('sgn') else 1
            hours = decoded.get('hours') or 0
            minutes = decoded.get('minutes') or 0
            seconds = decoded.get('seconds') or 0
            milis_str = decoded.get('milis') or '0'
            milis_val = float("0." + milis_str)
            total = sgn * (hours * 3600 + minutes * 60 + seconds + milis_val)
            return cls(total, 'seconds')
        raise ValueError(f"Invalid time format: {string}")


class Distance(Metric):

    _FACTORS = {'kilometers': 1000, 'meters': 1}

    def __init__(self, value=0, unit='meters'):
        super().__init__(value, unit)

    def __str__(self):
        sgn, km, m = self.values
        sgn_str = '-' if sgn == -1 else ''
        if km > 0:
            total_km = abs(self._magnitude) / 1000
            if total_km.is_integer():
                return f'{sgn_str}{int(total_km)}km'
            return f'{sgn_str}{total_km:.2f}km'.rstrip('0').rstrip('.')

        if m.is_integer():
            return f'{sgn_str}{int(m)}m'
        return f'{sgn_str}{m:.2f}m'.rstrip('0').rstrip('.')

    @classmethod
    def regex(cls):
        if not hasattr(cls, '_regex'):
            sgn = rex.Pattern(regex=r'-', name='sgn')
            val = rex.Number(name='value', signum=False)
            unit = rex.Pattern(regex=r'km|m', name='unit')
            cls._regex = r'(?:' + str(sgn) + r')?(?:' + \
                str(val) + r')\s?(?:' + str(unit) + r')'
        return cls._regex

    @classmethod
    def read(cls, string):
        regex_str = cls.regex()
        match = re.fullmatch(regex_str, string)
        if match:
            decoded = rex.decode(regex_str, string, kind='first')
            sgn = -1 if decoded.get('sgn') else 1
            value = decoded.get('value') or 0
            unit = decoded.get('unit') or 'm'
            val = sgn * value
            return cls(val, 'kilometers' if unit == 'km' else 'meters')
        raise ValueError(f"Invalid distance format: {string}")
