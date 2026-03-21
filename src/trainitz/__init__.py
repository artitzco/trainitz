import pandas as pd
from datetime import datetime, timedelta
from trainitz.metrics import Time, Distance


class TrainingPlanGenerator:
    """
    Generador de planes de entrenamiento semanales basados en parámetros variables.
    """

    _UNIT_CONFIG = {
        'time': {'class': Time, 'unit': 'minutes'},
        'distance': {'class': Distance, 'unit': 'kilometers'},
    }

    def __init__(self, data_list, round_to_half=True, unit='time'):
        if unit not in self._UNIT_CONFIG:
            raise ValueError(
                f"unit must be one of {list(self._UNIT_CONFIG)}, got {unit!r}")

        self.data_list = data_list or []
        self.round_to_half = round_to_half
        self.unit = unit
        self.plan = []

        # Variables de Estado (State) para cálculos entre semanas
        self.last_load_vol = None
        self.prev_vol = None

        # Estado de la tirada larga (Long Run)
        self.long_run_base = 0
        self.long_run_increment = 0
        self.last_load_long_run = None
        self.prev_long_run = None

    def _to_monday(self, dt):
        """Normaliza una fecha al lunes de su respectiva semana."""
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
        return dt - timedelta(days=dt.weekday())

    def _prepare_data(self):
        """Normaliza fechas, resuelve semanas relativas y ordena la configuración de entrada."""
        # Paso 1: Normalizar fechas absolutas y validar presencia de 'week'
        for d in self.data_list:
            if 'week' not in d:
                return False  # 'week' es estrictamente obligatorio
            if not isinstance(d['week'], int):
                d['week'] = self._to_monday(d['week'])
            if 'finish' in d and not isinstance(d['finish'], int):
                d['finish'] = self._to_monday(d['finish'])

        base_start_date = next(
            (d['week'] for d in self.data_list if not isinstance(d['week'], int)), None)

        # Paso 2: Resolver 'week' relativas POSITIVAS y duraciones en orden de inserción
        last_stack_finish = None
        for d in self.data_list:
            if isinstance(d['week'], int) and d['week'] >= 0:
                base = last_stack_finish if d.get('stack') else base_start_date
                if base is None:
                    return False
                d['week'] = base + timedelta(days=d['week'] * 7)

            if not isinstance(d['week'], int):
                # Resolver duraciones 'finish'
                if 'finish' in d and isinstance(d['finish'], int):
                    if d['finish'] <= 0:
                        return False
                    d['finish'] = d['week'] + timedelta(days=(d['finish'] - 1) * 7)
                
                # Actualizar el stack hacia la siguiente semana disponible si aplica
                if d.get('stack') and 'finish' in d and not isinstance(d['finish'], int):
                    last_stack_finish = d['finish'] + timedelta(days=7)

        # Paso 3: Obtener la fecha global de fin para usarla como ancla en relativas hacia atrás
        all_finishes = [d['finish'] for d in self.data_list if 'finish' in d and not isinstance(d['finish'], int)]
        if not all_finishes:
            return False  # Ni un solo finish especificado = tabla vacía
            
        global_finish_date = max(all_finishes)

        # Paso 4: Resolver 'week' relativas NEGATIVAS en orden inverso (de abajo hacia arriba)
        next_stack_week = None
        for d in reversed(self.data_list):
            if isinstance(d['week'], int) and d['week'] < 0:
                if d.get('stack') and next_stack_week is not None:
                    # En una pila, resta las semanas directamente desde el inicio del bloque posterior
                    d['week'] = next_stack_week + timedelta(days=d['week'] * 7)
                else:
                    target_finish = d.get('finish', global_finish_date)
                    if target_finish is None or isinstance(target_finish, int):
                        return False
                    # Último de la pila o anclado globalmente. Regla inclusiva del final.
                    d['week'] = target_finish + timedelta(days=(d['week'] + 1) * 7)

                if d.get('stack'):
                    next_stack_week = d['week']
            elif not isinstance(d['week'], int):
                if d.get('stack'):
                    next_stack_week = d['week']
        
        self.data_list = sorted(self.data_list, key=lambda x: x['week'])
        return True

    def _get_active_params(self, current_week):
        """Recupera los parámetros vigentes ACUMULADOS para la semana actual."""
        active_params = {}
        for d in self.data_list:
            if d['week'] <= current_week:
                active_params.update(d)
            else:
                break
        return active_params

    def _determine_phase(self, current_week, finish_week, cycle):
        """Determina si la fase en curso es de Carga (L) o Descarga (D) usando lógica inversa."""
        parts = cycle.split('-')
        repeating = parts[0]
        suffix = parts[1] if len(parts) > 1 else ""

        n = (finish_week - current_week).days // 7

        if n < 0:
            return 'D'
        elif n < len(suffix):
            return suffix[len(suffix) - 1 - n]
        else:
            n_adj = n - len(suffix)
            rev_repeating = repeating[::-1]
            return rev_repeating[n_adj % len(repeating)]

    def _calculate_total_volume(self, current_week, active_params, status, increment, deload):
        """Calcula el volumen para la semana dada y actualiza el estado interno de volumen."""
        current_entry = next(
            (d for d in self.data_list if d['week'] == current_week), {})

        # Caso A: Volumen establecido explícitamente para esta semana específica
        if 'volume' in current_entry:
            base_vol = current_entry['volume']
            current_vol = base_vol * deload if status == 'D' else base_vol
            # Sincronizamos la memoria de carga
            self.last_load_vol = base_vol

        # Caso B: Cálculo por incremento o descarga
        else:
            if status == 'L':
                if self.last_load_vol is not None:
                    current_vol = self.last_load_vol + increment
                elif self.prev_vol is not None:
                    current_vol = active_params.get('volume', 0) + increment
                else:
                    current_vol = active_params.get('volume', 0)
            else:  # status == 'D'
                if self.prev_vol is not None:
                    current_vol = self.prev_vol * deload
                else:
                    current_vol = active_params.get('volume', 0) / deload

        # Actualizar rastreadores de estado
        if status == 'L':
            self.last_load_vol = current_vol
        self.prev_vol = current_vol

        return current_vol, current_entry

    def _setup_long_run(self, current_week, finish_week, current_entry, suffix, repeating):
        """Configura los incrementos necesarios para la tirada larga si inicia un bloque."""
        lr_start, lr_finish = current_entry['long_run']
        self.long_run_base = lr_start

        # Contar semanas L desde actual hasta finish
        l_count = 0
        temp_week = current_week
        while temp_week <= finish_week:
            st = self._determine_phase(
                temp_week, finish_week, f"{repeating}-{suffix}" if suffix else repeating)
            if st == 'L':
                l_count += 1
            temp_week += timedelta(days=7)

        if l_count > 1:
            self.long_run_increment = (lr_finish - lr_start) / (l_count - 1)
        else:
            self.long_run_increment = 0

        self.last_load_long_run = None

    def _calculate_long_run(self, active_params, current_entry, status):
        """Calcula la tirada larga semanal."""
        current_long_run = None
        if 'long_run' in active_params:
            if status == 'L':
                if 'long_run' in current_entry:
                    current_long_run = self.long_run_base
                else:
                    if self.last_load_long_run is not None:
                        current_long_run = self.last_load_long_run + self.long_run_increment
                    else:
                        current_long_run = self.long_run_base
            else:  # status == 'D'
                deload = active_params.get('deload', 1.0)
                if 'long_run' in current_entry:
                    current_long_run = self.long_run_base * deload
                elif self.prev_long_run is not None:
                    current_long_run = self.prev_long_run * deload
                else:
                    current_long_run = self.long_run_base / deload if deload else self.long_run_base

            # Actualizar estado del Long Run
            if status == 'L' and current_long_run is not None:
                self.last_load_long_run = current_long_run
            if current_long_run is not None:
                self.prev_long_run = current_long_run

        return current_long_run

    def _calculate_specifics(self, current_vol, current_long_run, specifics):
        """Calcula de forma distributiva los entrenamientos específicos del día en la semana."""
        rem_vol = current_vol - \
            (current_long_run if current_long_run is not None else 0)

        sp_vols = []
        if specifics is not None:
            if isinstance(specifics, (int, float)):
                specifics = [specifics]

            total_x = sum(specifics)
            for x in specifics:
                sp_vols.append(rem_vol * x)
            # Agregar el restante si es mayor a 0
            if round(1.0 - total_x, 4) > 0:
                sp_vols.append(rem_vol * (1.0 - total_x))
        else:
            sp_vols.append(rem_vol)

        if self.round_to_half:
            return [round(v * 2) / 2 for v in sp_vols]
        else:
            return [round(v, 2) for v in sp_vols]

    def _to_metric(self, value):
        """Convierte un valor numérico a la instancia de métrica correspondiente."""
        cfg = self._UNIT_CONFIG[self.unit]
        return cfg['class'](value, cfg['unit'])

    def _format_row(self, current_week, active_params, status, current_vol, current_long_run, sp_vols):
        """Formatea todas las variables procesadas a un dict (que será una fila del DataFrame)."""
        iso_year, iso_week, _ = current_week.isocalendar()

        lr_val = None
        if current_long_run is not None:
            lr_rounded = round(current_long_run * 2) / \
                2 if self.round_to_half else round(current_long_run, 2)
            lr_val = self._to_metric(lr_rounded)

        row = {
            'ISO_Week': f"{str(iso_year)[-2:]}-{iso_week:02d}",
            'Week': current_week,
            'Stage': active_params.get('stage'),
            'Phase': status,
            'Increment': active_params.get('increment', 0),
            'Deload': active_params.get('deload', 1.0),
            'Volume': self._to_metric(current_vol),
            'LR': lr_val
        }

        for idx, sp_val in enumerate(sp_vols, 1):
            row[f'Sp_{idx}'] = self._to_metric(sp_val)

        return row

    def generate(self) -> pd.DataFrame:
        """
        Orquesta los métodos internos y devuelve el DataFrame Final.
        Este es el único método público que se debe llamar desde afuera.
        """
        empty_cols = ['ISO_Week', 'Week', 'Stage',
                      'Phase', 'Increment', 'Deload', 'Volume', 'LR']
                      
        # Limpiar estados por si el método se manda a llamar 2 o más veces
        self.plan = []
        self.last_load_vol = None
        self.prev_vol = None
        self.long_run_base = 0
        self.long_run_increment = 0
        self.last_load_long_run = None
        self.prev_long_run = None

        if not self.data_list:
            return pd.DataFrame(columns=empty_cols)

        success = self._prepare_data()
        if not success:
            return pd.DataFrame(columns=empty_cols)

        start_date = self.data_list[0]['week']

        # Determinar fecha final global
        finishes = [d['finish'] for d in self.data_list if 'finish' in d]
        end_date = max(finishes)

        weeks = pd.date_range(start=start_date, end=end_date, freq='W-MON')

        for current_week in weeks:
            active_params = self._get_active_params(current_week)
            if not active_params:
                continue

            # Si el bloque activo no tiene finish explícito, asume el final del plan global
            finish_week = active_params.get('finish', end_date)
            cycle = active_params.get('cycle', 'L')
            increment = active_params.get('increment', 0)
            deload = active_params.get('deload', 1.0)
            specifics = active_params.get('specifics')

            # 1. Determinar fase (Carga L / Descarga D)
            status = self._determine_phase(current_week, finish_week, cycle)

            # 2. Calcular volumen total
            current_vol, current_entry = self._calculate_total_volume(
                current_week, active_params, status, increment, deload
            )

            # 3. Preparar y calcular Long Run
            if 'long_run' in current_entry:
                parts = cycle.split('-')
                suffix = parts[1] if len(parts) > 1 else ""
                repeating = parts[0]
                self._setup_long_run(
                    current_week, finish_week, current_entry, suffix, repeating)

            current_long_run = self._calculate_long_run(
                active_params, current_entry, status)

            # 4. Calcular trabajos específicos a lo largo de la semana
            sp_vols = self._calculate_specifics(
                current_vol, current_long_run, specifics)

            # 5. Formatear y añadir fila
            row = self._format_row(
                current_week, active_params, status, current_vol, current_long_run, sp_vols
            )
            self.plan.append(row)

        return pd.DataFrame(self.plan)
