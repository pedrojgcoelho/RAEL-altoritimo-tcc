# Modelo astronômico de rastreamento solar orientado à energia líquida

Proposta técnica para o TCC de Pedro José Guimarães Coelho

## 1 Proposta e contribuição

Propõe-se o **Rastreamento Astronômico por Energia Líquida — RAEL**, um modelo computacional para trackers fotovoltaicos monofaciais de eixo horizontal norte–sul. O algoritmo utiliza o SolTrack para calcular a posição solar e acrescenta uma política de posicionamento que considera irradiância direta, difusa e refletida, restrições de sombreamento entre fileiras, energia dos atuadores e intervalo entre movimentos.

A pergunta central passa a ser: **qual movimento oferece o maior benefício energético previsto, depois de descontado seu custo de execução?** A posição do Sol continua sendo calculada por um método astronômico conhecido. A contribuição proposta para o TCC é a formulação e implementação reproduzível da política de decisão que usa esse cálculo.

O RAEL é um novo modelo proposto neste trabalho, baseado em técnicas existentes. Não constitui uma nova teoria de efemérides nem demonstra ineditismo científico internacional. A literatura anexada já apresenta otimização por irradiância, backtracking, controle híbrido e análise de movimentos. Uma alegação de novidade científica exigiria revisão sistemática direcionada e comparação com essas estratégias. O ganho energético é hipótese experimental, não propriedade garantida do algoritmo.

O pacote inclui código executável, testes, comparação independente de geometria, simulação sintética e rastreabilidade dos 32 PDFs fornecidos. O TCC original foi mantido intacto.

## 2 Relação com o texto e com a pesquisa

O texto atual do TCC compara estratégias sob a perspectiva da Engenharia de Software e declara não possuir implementação ou simulação própria. O RAEL oferece uma extensão prática dessa pesquisa. Sua inclusão exige alterar metodologia e limitações para distinguir a revisão bibliográfica, a proposta de software e os ensaios numéricos.

As bases mais diretamente relacionadas à proposta são:

| Fonte fornecida | Relação com a proposta | Distinção necessária |
|---|---|---|
| Muñoz et al., Solar RRL, 2024, 2300507, páginas PDF 1, 3 e 13–14 | Comparação entre rastreamento astronômico, otimização de irradiância e esforço de movimento | Otimizar irradiância e contar movimentos já são abordagens publicadas |
| Osman et al., 2022, artigo 7715214, página PDF 1 | Medição de energia gerada e consumo de controle e atuação | Seus percentuais experimentais não são parâmetros universais do RAEL |
| Santos de Araújo et al., 2024, Sensors 3890, páginas PDF 6–7 e 20 | Separação entre cálculo de ângulo e aplicação por infraestrutura NCU/TCU | O protótipo entregue não implementa Modbus nem a estratégia de IA desse artigo |
| Keiner et al., Solar Energy 267, 112228, página PDF 1 | Dependência do backtracking em relação à tecnologia e à geometria da planta | Evitar qualquer sombra é uma opção conservadora, não uma prova de máxima geração |
| Chowdhury et al., 2019, artigo 3681031, páginas PDF 1 e 8–9 | Cálculo solar associado a controle com realimentação física | Cálculo astronômico não substitui medição da posição mecânica |
| Sadeghi et al., Energies 18, 2553, seções 4 e 5 | Contextualização de controle híbrido, difusa e backtracking | A revisão organiza resultados heterogêneos; não fornece um ensaio comum de todos os algoritmos |

Os demais anexos contribuem para contextualização ou delimitação, conforme `Fontes_e_rastreabilidade.md`. Os dois documentos sobre transporte não foram usados como evidência de controle solar. A revisão sobre MPPT é relacionada à extração elétrica de potência e não equivale ao controle de orientação mecânica.

## 3 Escopo físico e convenções

O protótipo adota fileiras paralelas, idênticas, coplanares, com mesma orientação angular e espaçamento uniforme, em terreno plano. Os módulos são monofaciais. Não modela bifacialidade, topografia, obstáculos externos ou strings parcialmente sombreadas. Sua aplicação principal é simulação comparativa de software.

Entradas principais:

