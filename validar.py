"""Validacao numerica independente com pvlib e testes de requisitos."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
import pvlib
from modelo import *


class Requirements(unittest.TestCase):
    def setUp(self):
        self.c=Config()
        self.t=datetime(2026,3,20,13,tzinfo=timezone.utc)
        self.s=solar_position(self.t,self.c)
        self.w=Weather(self.t,700,100,700*self.s.up+100)

    def test_upstream_fixture(self):
        c=replace(self.c,latitude=51.987380,longitude=5.950270,pressure_kpa=101,temperature_k=283)
        t=datetime(2045,7,16,6,2,49,217348,tzinfo=timezone.utc)
        s=solar_position(t,c)
        # A fixture publicada e da versao C; a porta Python nao e bit a bit identica.
        self.assertLess(abs(s.azimuth_deg-80.333093),0.001)
        self.assertLess(abs(s.elevation_deg-19.742741),0.001)

    def test_timezone(self):
        local=self.t.astimezone(timezone(timedelta(hours=-3)))
        self.assertEqual(solar_position(local,self.c), self.s)
        with self.assertRaises(ValueError): solar_position(self.t.replace(tzinfo=None),self.c)

    def test_invalid_config(self):
        for params in ({'gcr':0},{'grid_deg':0},{'sample_s':0},{'efficiency':2},{'latitude':float('nan')}):
            with self.assertRaises(ValueError): Config(**params)

    def test_bad_angle(self):
        for x in (float('nan'),float('inf'),61):
            with self.assertRaises(ValueError): decide(self.t,x,self.w,self.c)

    def test_weather(self):
        self.assertTrue(weather_valid(self.w,self.t,self.c,self.s))
        for w in (replace(self.w,dni=-1),replace(self.w,dhi=float('nan')),
                  replace(self.w,time=self.t-timedelta(seconds=181)),
                  replace(self.w,time=self.t+timedelta(seconds=1)),replace(self.w,ghi=0)):
            self.assertFalse(weather_valid(w,self.t,self.c,self.s))

    def test_fallback(self):
        d=decide(self.t,0,None,self.c)
        self.assertEqual(d.mode,'ASTRO_FALLBACK')
        self.assertAlmostEqual(d.target_deg,backtracking(self.s,self.c))

    def test_stow_and_failure(self):
        self.assertEqual(decide(self.t,20,self.w,self.c,stow=True).target_deg,0)
        d=decide(self.t,20,self.w,self.c,communication_ok=False)
        self.assertFalse(d.move)
        self.assertEqual(d.mode,'FAULT_HOLD')

    def test_night(self):
        self.assertEqual(decide(self.t.replace(hour=3),0,self.w,self.c).mode,'NIGHT')

    def test_motor_accounting(self):
        self.assertEqual(motor_cost(3,3,self.c),0)
        self.assertAlmostEqual(motor_cost(0,10,self.c),0.04)

    def test_slew(self):
        self.assertEqual(motion(20,-20,5,self.c),15)
        self.assertEqual(motion(20,-20,100,self.c),-20)

    def test_diffuse_horizontal(self):
        w=Weather(self.t,0,300,300)
        # Sem custo por grau, o maximo isotropico puramente difuso e horizontal.
        d=decide(self.t,25,w,replace(self.c,travel_wh_deg=0))
        self.assertEqual(d.mode,'ENERGY_MOVE')
        self.assertAlmostEqual(d.target_deg,0)

    def test_expensive_motor_holds(self):
        d=decide(self.t,0,self.w,replace(self.c,startup_wh=1e6))
        self.assertEqual(d.mode,'HOLD')

    def test_minimum_interval(self):
        d=decide(self.t,0,self.w,self.c,last_move=self.t-timedelta(seconds=1))
        self.assertEqual(d.mode,'HOLD')

    def test_limits_and_constraint(self):
        for h in (10,12,15,18,20):
            t=self.t.replace(hour=h)
            s=solar_position(t,self.c)
            if s.elevation_deg<3: continue
            w=Weather(t,600,150,600*s.up+150)
            d=decide(t,0,w,self.c)
            self.assertLessEqual(abs(d.target_deg),self.c.limit_deg)
            self.assertTrue(no_shade(d.target_deg,s,self.c))


def independent_comparison():
    errors=[]; geometry=[]
    # Mesma atmosfera em ambos, altitude geometrica da estacao = 0 m.
    for lat,lon in [(-21.76,-43.35),(-3.72,-38.54),(51.99,5.95),(0,0)]:
        c=Config(latitude=lat,longitude=lon,pressure_kpa=101,temperature_k=283)
        for date in ['2026-03-20','2026-06-21','2026-09-22','2026-12-21']:
            times=pd.date_range(date,periods=48,freq='30min',tz='UTC')
            spa=pvlib.solarposition.spa_python(times,lat,lon,altitude=0,pressure=101000,temperature=9.85)
            for t,(_,ref) in zip(times,spa.iterrows()):
                s=solar_position(t.to_pydatetime(),c)
                if s.elevation_deg<5: continue
                a,e=math.radians(ref.azimuth),math.radians(ref.apparent_elevation)
                v=(math.cos(e)*math.sin(a),math.cos(e)*math.cos(a),math.sin(e))
                dot=s.east*v[0]+s.north*v[1]+s.up*v[2]
                errors.append(math.degrees(math.acos(max(-1,min(1,dot)))))
                p=pvlib.tracking.singleaxis(90-s.elevation_deg,s.azimuth_deg,axis_tilt=0,
                                           axis_azimuth=0,max_angle=60,backtrack=True,gcr=c.gcr)
                # Com axis_azimuth=0, ambas convencoes usam positivo para leste.
                geometry.append(abs(backtracking(s,c)-float(np.asarray(p['tracker_theta']).item())))
    result={'samples':len(errors),'solar_separation_mean_deg':float(np.mean(errors)),
            'solar_separation_max_deg':max(errors),'backtracking_max_difference_deg':max(geometry),
            'pvlib_version':pvlib.__version__}
    if max(errors)>0.1: raise AssertionError(result)
    if max(geometry)>1e-6: raise AssertionError(result)
    return result


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Requirements)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful(): raise SystemExit(1)
    report={'unit_tests':result.testsRun,'independent_comparison':independent_comparison()}
    Path(__file__).with_name('validacao.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))
