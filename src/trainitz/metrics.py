import functools
import re

# -------------------------------------------------------------------------
# 0. SISTEMA DE UNIDADES
# -------------------------------------------------------------------------

class UnitDef:
    """Definición de una unidad física con todas sus representaciones."""
    def __init__(self, multiplier, short, long=None, plural=None):
        self.multiplier = multiplier
        self.short = short               # 'h'
        self.long = long or short         # 'hour'
        self.plural = plural or self.long # 'hours'

    def match(self, alias):
        """¿Este alias pertenece a esta unidad?"""
        return alias in (self.short, self.long, self.plural)

    def display(self, format_name):
        """Devuelve el alias adecuado según el formato visual."""
        if format_name == 'long':
            return self.plural
        return self.short

class UnitSystem:
    """Sistema de unidades para un tipo de métrica."""
    def __init__(self, *units, formats=None):
        self.units = units                     # tupla de UnitDef
        self.formats = formats or ['short']    # formatos aceptados

    def find(self, alias):
        """Busca la UnitDef que coincida con un alias."""
        for u in self.units:
            if u.match(alias):
                return u
        raise ValueError(f"Unknown unit: {alias}")

    def canonical(self, alias):
        """Devuelve el nombre canónico (short) para cualquier alias."""
        return self.find(alias).short

    def multiplier(self, alias):
        return self.find(alias).multiplier

    def display(self, canonical_unit, format_name):
        return self.find(canonical_unit).display(format_name)

    def __contains__(self, alias):
        return any(u.match(alias) for u in self.units)

TIME_UNITS = UnitSystem(
    UnitDef(3600,  'h',  'hour',        'hours'),
    UnitDef(60,    'min','minute',       'minutes'),
    UnitDef(1,     's',  'second',       'seconds'),
    UnitDef(0.001, 'ms', 'millisecond',  'milliseconds'),
    formats=['short', 'long', 'clock']
)

DISTANCE_UNITS = UnitSystem(
    UnitDef(1000, 'km', 'kilometer', 'kilometers'),
    UnitDef(1,    'm',  'meter',     'meters'),
    formats=['short', 'long']
)

# -------------------------------------------------------------------------
# 1. FORMATTERS (Representaciones visuales y parseo)
# -------------------------------------------------------------------------
# Desacoplamos la vista del modelo. Las físicas operan sobre magnitudes; 
# los formatos operan sobre cómo "dibujar" o "leer" un string.

def render_short(mag, factor, unit_name):
    val = abs(mag / factor)
    prec = 3 if unit_name in ('km', 'kilometer', 'kilometers') else 2
    val_str = str(int(val)) if val.is_integer() else f"{val:.{prec}f}".rstrip('0').rstrip('.')
    sgn = "-" if mag < 0 else ""
    return f"{sgn}{val_str}{unit_name}"

def render_long(mag, factor, unit_name):
    val = abs(mag / factor)
    prec = 3 if unit_name in ('km', 'kilometer', 'kilometers') else 2
    val_str = str(int(val)) if val.is_integer() else f"{val:.{prec}f}".rstrip('0').rstrip('.')
    sgn = "-" if mag < 0 else ""
    return f"{sgn}{val_str} {unit_name}"

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
    if secs >= 60:
        mins += 1
        secs -= 60
    if mins >= 60:
        hrs += 1
        mins -= 60
    milis_str = f".{milis:03d}".rstrip('0') if milis > 0 else ""
    sgn = "-" if mag < 0 else ""
    if hrs > 0:
        return f"{sgn}{hrs}:{mins:02d}:{secs:02d}{milis_str}"
    return f"{sgn}{mins}:{secs:02d}{milis_str}"

