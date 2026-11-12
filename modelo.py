"""RAEL: rastreamento astronomico por energia liquida. Prototipo de pesquisa.

Eixo horizontal norte-sul, terreno plano, modulo monofacial.
Angulo positivo: normal voltada para leste. Angulos externos em graus.
Codigo novo: GPL-3.0-or-later; nucleo astronomico externo preservado em vendor/.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'vendor'))
from soltrack import Location, Time, computeSunPosition


def finite(*values):
    return all(math.isfinite(v) for v in values)


@dataclass(frozen=True)
class Config:
    latitude: float = -21.76  # Exemplo aproximado de Juiz de Fora; nao e levantamento da planta.
    longitude: float = -43.35
    pressure_kpa: float = 92.0
    temperature_k: float = 298.15
    gcr: float = 0.35
    limit_deg: float = 60.0
    area_m2: float = 2.0
    efficiency: float = 0.20
    albedo: float = 0.20
    horizon_s: int = 600
    sample_s: int = 60
    grid_deg: float = 1.0
    speed_deg_s: float = 1.0
    startup_wh: float = 0.02
    travel_wh_deg: float = 0.002
    wear_wh_deg: float = 0.0  # Penalidade equivalente, nao consumo eletrico.
    margin_wh: float = 0.02
    deadband_deg: float = 0.5
    min_interval_s: int = 120
    min_elevation_deg: float = 3.0
    max_weather_age_s: float = 180.0

    def __post_init__(self):
        if not finite(*self.__dict__.values()):
            raise ValueError('Configuracao contem NaN ou infinito')
        if not (-90 <= self.latitude <= 90 and -180 <= self.longitude <= 180):
            raise ValueError('Coordenadas invalidas')
        if not (0 < self.gcr < 1 and 0 < self.limit_deg < 80):
            raise ValueError('GCR ou limite invalido')
        if not (0 < self.efficiency <= 1 and self.area_m2 > 0 and 0 <= self.albedo <= 1):
            raise ValueError('Parametros fotovoltaicos invalidos')
        if self.pressure_kpa <= 0 or self.temperature_k <= 0:
            raise ValueError('Atmosfera invalida')
        if self.sample_s <= 0 or self.horizon_s < self.sample_s or self.horizon_s % self.sample_s:
            raise ValueError('Horizonte deve ser multiplo positivo da amostragem')
        if not 0 < self.grid_deg <= 10 or self.speed_deg_s <= 0:
            raise ValueError('Resolucao ou velocidade invalida')
        if any(x < 0 for x in (self.startup_wh, self.travel_wh_deg, self.wear_wh_deg,
                              self.margin_wh, self.deadband_deg, self.min_interval_s,
                              self.max_weather_age_s)):
            raise ValueError('Custos, margens e tempos devem ser nao negativos')


@dataclass(frozen=True)
class Sun:
    azimuth_deg: float
    elevation_deg: float
    east: float
    north: float
    up: float


@dataclass(frozen=True)
class Weather:
    time: datetime
    dni: float
    dhi: float
    ghi: float


@dataclass(frozen=True)
class Decision:
    mode: str
    target_deg: float
    move: bool
    predicted_gain_wh: float = 0.0
    predicted_motor_wh: float = 0.0
    reason: str = ''


def aware(t):
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError('Data e hora precisam de fuso explicito')
    return t.astimezone(timezone.utc)


def solar_position(t, c):
    t = aware(t)
    loc = Location(c.longitude, c.latitude, pressure=c.pressure_kpa, temperature=c.temperature_k)
    st = Time(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)
    # Preserva formulas do SolTrack; nao usa sua refracao fora do dominio diurno.
    p = computeSunPosition(loc, st, useDegrees=True, useNorthEqualsZero=True)
    e = p.altitudeRefract if p.altitude >= c.min_elevation_deg else p.altitude
    a = p.azimuthRefract % 360
    ar, er = math.radians(a), math.radians(e)
    return Sun(a, e, math.cos(er)*math.sin(ar), math.cos(er)*math.cos(ar), math.sin(er))


def true_tracking(s):
    return math.degrees(math.atan2(s.east, s.up))


def backtracking(s, c):
    if s.elevation_deg <= 0:
        return 0.0
    ideal = true_tracking(s)
    ratio = abs(math.cos(math.radians(ideal))) / c.gcr
    correction = math.degrees(math.acos(min(1.0, ratio)))
    theta = ideal - math.copysign(correction, ideal)
    return max(-c.limit_deg, min(c.limit_deg, theta))


def no_shade(theta, s, c):
    """Sombra direta entre fileiras infinitas identicas, mesmo angulo e mesma cota."""
    if s.elevation_deg < c.min_elevation_deg:
        return True
    ideal = math.radians(true_tracking(s))
    return c.gcr * abs(math.cos(math.radians(theta)-ideal)) <= math.cos(ideal)+1e-10


def power(theta, s, w, c):
    if s.elevation_deg < c.min_elevation_deg:
        return 0.0
    r = math.radians(theta)
    incidence = max(0.0, s.east * math.sin(r) + s.up * math.cos(r))
    poa = w.dni * incidence + w.dhi*(1+math.cos(r))/2 + c.albedo*w.ghi*(1-math.cos(r))/2
    return c.area_m2*c.efficiency*poa


def weather_valid(w, now, c, s):
    if w is None:
        return False
    age = (aware(now)-aware(w.time)).total_seconds()
    if not finite(w.dni, w.dhi, w.ghi) or min(w.dni, w.dhi, w.ghi) < 0:
        return False
    if not 0 <= age <= c.max_weather_age_s:
        return False
    closure = w.dni*max(0, s.up)+w.dhi
    return abs(w.ghi-closure) <= max(50.0, 0.15*w.ghi)


def motion(current, target, elapsed, c):
    return current + math.copysign(min(abs(target-current), c.speed_deg_s*elapsed), target-current)


def motor_cost(current, target, c):
    d = abs(target-current)
    return 0.0 if d < 1e-9 else c.startup_wh+c.travel_wh_deg*d


def forecast_samples(now, c):
    # Pontos medios: evita contar duas vezes extremos dos intervalos de integracao.
    return [(j*c.sample_s+c.sample_s/2,
             solar_position(now+timedelta(seconds=j*c.sample_s+c.sample_s/2), c))
            for j in range(c.horizon_s//c.sample_s)]


def decide(now, current, w, c=Config(), last_move=None, stow=False, communication_ok=True):
    now = aware(now)
    if not finite(current) or abs(current) > c.limit_deg:
        raise ValueError('Angulo medido invalido ou fora dos limites')
    if last_move is not None and aware(last_move) > now:
        raise ValueError('Instante do ultimo movimento esta no futuro')
    # Aqui retornam-se referencias; nenhum comando e escrito em equipamento.
    if not communication_ok:
        return Decision('FAULT_HOLD', current, False, reason='Comunicacao indisponivel')
    if stow:
        return Decision('STOW', 0.0, abs(current)>1e-9, reason='Referencia ilustrativa; configurar pelo fabricante')
    s = solar_position(now, c)
    if s.elevation_deg < c.min_elevation_deg:
        return Decision('NIGHT', 0.0, abs(current)>1e-9, reason='Parque horizontal de simulacao')
    if not weather_valid(w, now, c, s):
        target = backtracking(s, c)
        moved = abs(target-current) >= c.deadband_deg or not no_shade(current, s, c)
        return Decision('ASTRO_FALLBACK', target if moved else current, moved,
                        reason='Sem meteorologia valida; retorno geometrico sem otimizacao energetica')
    samples = forecast_samples(now, c)
    targets = {0.0, current, backtracking(s, c)}
    n = math.ceil(2*c.limit_deg/c.grid_deg)
    targets.update(-c.limit_deg+j*2*c.limit_deg/n for j in range(n+1))
    def trajectory_energy(target):
        return sum(power(motion(current,target,t,c),sun,w,c)*c.sample_s/3600 for t,sun in samples)
    def feasible(target):
        return no_shade(target,s,c) and all(
            no_shade(target,sun,c) and no_shade(motion(current,target,t,c),sun,c)
            for t,sun in samples)
    candidates = [x for x in targets if feasible(x)]
    if not candidates:
        return Decision('FAULT_HOLD', current, False, reason='Sem trajetoria amostrada viavel; exigir tratamento local')
    base = trajectory_energy(current)
    def score(x):
        return trajectory_energy(x)-motor_cost(current,x,c)-c.wear_wh_deg*abs(x-current)
    best = max(candidates, key=lambda x:(score(x), -abs(x-current), -abs(x)))
    gain = score(best)-base
    hold_safe = feasible(current)
    if hold_safe:
        if abs(best-current)<c.deadband_deg or gain<=c.margin_wh:
            return Decision('HOLD',current,False,gain,reason='Beneficio abaixo da margem ou da banda angular')
        if last_move is not None and (now-aware(last_move)).total_seconds()<c.min_interval_s:
            return Decision('HOLD',current,False,gain,reason='Intervalo minimo entre movimentos')
    mode = 'ENERGY_MOVE' if hold_safe else 'GEOMETRY_MOVE'
    return Decision(mode,best,abs(best-current)>1e-9,gain,motor_cost(current,best,c),
                    'Melhor alvo constante no horizonte; reavaliar no proximo ciclo')
