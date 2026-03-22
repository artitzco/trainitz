import functools
import re

# -------------------------------------------------------------------------
# 0. REGISTRO FÍSICO (Solo matemáticas)
# -------------------------------------------------------------------------
# El registro almacena únicamente factores numéricos de conversión. 
# Si agregas una unidad aquí, automáticamente funcionará la física.

UNITS_REGISTRY = {
    'Time': {
        'h': 3600, 'hour': 3600, 'hours': 3600,
        'min': 60, 'minute': 60, 'minutes': 60,
        's': 1, 'second': 1, 'seconds': 1,
        'ms': 0.001, 'millisecond': 0.001, 'milliseconds': 0.001,
    },
    'Distance': {
        'km': 1000, 'kilometer': 1000, 'kilometers': 1000,
        'm': 1, 'meter': 1, 'meters': 1,
    }
}

# -------------------------------------------------------------------------
# 1. FORMATTERS (Representaciones visuales y parseo)
# -------------------------------------------------------------------------
# Desacoplamos la vista del modelo. Las físicas operan sobre magnitudes; 
# los formatos operan sobre cómo "dibujar" o "leer" un string.

def render_short(mag, factor, unit_name):
    val = mag / factor
    val_str = str(int(val)) if val.is_integer() else f"{val:.2f}".rstrip('0').rstrip('.')
    sgn = "-" if mag < 0 else ""
    return f"{sgn}{val_str}{unit_name}"

def render_derived(mag, factor, unit_name):
    # En derivadas, factor es la division cruzada, unit_name es tupla ('km', 'h')
    val = mag / factor
    val_str = str(int(val)) if val.is_integer() else f"{val:.2f}".rstrip('0').rstrip('.')
    sgn = "-" if mag < 0 else ""
    return f"{sgn}{val_str}{unit_name[0]}/{unit_name[1]}"

