# Sistema logístico de monedas colombianas — enjambre de 5 carritos hormiga (ESP32)

Proyecto de Micros (UMNG). **Núcleo común:** contador de monedas → banda → embalaje en vasos por denominación.
**Diferencial del grupo:** 5 carritos autónomos que actúan como una colonia de hormigas (ACO estigmérgico). Cada carrito busca
los vasos de **una** denominación ($50, $100, $200, $500 o $1.000), los lleva al nido dejando feromona, y su sensor de color se evalúa con una
**matriz de confusión**: al acumular errores el carrito vuelve al nido (el objetivo) a dejar lo que lleve y a recalibrar el sensor.

> Integrantes: [nombres del grupo] · Materia: Microcontroladores / Mecatrónica · Fecha: octubre 2026

---

## 1. Qué hay que subir (según lo que pidió el profe)

| Lo que pidió el profe | Dónde está | Estado |
|---|---|---|
| Diagramas circuitales del carrito (cómo va todo a los pines) | `planos/05_esquema_carrito` + `planos/05b_tabla_conexiones` | Hecho |
| Diagramas circuitales de todo el proyecto | `planos/06_esquema_sistema` | Hecho (la estación central es solo diseño) |
| Código del ESP32 con feromona y sensores | `firmware/carrito_hormiga/carrito_hormiga.ino` | **Compila**; no probado en hardware |
| Plano del espacio donde se mueven los carritos | `planos/04_arena` | Hecho |
| Planos del carrito: medidas, sensores acoplados, organización interna | `planos/01_vistas_carrito`, `planos/02_distribucion_interna` | Hecho |
| Peso y potencia (carrito + sensores) | `planos/03_pesos_consumo` | Hecho (estimado, falta pesar piezas reales) |
| Matriz de confusión aplicada a las hormigas | `swarm.py` + `planos/07_matriz_confusion` + `experimentos_confusion.py` | Hecho en simulación |
| Simulación en PyBullet | `pybullet_sim/` | URDF validado; **sin correr** |
| Presentación | https://claude.ai/artifact/ESERMjTicbdoh4pJRDs1cV (privada: descárgala desde ahí como PDF/PPT y súbela también) | Hecho |

**Sube la carpeta `monedas_app/` completa.** Los `.png` y `.pdf` de `planos/` son lo que ve el profe; el resto es el código que los genera y los prueba.
No subas `__pycache__/` ni `.pio/` (ya están en `.gitignore`).

## 2. Mapa de archivos (qué es cada cosa)

```
monedas_app/
├─ swarm.py                    Cerebro del enjambre en Python: feromona, 3 obstáculos, sensor de color con ruido, matriz de confusión, regla de errores
├─ experimentos_confusion.py   Corre swarm.py muchas veces (paleta actual vs recomendada, con/sin regla) y guarda planos/resultados_confusion.json
├─ firmware/
│  ├─ carrito_hormiga/         Firmware del ESP32 de CADA carrito (el mismo código con otro CARRITO_ID)
│  └─ esp32_monedas/           Firmware viejo del contador de monedas (solo cuenta y sirve /data por WiFi)
├─ planos/                     Láminas 1–7 (PNG + PDF) y los scripts que las dibujan
│  └─ datos_carrito.py         FUENTE ÚNICA: medidas, pesos, posición de cada pieza, consumos y pines. Si cambias algo, cámbialo aquí y corre generar_todo.py
├─ pybullet_sim/               carrito.urdf (modelo) + swarm_pybullet.py (5 carritos en PyBullet)
├─ aco.py, coins.py, simulador.py, mock_esp32.py, esp32_client.py, app.py, interfaz.html
│                              Dashboard del NÚCLEO (monedas/banda). OJO: todavía muestra el dron, no el enjambre
└─ requirements.txt, .gitignore
```

## 3. Cómo probar cada cosa

### 3.1 Instalar (una vez)
```
python -m pip install -r requirements.txt
```

### 3.2 Probar la simulación del enjambre (sin hardware, ~10 s)
```
python -c "from swarm import Enjambre; e=Enjambre(1); [e.step(0.2) for _ in range(9000)]; s=e.estado(); print('ok',s['entregados_ok'],'mal',s['entregados_err']); print(s['confusion']['matriz'])"
```
Simula 30 min con 5 carritos. Debe imprimir algo como `ok 176 mal 3` y una matriz 5×5 casi diagonal con errores entre `$50` y `$200`
(filas = denominación real, columnas = lo que predijo el sensor). Para ver el efecto de la paleta recomendada:
```
python -c "import swarm; swarm.usar_paleta(swarm.PALETA_RECOMENDADA); from swarm import Enjambre; e=Enjambre(1); [e.step(0.2) for _ in range(9000)]; print(e.estado()['confusion']['matriz'])"
```
→ la matriz queda diagonal y `mal` baja a 0.

### 3.3 Regenerar los planos (~20 s)
```
cd planos
python generar_todo.py
```
Reescribe los PNG/PDF. Cambia un número en `datos_carrito.py` (p. ej. la masa de la batería) y vuelve a correr: los planos 1, 2 y 3 cambian solos.