class FormatPattern:
    def __init__(self, regex, parser, renderer=None):
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
    'long': FormatPattern(
        regex = r'^(?P<sgn>-)?(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z]+)$',
        parser = lambda m: (
            float(m.group('val')) * (-1 if m.group('sgn') else 1),
            m.group('unit')
        ),
        renderer = render_long
    ),
    'derived': FormatPattern(
        regex = r'^(?P<sgn>-)?(?P<val>\d+(?:\.\d+)?)\s*(?P<u1>[a-zA-Z]+)/(?P<u2>[a-zA-Z]+)$',
        parser = lambda m: (
            float(m.group('val')) * (-1 if m.group('sgn') else 1),
            (m.group('u1'), m.group('u2'))
        ),
    ),
    'clock_ratio': FormatPattern(
        regex = r'^(?P<sgn>-)?(?:(?P<h>\d+):)?(?P<m>\d+):(?P<s>\d{2})(?:\.(?P<ms>\d+))?/(?P<u2>[a-zA-Z]+)$',
        parser = lambda m: (
            float((-1 if m.group('sgn') else 1) * (
                int(m.group('h') or 0) * 3600 +
                int(m.group('m') or 0) * 60 +
                int(m.group('s')) +
                float("0." + (m.group('ms') or "0"))
            )),
            ('s', m.group('u2'))
        ),
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
    def _is_multidim(cls):
        """True si _UNITS es una lista de tuplas (UnitSystem, exponente)."""
        return isinstance(cls._UNITS, (list, tuple)) and \
            len(cls._UNITS) > 0 and isinstance(cls._UNITS[0], tuple)

    # ----- helpers para la notación slash basada en exponentes -----

    @classmethod
    def _dim_separator(cls):
        """Devuelve el separador que une las dimensiones según los exponentes.
        Si hay al menos un exponente negativo se usa '/', de lo contrario '*'."""
        if not cls._is_multidim():
            return None
        for _, exp in cls._UNITS:
            if exp < 0:
                return '/'
        return '*'

    @classmethod
    def _contract(cls, components):
        """Contrae una tupla de componentes a su notación string.
        ('km', 'h') → 'km/h' si los exponentes son (1, -1)."""
        sep = cls._dim_separator()
        if sep is None:
            return components
        return sep.join(str(c) for c in components)

    @classmethod
    def _expand(cls, notation):
        """Expande una notación string a tupla según el separador.
        'km/h' → ('km', 'h')  |  'short/short' → ('short', 'short')"""
        if isinstance(notation, tuple):
            return notation
        sep = cls._dim_separator()
        if sep and isinstance(notation, str) and sep in notation:
            return tuple(notation.split(sep))
        return notation

    @classmethod
    def _accepted_formats(cls):
        if cls._is_multidim():
            return cls._ACCEPTED_FORMATS
        if isinstance(cls._UNITS, UnitSystem):
            return cls._UNITS.formats
        return getattr(cls, '_ACCEPTED_FORMATS', ['short'])

    @classmethod
    def _get_multiplier(cls, unit):
        """Resolves the conversion factor for a given unit."""
        if isinstance(cls._UNITS, UnitSystem):
            return cls._UNITS.multiplier(unit)

        unit_tuple = unit if isinstance(unit, tuple) else (unit,)
        if len(unit_tuple) != len(cls._UNITS):
            raise ValueError(f"Unit {unit} does not match {cls.__name__} dimensions.")

        factor = 1.0
        for u, (unit_system, exponent) in zip(unit_tuple, cls._UNITS):
            factor *= (unit_system.multiplier(u) ** exponent)
        return factor

    def __init__(self, value=0, unit=None, format=None):
        is_multidim = self.__class__._is_multidim()

        if isinstance(value, str):
            mag, det_unit, det_format = self._parse_string(value)
            self._magnitude = mag
            target_unit = self.__class__._expand(unit) if unit else det_unit
            target_format = self.__class__._expand(format) if format else det_format
        else:
            raw_unit = unit or self.__class__._DEFAULT_UNIT
            target_unit = self.__class__._expand(raw_unit)
            default_fmt = self._accepted_formats()[0] if not is_multidim \
                else self._accepted_formats()[0] if self._accepted_formats() \
                else ('short',) * len(self.__class__._UNITS)
            target_format = self.__class__._expand(format) if format else default_fmt

            if isinstance(value, (int, float)):
                pass  # computed below
            elif isinstance(value, self.__class__):
                self._magnitude = value._magnitude
            else:
                raise ValueError(f"Invalid {self.__class__.__name__.lower()} format: {value}")

        if is_multidim:
            target_unit = target_unit if isinstance(target_unit, tuple) else (target_unit,)
            if len(target_unit) != len(self.__class__._UNITS):
                raise ValueError(f"Invalid multidimensional unit: {target_unit}")

            # Validar abreviaturas si fue explícito, y construir unit canónica
            canonical_unit = []
            for u, (unit_system, _) in zip(target_unit, self.__class__._UNITS):
                udef = unit_system.find(u)
                if unit is not None and u != udef.short:
                    raise ValueError(
                        f"Multi-dimensional units must use abbreviations "
                        f"(expected '{udef.short}', got '{u}')")
                canonical_unit.append(udef.short)

            self._unit = tuple(canonical_unit)

            target_format = target_format if isinstance(target_format, tuple) \
                else (target_format,) * len(self.__class__._UNITS)
            if len(target_format) != len(self.__class__._UNITS):
                raise ValueError(f"Invalid multidimensional format: {target_format}")

            # Validar formatos exactos contra los aceptados
            if target_format not in self._accepted_formats():
                if isinstance(format, str):
                    raise ValueError(f"Invalid multidimensional format: '{format}'")
                raise ValueError(
                    f"Format {target_format} not in accepted formats "
                    f"for {self.__class__.__name__}")

            self._format = target_format

            if not isinstance(value, str) and isinstance(value, (int, float)):
                self._magnitude = float(value) * self.multiplier
        else:
            self._unit = self.__class__._UNITS.canonical(target_unit)
            self._format = target_format
            if not isinstance(value, str) and isinstance(value, (int, float)):
                self._magnitude = float(value) * self.multiplier

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
        target_unit = self.__class__._expand(unit) if unit else self._unit
        target_format = self.__class__._expand(format) if format else self._format

        if not self.__class__._is_multidim():
            if isinstance(self.__class__._UNITS, UnitSystem):
                target_unit = self.__class__._UNITS.canonical(target_unit)
            if target_format not in self._accepted_formats():
                raise ValueError(
                    f"Format {target_format} not available for {self.__class__.__name__}")

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
        if self.__class__._is_multidim():
            formats = self._format if isinstance(self._format, tuple) \
                else (self._format,) * len(self._unit)
            sep = self.__class__._dim_separator() or '/'

            # --- Numerador (primer componente) ---
            unit_sys_num = self.__class__._UNITS[0][0]
            factor_num = unit_sys_num.multiplier(self._unit[0])

            val = abs(self._magnitude / self.multiplier)
            mock_mag = val * factor_num
            display_num = unit_sys_num.display(self._unit[0], formats[0])
            rendered_num = FORMATS[formats[0]].renderer(
                mock_mag, factor_num, display_num)

            # --- Denominador (componentes restantes) ---
            denominators = []
            for i in range(1, len(self._unit)):
                unit_sys_den = self.__class__._UNITS[i][0]
                display_den = unit_sys_den.display(self._unit[i], formats[i])

                if formats[i] == 'clock':
                    factor_den = unit_sys_den.multiplier(self._unit[i])
                    rendered_den = FORMATS['clock'].renderer(
                        factor_den, factor_den, "")
                    denominators.append(rendered_den)
                else:
                    denominators.append(display_den)

            sgn = "-" if self._magnitude < 0 else ""
            res = f"{sgn}{rendered_num}"
            if denominators:
                res += sep + sep.join(denominators)
            return res

        format_name = self._format
        accepted = self._accepted_formats()
        if format_name not in accepted:
            format_name = accepted[0]

        display_unit = self.__class__._UNITS.display(self._unit, format_name)
        return FORMATS[format_name].renderer(
            self._magnitude, self.multiplier, display_unit)

    def __repr__(self):
        return self.__str__()

    @classmethod
    def read(cls, string):
        """Reads a string and returns a metric instance."""
        return cls(string)

    @classmethod
    def _parse_string(cls, string):
        accepted = cls._accepted_formats()
        # Para multidim, aplanar a nombres de formato base para parseo
        if cls._is_multidim():
            parse_formats = set()
            for fmt_tuple in accepted:
                for f in fmt_tuple:
                    parse_formats.add(f)
            # Incluir el regex de parseo multidim según el separador
            sep = cls._dim_separator()
            if sep == '/':
                parse_formats.add('derived')
                parse_formats.add('clock_ratio')
            parse_formats = list(parse_formats)
        else:
            parse_formats = list(accepted)

        tried_text = False
        for format_name in parse_formats:
            is_text = format_name in ('short', 'long')
            if is_text:
                if tried_text:
                    continue
                tried_text = True

            fmt = FORMATS.get(format_name if not is_text else 'short')
            if fmt is None:
                continue
            match = fmt.regex.match(string)
            if not match:
                continue
            res = fmt.parser(match)
            if res is None:
                continue
            val, parsed_unit = res

            if isinstance(cls._UNITS, UnitSystem):
                if parsed_unit not in cls._UNITS:
                    continue
                unit_def = cls._UNITS.find(parsed_unit)
                canonical = unit_def.short
                mag = val * unit_def.multiplier

                if is_text:
                    detected = 'long' if parsed_unit != canonical else 'short'
                else:
                    detected = format_name
                return mag, canonical, detected
            else:
                if not isinstance(parsed_unit, tuple) or \
                        len(parsed_unit) != len(cls._UNITS):
                    continue
                try:
                    factor = cls._get_multiplier(parsed_unit)
                    detected_format = []
                    canonical_unit = []
                    for idx, (u, (unit_system, _)) in enumerate(
                            zip(parsed_unit, cls._UNITS)):
                        udef = unit_system.find(u)
                        canonical_unit.append(udef.short)
                        if format_name == 'clock_ratio' and idx == 0:
                            detected_format.append('clock')
                        else:
                            detected_format.append(
                                'long' if u != udef.short else 'short')
                except ValueError:
                    continue
                mag = val * factor
                return mag, tuple(canonical_unit), tuple(detected_format)

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
        return self.__class__(-self._magnitude / self.multiplier,
                              self._unit, self._format)

    def __pos__(self):
        return self

    def __abs__(self):
        return self.__class__(abs(self._magnitude) / self.multiplier,
                              self._unit, self._format)

    def __add__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented: return NotImplemented
        return self.__class__((self._magnitude + m) / self.multiplier,
                              self._unit, self._format)

    def __sub__(self, other):
        m = self._get_magnitude(other)
        if m is NotImplemented: return NotImplemented
        return self.__class__((self._magnitude - m) / self.multiplier,
                              self._unit, self._format)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__((self._magnitude * other) / self.multiplier,
                                  self._unit, self._format)
        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, (int, float)):
            return self.__mul__(other)
        return NotImplemented

    def __radd__(self, other):
        if other == 0:
            return self
        return self.__add__(other)

    def __rsub__(self, other):
        if isinstance(other, (int, float)):
            return self.__class__((other * self.multiplier - self._magnitude) / self.multiplier,
                                  self._unit, self._format)
        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, self.__class__):
            return self._magnitude / other._magnitude
        if isinstance(other, (int, float)):
            return self.__class__((self._magnitude / other) / self.multiplier,
                                  self._unit, self._format)
        return NotImplemented


