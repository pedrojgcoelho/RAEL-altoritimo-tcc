"""Experimento sintetico deterministico. Nao representa energia medida em planta."""
import csv
import json
import math
from dataclasses import asdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
from modelo import *


def synthetic_weather(t,s,scenario):
    if s.elevation_deg<3: return Weather(t,0,0,0)
    envelope=max(0,s.up)**0.25
    if scenario=='claro': dni,dhi=850*envelope,80*envelope
    elif scenario=='difuso': dni,dhi=15*envelope,350*envelope
    else:
        # Variabilidade conhecida apenas pelo gerador, nao pelo controlador.
        minutes=(t.hour*60+t.minute)+t.second/60
        cloud=(math.sin(minutes*2*math.pi/37)+math.sin(minutes*2*math.pi/19))>0
        dni,dhi=(60*envelope,300*envelope) if cloud else (800*envelope,90*envelope)
    return Weather(t,dni,dhi,dni*max(0,s.up)+dhi)


def run():
    c=Config(); rows=[]; summaries=[]
    for scenario in ['claro','difuso','variavel']:
        for strategy in ['soltrack_backtracking','rael']:
            current=0.; last=None; gross=motor=travel=0.; count=0
            start=datetime(2026,3,20,0,tzinfo=timezone.utc)
            for minute in range(1440):
                t=start+timedelta(minutes=minute)
                s=solar_position(t,c); w=synthetic_weather(t,s,scenario)
                if strategy=='rael': d=decide(t,current,w,c,last_move=last)
                else:
                    target=backtracking(s,c) if s.elevation_deg>=3 else 0.
                    move=abs(target-current)>=c.deadband_deg
                    d=Decision('BASELINE',target if move else current,move)
                old=current
                current=motion(old,d.target_deg,60,c)
                distance=abs(current-old)
                used=motor_cost(old,current,c)
                if distance>1e-9: count+=1;last=t
                # Integracao em 6 pontos medios inclui deslocamento durante o ciclo.
                energy=0.
                for seconds in (5,15,25,35,45,55):
                    tm=t+timedelta(seconds=seconds); sm=solar_position(tm,c)
                    wm=synthetic_weather(tm,sm,scenario)
                    energy+=power(motion(old,d.target_deg,seconds,c),sm,wm,c)*10/3600
                gross+=energy; motor+=used;travel+=distance
                rows.append(dict(scenario=scenario,strategy=strategy,time_utc=t.isoformat(),
                                 angle_deg=current,mode=d.mode,gross_wh=energy,motor_wh=used))
            summaries.append(dict(scenario=scenario,strategy=strategy,gross_wh=gross,
                                  motor_wh=motor,net_wh=gross-motor,movements=count,travel_deg=travel))
    folder=Path(__file__).parent
    with (folder/'simulacao_sintetica.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    (folder/'resultados_sinteticos.json').write_text(json.dumps({'config':asdict(c),'results':summaries},indent=2),encoding='utf8')
    print(json.dumps(summaries,indent=2))


if __name__=='__main__': run()