| Grandeza | Símbolo | Unidade ou convenção |
|---|---|---|
| Data e hora | t | datetime com fuso explícito, convertido para UTC |
| Latitude e longitude | φ, λ | graus; norte e leste positivos |
| Pressão e temperatura do ar | p, T | kPa e kelvin na interface legada do SolTrack |
| Azimute solar | A | 0° norte, 90° leste, 180° sul, 270° oeste |
| Elevação solar | h | graus acima do horizonte |
| Ângulo da normal do módulo | θ | 0° vertical; positivo voltado para leste |
| Irradiância direta normal | DNI | W/m² |
| Irradiância difusa e global horizontais | DHI, GHI | W/m² |
| Cobertura do terreno | GCR | largura de fileira dividida pelo passo entre fileiras |
| Posição mecânica | θₖ | graus, preferencialmente medidos por inclinômetro |

A inclinação física da superfície em relação à horizontal é β = |θ|. Um tracker de eixo único não consegue manter sua normal alinhada ao vetor solar em três dimensões durante todo o dia. A otimização geométrica restringe a normal ao plano perpendicular ao eixo norte–sul.

## 4 Núcleo astronômico

Foi utilizado o repositório exato indicado no pedido:

<https://github.com/MarcvdSluys/SolTrack>

Commit fixado: `5f296faf20ffdfee331bf5297e4cf71fb181faf9`.

O protótipo usa a implementação Python legada contida em `Python/soltrack` desse commit, copiada sem alterações para `vendor/soltrack`. Não usa a API atual de outro pacote homônimo instalado pelo pip. Assim, mudanças futuras do pacote SolTrack não alteram silenciosamente os ensaios entregues.

A sequência original do SolTrack calcula o dia juliano, a longitude solar e a obliquidade, converte coordenadas eclípticas em equatoriais e depois em horizontais, com correções de paralaxe e refração. Esses cálculos e seus coeficientes são de autoria dos desenvolvedores do SolTrack e foram preservados.

Para controle, usa-se a elevação corrigida por refração apenas no domínio diurno adotado. Abaixo de 3° de elevação geométrica, o protótipo usa a elevação sem refração para decidir o estacionamento. Isso evita interpretar a aproximação de refração noturna como uma observação física válida. Não se reivindica precisão operacional junto ao horizonte.

O código legado recebe tempo UT; o adaptador utiliza UTC como aproximação operacional. Uma avaliação metrológica precisa explicitar UT1, TT, ΔT e incerteza do relógio. A comparação com SPA realizada aqui não estabelece precisão global do SolTrack, nem precisão do mecanismo real.

## 5 Transformação vetorial

No sistema local leste–norte–cima:

\[
\mathbf{s}(t)=\begin{bmatrix}\cos h\sin A\\\cos h\cos A\\\sin h\end{bmatrix},\qquad
\mathbf{n}(\theta)=\begin{bmatrix}\sin\theta\\0\\\cos\theta\end{bmatrix}.
\]

O cosseno útil do ângulo de incidência é:

\[
\mu(t,\theta)=\max(0,\mathbf{s}(t)\cdot\mathbf{n}(\theta)).
\]

A referência geométrica para eixo horizontal norte–sul é:

\[
\theta_{TT}(t)=\operatorname{atan2}(s_E(t),s_U(t)).
\]

Todos os argumentos de funções trigonométricas são convertidos para radianos. A API do protótipo fornece e recebe ângulos em graus. A adoção de `atan2` preserva os quadrantes e evita confundir azimute solar com ângulo mecânico.

## 6 Backtracking e conjunto de posições permitidas

Para terreno plano e fileiras uniformes, a referência convencional é:

\[
r(t)=\frac{|\cos\theta_{TT}(t)|}{GCR},\qquad
\theta_{BT}(t)=\theta_{TT}(t)-\operatorname{sgn}(\theta_{TT}(t))\arccos(\min(1,r(t))).
\]

Aplica-se depois o limite mecânico. Quando r ≥ 1, a correção é nula. O protótipo também testa diretamente uma restrição geométrica de não sobreposição das projeções de fileiras sobre o plano normal ao feixe:

\[
GCR\,|\cos(\theta-\theta_{TT})|\leq\cos\theta_{TT}.
\]

A expressão vale no domínio diurno e nas hipóteses de fileiras coplanares e uniformes adotadas. Ela não calcula a perda elétrica de sombreamento. A restrição é verificada no instante atual e nas amostras do horizonte, tanto para o destino como para a trajetória estimada de movimento.

As verificações são discretas. Não certificam ausência contínua de sombra entre amostras. Na integração real, fileiras vizinhas que se movem em instantes diferentes exigem modelo conjunto das suas posições; a hipótese de todas as fileiras com o mesmo ângulo deixa de valer durante esse deslocamento.

Ao contrário de permitir sombra e otimizar seus efeitos elétricos, esta primeira versão a impede no modelo geométrico. Isso reduz a complexidade da comparação, mas pode excluir soluções energeticamente superiores em tecnologias específicas, como alerta a pesquisa de Keiner et al.

## 7 Modelo de irradiância e potência

Adota-se uma aproximação isotrópica, monofacial:

\[
G_{POA}(t,\theta)=DNI(t)\mu(t,\theta)
+DHI(t)\frac{1+\cos\beta}{2}
+\rho_gGHI(t)\frac{1-\cos\beta}{2}.
\]

\[
\widehat P(t,\theta)=A_m\eta\,G_{POA}(t,\theta).
\]

Aqui, Aₘ é a área ativa dos módulos, η é uma eficiência constante e ρg é o albedo. Cada parcela de GPOA tem unidade W/m²; a potência resultante tem unidade W. As componentes difusa e refletida usam fatores de vista de uma superfície isolada: obstrução do céu por fileiras vizinhas e reflexão múltipla não são representadas.

O objetivo desta versão é comparar a lógica de decisão sob hipóteses transparentes. Não é um modelo completo de produção DC ou AC. Temperatura de célula, IAM, resposta espectral, perdas elétricas, diodos bypass, clipping e inversores precisam ser acrescentados antes de prever produção real. A revisão de MPPT anexada não fornece esses efeitos automaticamente ao modelo.

Na ausência de previsão meteorológica, os valores válidos mais recentes de DNI, DHI e GHI são mantidos durante o horizonte. Trata-se de previsão por persistência; não há informação futura de nuvens nem aprendizado de máquina. As três componentes mantidas podem deixar de satisfazer exatamente o fechamento radiométrico conforme a elevação muda. Para horizontes maiores, recomenda-se prever duas componentes e reconstruir a terceira consistentemente.

## 8 Função de decisão por energia líquida

Para cada destino candidato q, modela-se uma trajetória com velocidade angular limitada v:

\[
\theta_q(\tau)=\theta_k+\operatorname{sgn}(q-\theta_k)\min(|q-\theta_k|,v\tau).
\]

O horizonte H é dividido em M intervalos de duração Δt. A energia gerada é integrada nos pontos médios:

\[
\widehat E_{PV}(q)=\frac{\Delta t}{3600}\sum_{j=0}^{M-1}
\widehat P(t_k+(j+1/2)\Delta t,\theta_q((j+1/2)\Delta t)).
\]

O modelo ilustrativo de consumo de atuação é:

\[
\widehat E_{motor}(q)=\begin{cases}
0,&q=\theta_k,\\
E_0+c_\theta|q-\theta_k|,&q\ne\theta_k.
\end{cases}
\]

E₀ representa o custo de partida em Wh e cθ representa o consumo por grau em Wh/°. Eles devem ser identificados por ensaio de tensão e corrente do atuador real, incluindo carga, orientação e sentido. O custo independe do sentido apenas nesta aproximação.

A pontuação é:

\[
J(q)=\widehat E_{PV}(q)-\widehat E_{motor}(q)-\lambda_w|q-\theta_k|.
\]

O termo λw é uma penalidade equivalente por deslocamento, em Wh/°, e não consumo elétrico medido. Seu valor padrão é zero. Sua utilização exige justificar o compromisso entre produção e esforço mecânico; a energia líquida relatada não desconta artificialmente esse termo como se fosse energia consumida.

Seleciona-se:

\[
q^*=\arg\max_{q\in\mathcal F_k}J(q),\qquad
\Delta J=J(q^*)-\widehat E_{PV}(\theta_k).
\]

O conjunto Fₖ contém os candidatos dentro dos limites mecânicos que passam pelos testes geométricos discretos. São avaliados uma grade angular, a referência de backtracking, a posição atual e a posição horizontal. A posição atual só é candidata admissível se cumprir as mesmas restrições.

Se manter a posição continuar viável, o movimento ocorre quando ΔJ superar uma margem εE, o deslocamento superar uma banda εθ e houver transcorrido o intervalo mínimo entre movimentos. Se manter a posição violar as restrições geométricas amostradas, um movimento de correção tem prioridade sobre essa economia de atuação. Quando não há trajetória viável, retorna-se um estado de falha para tratamento pelo controlador local.

Esta é uma otimização de **um único destino mantido no horizonte**, recalculada a cada ciclo. Não é uma otimização global do dia nem um MPC com sequência completa de comandos futuros. A avaliação é O(MK), para M amostras e K candidatos; a grade pode ser refinada ou reduzida conforme os recursos do controlador.

## 9 Estados e qualidade dos dados

| Estado | Comportamento do protótipo |
|---|---|
| ENERGY_MOVE | Seleciona um movimento cujo benefício previsto supera os critérios definidos |
| HOLD | Mantém a referência por benefício insuficiente, banda angular ou intervalo mínimo |
| GEOMETRY_MOVE | Corrige uma posição cuja manutenção se torna geometricamente inviável nas amostras |
| ASTRO_FALLBACK | Retorna ao SolTrack com backtracking quando a meteorologia não é utilizável |
| NIGHT | Solicita estacionamento horizontal abaixo da elevação mínima |
| STOW | Solicita a referência ilustrativa de proteção, com prioridade sobre geração |
| FAULT_HOLD | Não solicita novo movimento diante de falha de comunicação ou ausência de trajetória viável |

A validação meteorológica rejeita NaN, infinito, irradiância negativa, registro futuro ou vencido e inconsistência excessiva no fechamento GHI ≈ DNI·sin(h) + DHI. Os limites de tolerância são escolhas de engenharia para o protótipo: 180 s de idade máxima e discrepância máxima igual ao maior valor entre 50 W/m² e 15% de GHI. Devem ser ajustados à instrumentação.

Os retornos são referências de pesquisa. NIGHT e STOW usam 0° apenas para demonstração; o ângulo de proteção real depende do fabricante e da análise estrutural. Em uma falha de comunicação, o controlador remoto não consegue garantir fisicamente a parada do motor. Watchdog, frenagem, fins de curso e intertravamentos pertencem ao controle local e não estão implementados aqui.

O modo de fallback não aplica a otimização energética nem o intervalo mínimo do RAEL; serve como retorno geométrico. O algoritmo usa a posição atual informada pela aplicação e não contém controlador PID ou simulador de erro de inclinômetro.

## 10 Pseudocódigo

```text
receber instante com fuso, posição medida, meteorologia e estado operacional
validar configuração, instante e posição
se comunicação indisponível: retornar FAULT_HOLD
se proteção solicitada: retornar STOW
calcular posição solar com SolTrack
se elevação insuficiente: retornar NIGHT
se meteorologia inválida: retornar referência astronômica com backtracking
calcular vetores solares futuros nos pontos médios do horizonte
gerar destinos candidatos e modelar o deslocamento até cada destino
rejeitar destinos e trajetórias que violam as restrições amostradas
calcular energia prevista, custo de atuação e penalidade de deslocamento
selecionar o candidato de maior pontuação
se manter a posição for inviável: retornar GEOMETRY_MOVE
se benefício, banda ou intervalo não autorizarem movimento: retornar HOLD
retornar ENERGY_MOVE
registrar referência, motivo, entradas e previsões
repetir no próximo ciclo usando a posição efetivamente medida
```

## 11 Parâmetros entregues