# -------------------------------------------------------------------------
# CLASES HIJAS DE DOMINIO FISICO
# -------------------------------------------------------------------------

class Time(Metric):
    _UNITS = TIME_UNITS
    _DEFAULT_UNIT = 's'

    def __mul__(self, other):
        if isinstance(other, Velocity):
            return Distance(
                float(other) * self.get(other.unit[1]),
                other.unit[0], other.format[0])
        return super().__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, Distance):
            fmt = (self.format, other.format)
            if fmt not in Slowness._ACCEPTED_FORMATS:
                fmt = Slowness._ACCEPTED_FORMATS[0]
            return Slowness(
                float(self) / float(other),
                (self.unit, other.unit), fmt)
        if isinstance(other, Slowness):
            return Distance(
                self.get(other.unit[0]) / float(other),
                other.unit[1], other.format[1])
        return super().__truediv__(other)


class Distance(Metric):
    _UNITS = DISTANCE_UNITS
    _DEFAULT_UNIT = 'm'

    def __mul__(self, other):
        if isinstance(other, Slowness):
            return Time(
                float(other) * self.get(other.unit[1]),
                other.unit[0], other.format[0])
        return super().__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, Time):
            fmt = (self.format, other.format)
            if fmt not in Velocity._ACCEPTED_FORMATS:
                fmt = Velocity._ACCEPTED_FORMATS[0]
            return Velocity(
                float(self) / float(other),
                (self.unit, other.unit), fmt)
        if isinstance(other, Velocity):
            return Time(
                self.get(other.unit[0]) / float(other),
                other.unit[1], other.format[1])
        return super().__truediv__(other)