### 3.4 Repetir los experimentos de la matriz de confusión (~6–10 min)
```
python experimentos_confusion.py
cd planos && python lamina7_confusion.py
```

### 3.5 Probar el firmware, paso a paso (con hardware)
1. **Arduino IDE** → Gestor de tarjetas: *esp32* (core 2.x o 3.x; el 2.0.17 es el que se compiló). Placa: *ESP32 Dev Module*.
2. Librerías: *Adafruit VL53L0X*, *Adafruit NeoPixel*, *ESP32Servo*.
3. Abre `firmware/carrito_hormiga/carrito_hormiga.ino`, cambia `CARRITO_ID` (0=$50, 1=$100, 2=$200, 3=$500, 4=$1000) y súbelo.
4. Monitor serie a **115200**. Debe decir `Carrito 0, objetivo $50…` y luego imprimir la tabla `CENT`. Prueba por etapas, **con el carrito en un soporte (ruedas al aire)**:

| Etapa | Comando serial | Qué debe pasar | Si falla |
|---|---|---|---|
| VL53L0X | `t` | `ToF` cambia al acercar la mano (30–250 mm) | Revisa SDA=21 / SCL=22 |
| TCS3200 | `w` (tarjeta blanca) y luego `0`…`4` con la pegatina de cada denominación frente al sensor, a ≈15 mm; `p` imprime la tabla | `rgb` cambia con el color | Revisa S2=18, S3=19, OUT=23; S0→3V3, S1→GND |
| Motores y encoders | `m` | Las dos ruedas giran 1 s y salen cuentas **positivas** | Si una sale negativa invierte `SIGNO_ENC_*`; si no gira, revisa STBY=13 |
| Giroscopio | `d` | `th` cambia al girar el carrito a mano | Quédate quieto 1 s al encender |
| Pinza | edita `PINZA_ABIERTA/CERRADA` y reinicia | Se abre y cierra sobre el vaso | Ajusta los ángulos |
| Todo junto | (solo, en la arena) | Sigue el corredor, detecta un vaso, lo lee, lo lleva al nido | Mira `d` para el estado |

5. Pega la tabla que imprime `p` dentro del código (variable `CENT`) y vuelve a subir. Mide en el carrito real `CUENTAS_POR_VUELTA`, `KFF` (ganancia de velocidad) y los ángulos de la pinza: están marcados `[CALIBRAR]`.
6. Cuando un carrito ande bien, súbele el mismo código a los otros cuatro cambiando solo `CARRITO_ID`. Los 5 comparten feromona por ESP-NOW (canal 1) sin router.

### 3.6 PyBullet (en el computador del curso, no en el mío)
```
pip install pybullet
cd pybullet_sim
python swarm_pybullet.py
```
Carga el URDF de `carrito.urdf`, 5 carritos y los 3 obstáculos. **No lo pude correr** (pybullet no instala en el Python 3.14 del equipo donde lo desarrollé); si falla, avisa el error.

### 3.7 Dashboard del núcleo (opcional)
`streamlit run app.py` o abrir `interfaz.html`. Muestra contador/banda/monedas con datos simulados. **Aún no muestra el enjambre.**

## 4. Qué está probado y qué no (para no prometer de más)

| Cosa | Estado real |
|---|---|
| `swarm.py` y los experimentos | Corridos muchas veces, sin errores |
| Planos | Generados y revisados visualmente |
| Firmware del carrito | **Compila** con el core ESP32 2.0.17 (RAM 15,6 %, flash 62,5 %). Core 3.x sin probar. **Nunca se cargó a un ESP32** |
| `carrito.urdf` | XML válido; masa total 0,286 kg (coincide con el plano) |
| `swarm_pybullet.py` | Solo sintaxis revisada |
| Pesos, consumos y medidas de piezas | **Estimaciones** de hojas de datos: hay que pesar y medir las piezas reales |
| Ruido del sensor de color en la simulación | **Supuesto**: hay que medirlo con el TCS3200 real |
| Regla de errores (E_MAX) | **Interpretación nuestra** de lo que dijo el profe: confirmarla con él |

## 5. Pendientes
- Firmware de la **estación central**: banda, brazo, báscula del nido y el mensaje de verificación ESP-NOW que el carrito espera (`MSG_VERIF`). Los pines están en el plano 6.
- Actualizar `interfaz.html` / `app.py` para mostrar el enjambre en vez del dron.
- Armar un carrito, pesar y medir, y corregir `datos_carrito.py`.
- Correr PyBullet en el entorno del curso.

## 6. Subir a GitHub
```
cd monedas_app
git init
git add .
git status          # revisa que no entren __pycache__ ni .pio
git commit -m "Enjambre de carritos hormiga: planos, firmware, simulación y matriz de confusión"
git branch -M main
git remote add origin https://github.com/<tu-usuario>/<tu-repo>.git
git push -u origin main
```
Pesa ≈ 2,5 MB. Si el profe pide estructura como la del repo `U_Militar`, copia la carpeta `monedas_app/` como una carpeta nueva dentro de él (por ejemplo `13) Enjambre_Carritos/`).