| Parâmetro | Valor inicial | Natureza |
|---|---:|---|
| Latitude e longitude | −21,76°; −43,35° | Exemplo aproximado de Juiz de Fora, não levantamento da planta |
| Limites | ±60° | Hipótese de simulação |
| GCR | 0,35 | Hipótese geométrica |
| Área e eficiência | 2 m²; 20% | Módulo representativo, não equipamento identificado |
| Horizonte e passo | 600 s; 60 s | Escolha de projeto |
| Grade | 1° | Escolha de projeto |
| Velocidade | 1°/s | Hipótese de atuação |
| Partida e deslocamento | 0,02 Wh; 0,002 Wh/° | Custos sintéticos, sem identificação experimental |
| Margem e banda | 0,02 Wh; 0,5° | Escolhas de projeto |
| Intervalo mínimo | 120 s | Escolha de projeto |
| Albedo | 0,20 | Hipótese ambiental |

Os valores não foram ajustados para maximizar os resultados abaixo. São suficientes para reproduzir o exemplo e devem ser submetidos a análise de sensibilidade antes de qualquer conclusão sobre desempenho local.

## 12 Verificação executada

Foram executados **14 testes automatizados de requisitos**, abrangendo fuso horário, entradas inválidas, condições meteorológicas, fallback, limites, geometria, consumo de atuação, velocidade, estacionamento, falha de comunicação, intervalo mínimo e resposta ao cenário puramente difuso.

A posição solar foi comparada com `pvlib.solarposition.spa_python`, versão pvlib **0.16.1**, em quatro localidades: exemplo de Juiz de Fora, Fortaleza, Arnhem e equador em Greenwich. Utilizaram-se quatro datas sazonais de 2026, com passo de 30 minutos; **358 instantes** apresentaram elevação solar de pelo menos 5° e foram considerados. Pressão e temperatura foram compatibilizadas em 101 kPa e 283 K, com altitude da estação de referência igual a 0 m.

| Indicador | Resultado |
|---|---:|
| Separação angular vetorial média entre SolTrack e SPA | 0,003124° |
| Separação angular vetorial máxima na amostra | 0,005909° |
| Diferença máxima de backtracking frente à pvlib com o mesmo vetor solar | 1,42 × 10⁻¹³° |

O erro foi medido por separação entre vetores unitários, evitando interpretar a diferença de azimute perto do zênite como erro espacial equivalente. O backtracking usa `axis_azimuth=0`, compatível com a convenção positiva para leste desta implementação.

Também foi verificado o exemplo numérico publicado no repositório SolTrack para Arnhem, em 16/07/2045 às 06:02:49,217348 UTC. A tolerância de 0,001° reconhece que o exemplo publicado é da versão C e o protótipo usa a porta Python legada.

Essas verificações estabelecem consistência numérica na amostra e cumprimento de requisitos do protótipo. Não substituem validação astronômica em todo o domínio temporal/geográfico, prova contínua de restrições ou ensaio em campo.

## 13 Simulação sintética reproduzível

Executou-se um dia UTC completo, em 20/03/2026, com avaliação de comando a cada minuto e integração da potência em seis pontos médios por minuto. Cada ciclo incorpora a trajetória limitada por velocidade. Os cenários claro, difuso e variável são funções determinísticas criadas para o ensaio; não são medições climáticas.

A referência comparativa utiliza o mesmo SolTrack, geometria, modelo de potência e custo de motor, com backtracking convencional e banda de 0,5°. O RAEL adiciona o horizonte de 10 minutos, a otimização energética e o intervalo mínimo de 120 s. A comparação verifica o efeito do conjunto dessas regras, não isola a contribuição individual de cada uma.

| Cenário sintético | Energia líquida da referência | Energia líquida RAEL | Variação | Movimentos referência / RAEL |
|---|---:|---:|---:|---:|
| Claro | 3357,11 Wh | 3337,16 Wh | −0,594% | 335 / 138 |
| Difuso | 1328,95 Wh | 1433,49 Wh | +7,866% | 335 / 0 |
| Variável | 2308,30 Wh | 2316,15 Wh | +0,340% | 335 / 125 |

No cenário claro, a menor energia bruta capturada supera a economia de atuação e resulta em perda líquida. O algoritmo não domina o rastreamento convencional em todas as condições. No difuso, permanecer horizontal favorece o modelo isotrópico adotado e dispensa movimentos nesse dia específico. No variável, a persistência meteorológica produz pequena melhora líquida.