def render_clock(mag, factor, unit_name):
    hrs = int(abs(mag) // 3600)
    rem = abs(mag) % 3600
    mins = int(rem // 60)
    rem %= 60
    secs = int(rem // 1)
    milis = int(round((rem % 1) * 1000))
    if milis >= 1000:
        secs += 1
        milis -= 1000
    milis_str = f".{milis:03d}" if milis > 0 else ""
    sgn = "-" if mag < 0 else ""
    if hrs > 0:
        return f"{sgn}{hrs}:{mins:02d}:{secs:02d}{milis_str}"
    return f"{sgn}{mins}:{secs:02d}{milis_str}"

class FormatPattern:
    def __init__(self, regex, parser, renderer):
        self.regex = re.compile(regex)
        self.parser = parser
        self.renderer = renderer

FORMATS = {
    'clock': FormatPattern(
        regex = r'^(?P<sgn>-)?(?:(?P<h>\d+):)?(?P<m>\d+):(?P<s>\d{2})(?:\.(?P<ms>\d+))?$',
        parser = lambda m: (
            float((-1 if m.group('sgn') else 1) * (
                int(m.group('h') or 0) * 3600 +
                int(m.group('m') or 0) * 60 +
                int(m.group('s')) +
                float("0." + (m.group('ms') or "0"))
            )),
            's' # Unidad base asumida al leer un reloj
        ),
        renderer = render_clock
    ),
    'short': FormatPattern(
        regex = r'^(?P<sgn>-)?(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z]+)$',
        parser = lambda m: (
            float(m.group('val')) * (-1 if m.group('sgn') else 1),
            m.group('unit')
        ),
        renderer = render_short
    ),
    'derived': FormatPattern(
        regex = r'^(?P<sgn>-)?(?P<val>\d+(?:\.\d+)?)\s*(?P<u1>[a-zA-Z]+)/(?P<u2>[a-zA-Z]+)$',
        parser = lambda m: (
            float(m.group('val')) * (-1 if m.group('sgn') else 1),
            (m.group('u1'), m.group('u2'))
        ),
        renderer = render_derived
    )
}

# -------------------------------------------------------------------------
# 2. MOTOR DE FÍSICA Y MÉTRICA BASE
# -------------------------------------------------------------------------

@functools.total_ordering
class Metric:
    """Base class for decoupled physical metrics."""

    _UNITS = {'unit': 1}
    _DEFAULT_UNIT = 'unit'
    _ACCEPTED_FORMATS = ['short']

    @classmethod
    def _get_multiplier(cls, unit):
        """Resolves the conversion factor for a given unit (recursive)."""
        if isinstance(cls._UNITS, dict):
            if unit not in cls._UNITS:
                raise ValueError(f"Unit '{unit}' not supported by {cls.__name__}")
            return cls._UNITS[unit]
            
        unit_tuple = unit if isinstance(unit, tuple) else (unit,)
        if len(unit_tuple) != len(cls._UNITS):
            raise ValueError(f"Unit {unit} does not match {cls.__name__} dimensions.")
            
        factor = 1.0
        for u, (comp_class, exponent) in zip(unit_tuple, cls._UNITS):
            factor *= (comp_class._get_multiplier(u) ** exponent)
        return factor

    def __init__(self, value=0, unit=None, format=None):
        if isinstance(value, str):
            mag, det_unit, det_format = self._parse_string(value)
            self._magnitude = mag
            self._unit = unit or det_unit
            self._format = format or det_format
        else:
            self._unit = unit or getattr(self.__class__, '_DEFAULT_UNIT', 'unit')
            self._format = format or getattr(self.__class__, '_ACCEPTED_FORMATS', ['short'])[0]
            if isinstance(value, (int, float)):
                self._magnitude = float(value) * self.multiplier
            elif isinstance(value, self.__class__):
                self._magnitude = value._magnitude
            else:
                raise ValueError(f"Invalid {self.__class__.__name__.lower()} format: {value}")

    @property
    def multiplier(self):
        return self._get_multiplier(self._unit)

    @property
    def unit(self):
        return self._unit
        
    @property
    def format(self):
        return self._format

    def to(self, unit=None, format=None):
        """Returns a new metric instance converted to the target physical unit or format."""
        target_unit = unit or self._unit
        target_format = format or self._format
        
        if target_format not in getattr(self.__class__, '_ACCEPTED_FORMATS', ['short']):
            raise ValueError(f"Format {target_format} not available for {self.__class__.__name__}")
            
        factor = self._get_multiplier(target_unit)
        return self.__class__(self._magnitude / factor, target_unit, target_format)

    def get(self, unit):
        """Returns the float value of the metric in the target unit."""
        factor = self._get_multiplier(unit)
        return self._magnitude / factor

    # -------------------------------------------------------------------------
    # OPERADORES Y FORMATO
    # -------------------------------------------------------------------------

    def __float__(self):
        return self._magnitude / self.multiplier

    def __int__(self):
        return int(self._magnitude / self.multiplier)

    def __str__(self):
        format_name = self._format
        if format_name not in FORMATS:
            format_name = getattr(self.__class__, '_ACCEPTED_FORMATS', ['short'])[0]
        return FORMATS[format_name].renderer(self._magnitude, self.multiplier, self._unit)

    def __repr__(self):
        return self.__str__()

    @classmethod
    def read(cls, string):
        """Reads a string and returns a metric instance."""
        return cls(string)

    @classmethod
    def _parse_string(cls, string):
        accepted_formats = getattr(cls, '_ACCEPTED_FORMATS', ['short'])
        for format_name in accepted_formats:
            format_pattern = FORMATS[format_name]
            match = format_pattern.regex.match(string)
            if match:
                val, parsed_unit = format_pattern.parser(match)
                
                if isinstance(cls._UNITS, dict):
                    if parsed_unit not in cls._UNITS:
                        continue 
                    mag = val * cls._get_multiplier(parsed_unit)
                else:
                    if not isinstance(parsed_unit, tuple) or len(parsed_unit) != len(cls._UNITS):
                        continue
                    try:
                        factor = cls._get_multiplier(parsed_unit)
                    except ValueError:
                        continue
                    mag = val * factor
                    
                return mag, parsed_unit, format_name
                
        raise ValueError(f"Invalid {cls.__name__.lower()} format: {string}")

    def _get_magnitude(self, other):
        """Returns the internal magnitude for arithmetic/comparisons."""
        if isinstance(other, self.__class__): return other._magnitude
        if isinstance(other, (int, float)): return float(other) * self.multiplier
        return NotImplemented

    # -------------------------------------------------------------------------
    # COMPARACIÓN & MATEMÁTICAS
    # -------------------------------------------------------------------------

    def __eq__(self, other):
        m = self._get_magnitude(other)
        return self._magnitude == m if m is not NotImplemented else False

    def __lt__(self, other):
        m = self._get_magnitude(other)
        return self._magnitude < m if m is not NotImplemented else NotImplemented

    def __neg__(self):
        return self.__class__(-self._magnitude / self.multiplier, self._unit, self._format)

    def __pos__(self):
        return self

    def __abs__(self):
        return self.__class__(abs(self._magnitude) / self.multiplier, self._unit, self._format)

    def __add__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented: return NotImplemented
        return self.__class__((self._magnitude + m) / self.multiplier, self._unit, self._format)

    def __sub__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented: return NotImplemented
        return self.__class__((self._magnitude - m) / self.multiplier, self._unit, self._format)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__((self._magnitude * other) / self.multiplier, self._unit, self._format)
        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, self.__class__): return self._magnitude / other._magnitude
        if isinstance(other, (int, float)):
            return self.__class__((self._magnitude / other) / self.multiplier, self._unit, self._format)
        return NotImplemented


# -------------------------------------------------------------------------
# CLASES HIJAS DE DOMINIO FISICO
# -------------------------------------------------------------------------

class Time(Metric):
    _UNITS = UNITS_REGISTRY['Time']
    _DEFAULT_UNIT = 's'
    _ACCEPTED_FORMATS = ['short', 'clock']


class Distance(Metric):
    _UNITS = UNITS_REGISTRY['Distance']
    _DEFAULT_UNIT = 'm'
    _ACCEPTED_FORMATS = ['short']

    def __truediv__(self, other):
        if isinstance(other, Time):
            return Velocity(float(self) / float(other), (self.unit, other.unit), 'derived')
        if other.__class__.__name__ == 'Velocity':
            return Time(self.get(other.unit[0]) / float(other), other.unit[1], 'short')
        return super().__truediv__(other)


class Velocity(Metric):
    _UNITS = ((Distance, 1), (Time, -1))
    _DEFAULT_UNIT = ('m', 's')
    _ACCEPTED_FORMATS = ['derived']

    def __mul__(self, other):
        if isinstance(other, Time):
            return Distance(float(self) * other.get(self.unit[1]), self.unit[0], 'short')
        return super().__mul__(other)
 