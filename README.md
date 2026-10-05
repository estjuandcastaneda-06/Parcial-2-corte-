# Enjambre de carritos hormiga para un sistema logístico de monedas colombianas (ESP32)

Proyecto de Micros (UMNG) · Integrantes: [nombres del grupo] · Octubre 2026

Este repositorio documenta **cómo está pensado y construido** el sistema: qué hace cada carrito, cómo se comunican, cómo funciona la
feromona, qué dibuja cada plano y cómo se relacionan los planos con el código. Al final hay una lista de qué se subió y qué estado tiene cada cosa.

---

## 1. El sistema en una página

**Núcleo (común a todos los grupos):** las monedas pasan por un contador (mide diámetro y peso), una banda las lleva, un brazo tapa cada vaso
de 10 monedas, y quedan vasos separados por denominación ($50, $100, $200, $500, $1.000).

**Diferencial de este grupo:** cinco carritos autónomos, uno por denominación, que se comportan como una **colonia de hormigas**. Cada carrito
sale de una posición distinta, busca los vasos de *su* denominación, los trae al **nido** (la meta) y deja un rastro de **feromona** que
ayuda a los demás. Para saber si agarró el vaso correcto lee su color con un sensor, y esa lectura se evalúa con una **matriz de confusión**.

```
 monedas ─► CONTADOR ─► BANDA ─► BRAZO (tapa) ─► vasos por denominación
            (ESP32 #0: estación central)                  │
                                                          ▼
            ┌──────────── ARENA 2100 × 1200 mm ───────────────────────────┐
            │  NIDO ◄── corredor con 3 obstáculos ◄── ZONA DE VASOS       │
            │   ▲        5 carritos (ESP32 c/u) exploran, leen el color,  │
            │   │        cargan el vaso y dejan feromona                  │
            └───┼─────────────────────────────────────────────────────────┘
                │ báscula del nido pesa el vaso ─► "era $200, no $50" (verificación)
                ▼
   ESP-NOW (canal 1): feromona + telemetría + verificación      Wi-Fi propio ─► PC: dashboard Streamlit + chatbot
```

## 2. Cómo se conecta todo

Hay tres tipos de dispositivo y dos radios:

| Dispositivo | Qué lleva | Habla con |
|---|---|---|
| **Estación central** (1 ESP32) | Contador (slider de diámetro, barrera IR, celda de carga con HX711), banda (L298N + motor DC 12 V), brazo (3 servos), **báscula del nido** (2.º HX711) | Los 5 carritos por ESP-NOW, y el PC por Wi-Fi |
| **Carrito** (5 ESP32) | Motores N20 con encoder, VL53L0X, TCS3200, MPU6050, pinza con 2 servos, LED, batería LiPo | Los otros carritos y la estación por ESP-NOW |
| **PC** | Streamlit (dashboard + chatbot) | La estación, leyendo `GET /data` |

- **ESP-NOW (canal 1, sin router):** es el radio entre ESP32. Los carritos mandan mensajes *broadcast* (a todos). Hay tres mensajes:
  **DEPÓSITO** (5 bytes: quién, en qué celda, cuánta feromona), **TELEMETRÍA** (15 bytes: estado, errores, entregas bien/mal) y
  **VERIFICACIÓN** (3 bytes: la estación le dice al carrito qué denominación pesó de verdad).
- **Wi-Fi:** la estación crea su propia red (AP «monedas», canal 1) y el PC lee `http://192.168.4.1/data`. Se usa el mismo canal 1 para que
  Wi-Fi y ESP-NOW convivan.
- Los cables de cada carrito (qué GPIO va a qué módulo) están en las láminas 5 y 5b; los de la estación y la red, en la lámina 6.

**Qué parte existe como código hoy:** el firmware del **carrito** y la simulación sí. El firmware de la **estación** (banda, brazo, báscula, mensaje de
verificación) **no está escrito todavía**; sus pines son solo diseño. Sin la estación, un carrito en hardware no recibe la verificación y asume
que cada entrega fue correcta tras esperar unos segundos, así que **la regla de errores no se activaría**.

## 3. Cómo funciona un carrito

Cada carrito corre el mismo programa (`carrito_hormiga.ino`) con otro `CARRITO_ID` (0 = $50, 1 = $100, 2 = $200, 3 = $500, 4 = $1.000).
Cada 100 ms decide qué hacer según su estado:

```
EXPLORAR ──(VL53L0X ve algo que no es pared ni carrito)──► ACERCAR ──(vaso a ≈45 mm)──► LEER COLOR
   ▲  │                                                                               │
   │  └─(errores ≥ 2)──► RETORNO ──► RECALIBRAR ──┐                  ¿es MI denominación?
   │                                               │                     sí │      │ no
   └───────────── ENTREGANDO ◄── TRANSPORTAR ◄─────┴─────────────────────────┘      └─► lo rechaza, lo "veta" 45 s y sigue
        (suelta, la báscula verifica)   (lleva el vaso al nido dejando feromona)
```

**Qué hace cada sensor:**

| Sensor | Para qué sirve | Detalle importante |
|---|---|---|
| **VL53L0X** (distancia, láser) | Detectar vasos hasta 250 mm y no chocar | Está en la placa superior a 105 mm del borde trasero para que con el vaso agarrado lea ≈45 mm (su mínimo fiable es ≈30 mm). Para no confundir un vaso con una pared, calcula dónde cayó el punto medido y lo compara con el mapa de obstáculos y con las posiciones de los otros carritos |
| **TCS3200** (color) | Saber la denominación del vaso | Va en la «palma» de la pinza, a ≈15 mm del vaso, porque solo funciona de cerca. Lee rojo/verde/azul y se convierte en *cromaticidad* r/(r+g+b), que casi no depende de cuánta luz haya |
| **Encoders Hall + MPU6050** | Saber dónde está (odometría) | Los encoders dan la distancia; el giroscopio da el rumbo. Sin esto no podría usar la feromona, porque no sabría en qué celda está |
| **Motores N20 + TB6612FNG** | Moverse | Un lazo PI de velocidad por rueda usando los encoders |
| **Servos SG90** | Abrir/cerrar la pinza | Ángulos `PINZA_ABIERTA/CERRADA` a calibrar |
| **ESP-NOW** | Compartir feromona | Ver sección 4 |
| **LED WS2812 + divisor de batería** | Ver el estado a simple vista / apagar si la batería baja de 6,4 V | Un color por estado |

**Cómo navega:** la arena tiene 3 obstáculos en zigzag con un hueco de 450 mm cada uno. Mientras no ha cruzado hacia la zona de vasos sigue un
**corredor dado** (una lista de puntos). Dentro de la zona de vasos (x ≥ 1700 mm) explora libre. En todo momento, un **campo de repulsión** lo aleja
de paredes y obstáculos.

## 4. Cómo funciona la feromona

La idea viene de las hormigas reales: no se hablan, **dejan huellas en el piso** y las demás las huelen (estigmergia).

- **El «mapa de olor»:** una grilla de 42 × 24 celdas de 50 mm (la arena entera). Cada celda guarda un número, su nivel de feromona
  (máximo 300). Cada carrito tiene **su propia copia** del mapa.
- **Cuándo deja feromona:** solo cuando va **cargando un vaso hacia el nido** (es decir, cuando encontró algo bueno). En cada paso suma a la celda
  donde está `26 · dt · 4 · (0,5 + 1,5 · lejos)`, donde `lejos` vale de 0 a 1 según qué tan lejos está del nido. El rastro queda **más fuerte
  del lado de los vasos** (hasta 2×) que del lado del nido, así que apunta hacia donde hubo comida. Al entregar, además, marca el nido con un refuerzo.
- **Cómo se comparte:** cada vez que el carrito cambia de celda manda un mensaje DEPÓSITO por ESP-NOW; los otros cuatro suman esa cantidad en su
  copia del mapa. Así los 5 mapas se mantienen casi iguales **sin un servidor central**.
- **Evaporación:** cada segundo todas las celdas pierden el 4,5 % (`valor × (1 − 0,045)`). Vida media ≈ 15 s; un rastro de 40 baja a 2 en ≈ 66 s.
  Esto evita que huellas viejas engañen al enjambre.
- **Cuándo la usa:** un carrito que explora en la zona de vasos y **no ve ningún vaso** mira las 8 celdas vecinas. Si la mejor tiene más de 2, se
  orienta hacia ella; si no, camina al azar (cada paso gira hasta ±40° respecto al anterior). Si ve un vaso, la feromona no importa.
- **Diferencia entre simulación y firmware:** la simulación además *difunde* un 2 % de la feromona a las celdas vecinas; el firmware no.

**Qué tanto ayuda (medido en simulación, 6 corridas de 30 min, mismas semillas):** con feromona 1056 vasos correctos, sin feromona 964: **≈ 10 % más**.
Es una ayuda real pero modesta, porque los vasos aparecen en lugares al azar y el sensor ya los detecta a 250 mm. No se probó en el robot real.