O cenário variável também mostra um compromisso relevante: o deslocamento acumulado do RAEL foi **1532,31°**, frente a **239,85°** da referência, apesar de apresentar menos partidas. Portanto, menos movimentos não significa menor percurso ou desgaste. A penalidade de deslocamento está desabilitada por padrão e sua ativação requer análise de sensibilidade.

A energia líquida calculada é Eₚᵥ − Eₘₒₜₒᵣ. O consumo de eletrônica e comunicação não foi modelado: assume-se igual entre as estratégias apenas para esta comparação. Se o RAEL exigir hardware adicional ou maior processamento, seu consumo precisa ser incluído. A simulação não aplica perda elétrica por sombra residual durante a retenção ou entre amostras, o que também limita a interpretação dos totais.

Os valores são resultados internos de um cenário didático. Não representam ganho anual esperado, não comprovam ganho de uma usina real e não podem ser comparados diretamente com os percentuais experimentais de outros artigos.

## 14 Arquitetura de software proposta

```text
Relógio e configuração da planta
             |
             v
      SolTrack preservado ----> Vetores solares e backtracking
                                       |
Meteorologia --> Qualidade dos dados ---+--> Avaliador RAEL
Posição medida ------------------------+         |
Proteções locais --------------------------------+--> Supervisor de estados
                                                          |
                                                Referência e justificativa
                                                          |
                                         Adaptador de equipamento a desenvolver
                                                          |
                                               TCU e controle local do motor
```

O código entregue implementa os cálculos até a referência e justificativa. A integração com equipamento real deve definir mapa de registradores, unidade e sinal dos ângulos, limites, confirmação de recebimento, validade temporal do comando e comportamento perante perda de rede. Esses detalhes variam conforme o fabricante; não se inventou um mapa Modbus genérico.

Na aplicação local, recomenda-se registrar instante UTC, vetor solar, ângulo medido, referência enviada, modo, idade e validade dos sensores, energia prevista, corrente/tensão do motor, confirmação do comando e falhas. Isso permite verificar posteriormente se uma perda veio do modelo, dos dados ou da execução mecânica.

## 15 Protocolo para validação científica

1. Levantar geometria, orientação e limites reais; identificar resolução, velocidade, folga e consumo do atuador com medições independentes.
2. Obter séries locais de DNI, DHI, GHI e temperatura, com qualidade e resolução temporal compatíveis. Evitar vazamento de dados futuros: o controlador só deve receber o que estaria disponível naquele instante.
3. Comparar fixo, SolTrack com true tracking, SolTrack com backtracking, SPA com o mesmo backtracking, otimização instantânea sem custo e RAEL. Usar os mesmos módulos, clima e modelos de potência em todas as alternativas.
4. Separar os experimentos: para comparar efemérides, manter a política de controle; para comparar políticas, manter as efemérides. Assim, diferenças de geração não são atribuídas indevidamente ao núcleo astronômico.
5. Fazer ablações de horizonte, custos de partida/deslocamento, intervalo mínimo, restrições geométricas e penalidade de percurso. Comparar persistência com previsões causais e com uma referência ideal de conhecimento futuro, identificada apenas como limite superior.
6. Avaliar energia bruta e líquida, consumo auxiliar completo, partidas, percurso angular, inversões de sentido, erro de posição, tempo de CPU, memória, falhas e número de fallback. Estimar incertezas e intervalos de confiança por blocos de dias, respeitando autocorrelação temporal.
7. Usar período separado para calibração e avaliação; cobrir diferentes estações. Em campo, alternar estratégias ou utilizar grupos equivalentes, verificando diferenças entre fileiras, sujeira e disponibilidade.

Uma afirmação defensável de melhoria depende de ganho líquido consistente no período de avaliação, superior à incerteza de medição e sem piorar requisitos operacionais. Também é cientificamente útil concluir que o modelo economiza partidas, mas não melhora energia em determinada região ou configuração.

## 16 Texto sugerido para inclusão no TCC