class Velocity(Metric):
    _UNITS = ((DISTANCE_UNITS, 1), (TIME_UNITS, -1))
    _DEFAULT_UNIT = ('m', 's')
    _ACCEPTED_FORMATS = [
        ('short', 'short'),
        ('short', 'long'),
        ('long', 'short'),
        ('long', 'long'),
    ]


    def __mul__(self, other):
        if isinstance(other, Time):
            return Distance(
                float(self) * other.get(self.unit[1]),
                self.unit[0], self.format[0])
        if isinstance(other, Slowness):
            return self._magnitude * other._magnitude
        return super().__mul__(other)

    def __rtruediv__(self, other):
        if isinstance(other, (int, float)):
            fmt = (self.format[1], self.format[0])
            if fmt not in Slowness._ACCEPTED_FORMATS:
                fmt = Slowness._ACCEPTED_FORMATS[0]
            return Slowness(
                other / float(self),
                (self.unit[1], self.unit[0]), fmt)
        return NotImplemented


class Slowness(Metric):
    _UNITS = ((TIME_UNITS, 1), (DISTANCE_UNITS, -1))
    _DEFAULT_UNIT = ('s', 'm')
    _ACCEPTED_FORMATS = [
        ('short', 'short'),
        ('short', 'long'),
        ('long', 'short'),
        ('long', 'long'),
    ]

    def __mul__(self, other):
        if isinstance(other, Distance):
            return Time(
                float(self) * other.get(self.unit[1]),
                self.unit[0], self.format[0])
        if isinstance(other, Velocity):
            return self._magnitude * other._magnitude
        return super().__mul__(other)

    def __rtruediv__(self, other):
        if isinstance(other, (int, float)):
            fmt = (self.format[1], self.format[0])
            if fmt not in Velocity._ACCEPTED_FORMATS:
                fmt = Velocity._ACCEPTED_FORMATS[0]
            return Velocity(
                other / float(self),
                (self.unit[1], self.unit[0]), fmt)
        return NotImplemented