## 5. La matriz de confusión y la regla de errores

Idea del profe, aplicada así (**es nuestra interpretación; hay que confirmarla con él**):

- Cada vez que un carrito lee el color de un vaso, el sensor «predice» una denominación y la verdad es otra. La **matriz de confusión** cuenta los pares
  (denominación real, denominación predicha): la diagonal son aciertos y fuera de la diagonal están las confusiones.
- Si la lectura es dudosa (el mejor candidato no está claramente por delante del segundo), el carrito **relee y promedia** hasta 5 veces.
- Si acepta un vaso y en el nido la báscula descubre que era de otra denominación, eso es un **error confirmado** para ese carrito.
- Al llegar a **E_MAX = 2 errores**, el carrito deja de buscar, entrega lo que lleve **en el objetivo (el nido)**, recalibra el sensor con una tarjeta
  blanca y reinicia su contador.

**Qué mostró la simulación** (lámina 7): casi todo el error está en un solo par, **$50 plateado ↔ $200 beige** (sus colores son casi iguales para el
sensor). Con pegatinas blanco / amarillo / azul / rojo / verde la matriz queda diagonal y se entrega ≈ 33 % más. La regla de errores reduce a la mitad
las entregas equivocadas cuando el sensor se desvía mucho, pero cuesta ≈ 7 % de entregas correctas (los viajes a recalibrar); con poca desviación
casi no cambia nada. **El ruido del sensor es un supuesto**: hay que medirlo con el TCS3200 real.

## 6. Qué es cada archivo (y qué se sube)

**Se sube la carpeta `monedas_app/` completa.** Archivo por archivo:

### Raíz
| Archivo | Qué es |
|---|---|
| `README.md` | Este documento |
| `swarm.py` | **El cerebro en Python.** Simula el enjambre completo: grilla, feromona, 3 obstáculos, carritos con estados, sensor de color con ruido, matriz de confusión y regla de errores. El firmware es la misma lógica reescrita para el ESP32. Lo usan los experimentos, los planos (arena) y PyBullet |
| `experimentos_confusion.py` | Corre `swarm.py` muchas veces (paleta actual vs recomendada; con y sin la regla) y guarda los resultados en `planos/resultados_confusion.json` |
| `requirements.txt`, `.gitignore` | Librerías de Python; archivos que no deben subirse |

### `firmware/`
| Archivo | Qué es |
|---|---|
| `carrito_hormiga/carrito_hormiga.ino` | **Código del ESP32 de cada carrito.** Pines, motores con PI de velocidad, odometría (encoders + giroscopio), feromona por ESP-NOW, VL53L0X, TCS3200 y su calibración por monitor serie, pinza, máquina de estados, matriz de confusión y regla de errores. **Compila; no probado en hardware** |
| `esp32_monedas/esp32_monedas.ino` | Firmware viejo del contador de monedas (clasifica por diámetro y peso y sirve `/data` por Wi-Fi). No incluye banda ni brazo |

### `planos/` — qué dibuja cada lámina y de qué depende
| Lámina | Qué muestra | Para qué sirve |
|---|---|---|
| `01_vistas_carrito` | Planta, lateral y frontal a escala con cotas, sensores, centro de gravedad | Fabricar el chasis; verificar que los sensores quedan donde deben |
| `02_distribucion_interna` | Piso inferior, pinza y piso superior con cada componente numerado | Saber dónde va cada pieza dentro del carrito |
| `03_pesos_consumo` | Peso por pieza (290 g vacío, 401 g con vaso), potencia (≈3,2 W), autonomía (≈1,5 h teórica), estabilidad | Escoger batería, buck y fusible; comprobar que no vuelca |
| `04_arena` | Arena de 2100 × 1200 mm: obstáculos, corredor, nido, salidas, zona de vasos | Construir el escenario; sus coordenadas son las del código |
| `05_esquema_carrito` | Cada GPIO del ESP32 cableado a su módulo + alimentación | Armar y soldar el carrito |
| `05b_tabla_conexiones` | La misma información como tabla (GPIO, módulo, pin, nota) y de dónde sale cada riel | Cablear sin equivocarse |
| `06_esquema_sistema` | Estación central + red ESP-NOW + PC | Visión global y diseño de la estación |
| `07_matriz_confusion` | Matrices con dos paletas de pegatinas y la regla de errores | Justificar qué colores usar en los vasos |
| `planos_completos.pdf` | Las 8 láminas en un solo PDF | Imprimir / entregar |
| `datos_carrito.py` | **Fuente única de datos:** medidas, peso y posición de cada pieza, consumos y la tabla de pines | Todo lo demás sale de aquí |
| `generar_todo.py`, `lamina*.py`, `estilo.py` | Scripts que dibujan las láminas | Regenerarlas al cambiar datos |
| `verificar_pines.py` | Compara los pines del firmware con la tabla de los planos | Detectar si cambias un pin en un lado y no en el otro |
| `resultados_confusion.json` | Resultados de los experimentos | Alimenta la lámina 7 |

