# Protótipo RAEL para o TCC

Este pacote desenvolve um modelo astronômico de rastreamento orientado à energia líquida, com equações, código e verificação reproduzível. O núcleo de posição solar é o SolTrack indicado pelo usuário. A contribuição proposta é a política que decide quando e para onde mover o tracker.

Comece por **Modelo_astronomico_RAEL.md**. O documento explica hipóteses, equações, algoritmo, limitações, resultados e um texto sugerido para o TCC. **Fontes_e_rastreabilidade.md** identifica a função dos 32 PDFs na pesquisa e os ajustes bibliográficos encontrados.

## Executar

Requer Python 3.11 ou superior para o conjunto de bibliotecas de validação fixado. Os ensaios entregues foram executados com Python 3.12.14. Em um terminal aberto nesta pasta:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-validacao.txt
.\.venv\Scripts\python.exe validar.py
.\.venv\Scripts\python.exe simular.py
```

Para usar apenas `modelo.py`, a dependência externa é `pytz`. A implementação legada do SolTrack já acompanha o pacote em `vendor/soltrack`; não instalar outro `soltrack` pelo pip para executar este projeto.

Exemplo mínimo:

```python
from datetime import datetime, timezone
from modelo import Config, Weather, solar_position, decide

c = Config()  # Coordenadas e equipamento são exemplos; configurar sua planta.
t = datetime(2026, 3, 20, 13, tzinfo=timezone.utc)
s = solar_position(t, c)
w = Weather(t, dni=700, dhi=100, ghi=700*s.up + 100)
d = decide(t, current=0.0, w=w, c=c)
print(d)
```

`current` deve representar a posição efetivamente medida a cada ciclo. A decisão retorna uma referência e seu motivo. O pacote não escreve comandos em controladores e não contém um driver de motor.

## Arquivos de resultados

- `validacao.json`: 14 testes de requisitos e comparação de 358 posições com SPA, além do backtracking independente.
- `resultados_sinteticos.json`: configuração e resumo do experimento de um dia, três cenários e duas estratégias.
- `simulacao_sintetica.csv`: registro por minuto, com energia bruta e consumo de motor em Wh por intervalo.
- `ambiente_validacao.json` e `requirements-validacao.txt`: versões das bibliotecas usadas para verificação.

O cenário sintético claro apresentou variação líquida de −0,594%; o difuso, +7,866%; o variável, +0,340%, em relação à referência SolTrack com backtracking. São resultados de um exemplo determinístico, sem dados meteorológicos medidos. Não estimam produção anual, não provam ganho em campo e não demonstram superioridade universal. O relatório também registra o aumento do percurso angular no cenário variável.

O código mantém o núcleo astronômico original, aplica modelo isotrópico monofacial e assume terreno plano com fileiras uniformes. O cálculo de potência tem eficiência constante. Consumo do controlador, bifacialidade, temperatura de célula, topografia, sombra parcial elétrica, PID e integração industrial estão fora da implementação entregue.

## Origem e licenças

Origem: <https://github.com/MarcvdSluys/SolTrack>, commit `5f296faf20ffdfee331bf5297e4cf71fb181faf9`.

O diretório `vendor/soltrack` foi preservado sem modificações. Os cabeçalhos do código legado mencionam GPL e LGPL; os textos correspondentes foram incluídos. O código novo RAEL é disponibilizado sob GPL-3.0-or-later, cujo texto está em `COPYING`. O README original acompanha a cópia em `vendor/README_origem.md`.

Não confundir esse snapshot legado com a distribuição atual SolTrack-Python, que tem API e documentação de licença próprias.