> Como extensão à análise bibliográfica, propôs-se o modelo de Rastreamento Astronômico por Energia Líquida, denominado RAEL. A solução utiliza o SolTrack como núcleo de cálculo da posição solar e acrescenta uma política de decisão para trackers monofaciais de eixo horizontal norte–sul. O modelo avalia destinos angulares em horizonte finito, estima a energia fotovoltaica por uma aproximação isotrópica de irradiância e desconta o consumo previsto de atuação. A decisão respeita limites mecânicos e restrições discretas de sombreamento entre fileiras, além de aplicar banda angular e intervalo mínimo entre movimentos quando a posição atual permanece viável. A contribuição concentra-se na implementação e na avaliação da política de controle, preservando a autoria do núcleo astronômico utilizado.
>
> A implementação foi submetida a testes de requisitos e a comparação numérica com o SPA disponível na pvlib. Adicionalmente, realizaram-se simulações com condições meteorológicas sintéticas, cujos resultados não constituem evidência de desempenho anual ou em campo. Os ensaios indicaram que a redução de partidas pode coexistir com perda energética ou aumento do deslocamento acumulado, reforçando a necessidade de avaliar geração, consumo auxiliar e esforço mecânico de forma conjunta.

Sugestão de objetivo específico adicional: **“Desenvolver e verificar um protótipo de rastreamento baseado no SolTrack que decida o posicionamento pela energia líquida prevista, comparando-o com backtracking convencional em cenários controlados.”**

A metodologia deve passar a descrever pesquisa bibliográfica acompanhada de desenvolvimento de protótipo e experimento numérico exploratório. A limitação “não implementou simulação própria” precisa ser atualizada se estes resultados forem incorporados. Não descrever a simulação sintética como validação experimental em planta.

## 17 Referências centrais e atribuição

- VAN DER SLUYS, M.; VAN KAN, P. SolTrack: a free, fast and accurate routine to compute the position of the Sun. 2022. <https://arxiv.org/abs/2209.01557>.
- SOLTRACK. Código-fonte do repositório indicado, commit `5f296faf20ffdfee331bf5297e4cf71fb181faf9`. <https://github.com/MarcvdSluys/SolTrack/tree/5f296faf20ffdfee331bf5297e4cf71fb181faf9>.
- MUÑOZ, I. et al. Evaluation of Horizontal Single-Axis Solar Tracker Algorithms in Terms of Energy Production and Operational Performance. Solar RRL, 8, 2300507, 2024. <https://doi.org/10.1002/solr.202300507>.
- OSMAN, I. S. et al. Experimental Investigation and Comparison of the Net Energy Yield Using Control-Based Solar Tracking Systems. International Journal of Photoenergy, 2022, 7715214. <https://doi.org/10.1155/2022/7715214>.
- SANTOS DE ARAÚJO, J. V. et al. Solar Tracking Control Algorithm Based on Artificial Intelligence Applied to Large-Scale Bifacial Photovoltaic Power Plants. Sensors, 24, 3890, 2024. <https://doi.org/10.3390/s24123890>.
- KEINER, D. et al. Impact of backtracking strategies on techno-economics of horizontal single-axis tracking solar photovoltaic power plants. Solar Energy, 267, 112228, 2024. Documento fornecido `1-s2.0-S0038092X23008629-main.pdf`.
- CHOWDHURY, M. E. H. et al. A Low-Cost Closed-Loop Solar Tracking System Based on the Sun Position Algorithm. Journal of Sensors, 2019, 3681031. <https://doi.org/10.1155/2019/3681031>.
- SADEGHI, R. et al. A Review and Comparative Analysis of Solar Tracking Systems. Energies, 18, 2553, 2025. <https://doi.org/10.3390/en18102553>.
- PVLIB. Documentação da implementação SPA e de singleaxis. <https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.solarposition.spa_python.html>; <https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.tracking.singleaxis.html>. Versão executada: 0.16.1.

O SolTrack legado possui avisos GPL e LGPL em diferentes arquivos. Foram preservados os arquivos originais, seus cabeçalhos e os textos das duas licenças. O código novo deste protótipo é disponibilizado sob GPL-3.0-or-later. Esta cópia não deve ser confundida com a versão Python mais recente, cuja documentação menciona outra licença. As atribuições e os textos de licença acompanham o pacote.