### `pybullet_sim/`
| Archivo | Qué es |
|---|---|
| `carrito.urdf` | Modelo del carrito (chasis, 2 ruedas, rueda loca, sensores, pinza de 2 dedos); masa 0,286 kg como en los planos |
| `swarm_pybullet.py` | Carga 5 carritos y los 3 obstáculos en PyBullet; `swarm.py` decide y este script mueve los cuerpos con velocidad diferencial. **No se pudo correr** |

### Dashboard del núcleo (trabajo anterior)
`app.py`, `interfaz.html`, `simulador.py`, `mock_esp32.py`, `esp32_client.py`, `coins.py`, `aco.py`, `.streamlit/config.toml`: tablero de monedas/banda
con datos simulados o del ESP32. `coins.py` tiene las medidas reales de las monedas colombianas (serie nueva y antigua). **Aún muestran el dron, no el enjambre.**

## 7. Cómo se relacionan los planos con el código

| Si cambias… | Se actualiza / debe coincidir… |
|---|---|
| `datos_carrito.py` (pesos, medidas, posiciones, consumos) | Láminas 1, 2, 3 al correr `generar_todo.py` |
| `datos_carrito.py` (tabla `PINES`) | Láminas 5 y 5b; y **a mano** los `PIN_*` del `.ino` (`verificar_pines.py` avisa si no coinciden) |
| Obstáculos, corredor, nido o salidas | `swarm.py` (`OBSTACULOS`, `CORREDOR`, `NIDO`) → lámina 4 se redibuja sola; **a mano** `OBST`, `CORR`, `SALIDA` del `.ino` |
| Medidas del vaso o la pinza | `DIST_LISTO_MM` y `OFFSET_PINZA_MM` del firmware, `OFFSET_PINZA` de `swarm.py`, y `carrito.urdf` |
| Colores de las pegatinas | `COLOR` / `PALETA_RECOMENDADA` en `swarm.py`; en el robot, recalibrar con los comandos `0`–`4` |

Cómo influyen los planos en las decisiones: el **peso y el centro de gravedad** (lámina 3) se usan para comprobar que el carrito no vuelca con el
vaso más pesado; el **consumo** define batería de 850 mAh, buck de 3 A y fusible de 3 A; la **posición de los sensores** (lámina 1) fija las distancias del
firmware (VL53L0X a 45 mm del vaso, TCS3200 a 15 mm); y la **arena** (lámina 4) fija las coordenadas que usan la simulación, el firmware y PyBullet.

## 8. Cómo probar (resumen)

```
python -m pip install -r requirements.txt
python -c "from swarm import Enjambre; e=Enjambre(1); [e.step(0.2) for _ in range(9000)]; s=e.estado(); print('ok',s['entregados_ok'],'mal',s['entregados_err']); print(s['confusion']['matriz'])"
cd planos && python generar_todo.py && python verificar_pines.py
```
La simulación da ≈ `ok 176 mal 3` con una matriz que confunde $50 y $200; con `swarm.usar_paleta(swarm.PALETA_RECOMENDADA)` da `mal 0`.

**Firmware (Arduino IDE, placa *ESP32 Dev Module*, librerías Adafruit VL53L0X, Adafruit NeoPixel, ESP32Servo):** cambia `CARRITO_ID`, sube y abre el monitor a 115200.
Prueba con el carrito **levantado** y en este orden: `t` (VL53L0X y TCS3200), `w` y `0`…`4` (calibrar color con tarjeta blanca y cada pegatina) y `p` (imprime la tabla `CENT` para pegar en el código),
`m` (motores y encoders: las cuentas deben salir positivas; si no, invierte `SIGNO_ENC_*`), `d` (estado, rumbo y matriz de confusión local). Las constantes `[CALIBRAR]` hay que medirlas en el carrito real.

**PyBullet (en el computador del curso):** `pip install pybullet` y `python pybullet_sim/swarm_pybullet.py`.

