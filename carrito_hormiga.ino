/*
 * CARRITO HORMIGA — firmware del ESP32 (uno por carrito, 5 en total)
 * ---------------------------------------------------------------------------
 * Hace en hardware lo mismo que swarm.py hace en simulación:
 *   - navega por odometría (encoders N20 + giroscopio MPU6050) sobre la grilla de la arena
 *   - lleva SU mapa de feromona (42 x 24 celdas de 50 mm) y lo comparte por ESP-NOW
 *   - detecta vasos con el VL53L0X, lee el color con el TCS3200 y lo clasifica
 *   - lleva la matriz de confusión y el contador de errores; al llegar a E_MAX vuelve
 *     al nido (objetivo) a dejar lo que lleve y recalibrar el sensor de color
 *
 * ESTADO: compila (ver platformio.ini) pero NO se ha probado en hardware. Todas las
 * constantes marcadas con [CALIBRAR] hay que medirlas en el carrito real.
 *
 * Librerías (Gestor de librerías de Arduino): Adafruit VL53L0X, Adafruit NeoPixel,
 * ESP32Servo. Placa: "ESP32 Dev Module". Funciona con el core ESP32 2.x y 3.x.
 *
 * ANTES DE SUBIR: cambia CARRITO_ID (0..4). Cada carrito busca UNA denominación:
 *   0 -> $50   1 -> $100   2 -> $200   3 -> $500   4 -> $1000
 *
 * Marco de referencia (igual que swarm.py): x hacia la zona de vasos, y hacia abajo en el
 * plano de la arena, th = ángulo desde +x hacia +y (crece en sentido horario visto desde arriba).
 */
#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <ESP32Servo.h>
#include <Adafruit_NeoPixel.h>
#include <Adafruit_VL53L0X.h>

#ifndef ESP_ARDUINO_VERSION_MAJOR
#define ESP_ARDUINO_VERSION_MAJOR 2
#endif
#if ESP_ARDUINO_VERSION_MAJOR >= 3
typedef const esp_now_recv_info_t* NowOrigen;     // core 3.x (ESP-IDF 5)
#else
typedef const uint8_t* NowOrigen;                  // core 2.x: la MAC del emisor
#endif

// ============================================================================
// 1. CONFIGURACIÓN
// ============================================================================
#define CARRITO_ID 0                                   // <- cambiar en cada carrito (0..4)
static const uint16_t DENOMS[5] = {50, 100, 200, 500, 1000};
static const uint8_t  MI_IDX = CARRITO_ID;

// ---- pines (ver planos/lamina_5_esquema_carrito) -------------------------------------
// Puente H TB6612FNG
static const uint8_t PIN_PWMA = 25, PIN_AIN1 = 26, PIN_AIN2 = 27;     // motor izquierdo
static const uint8_t PIN_PWMB = 14, PIN_BIN1 = 32, PIN_BIN2 = 4;      // motor derecho
static const uint8_t PIN_STBY = 13;
// Encoders Hall de los N20 (pines solo-entrada del ESP32, sirven perfecto)
static const uint8_t PIN_ENC_I_A = 34, PIN_ENC_I_B = 35, PIN_ENC_D_A = 36, PIN_ENC_D_B = 39;
// TCS3200 (S0 -> 3V3 y S1 -> GND por cableado fijo: escala de frecuencia 20 %)
static const uint8_t PIN_TCS_S2 = 18, PIN_TCS_S3 = 19, PIN_TCS_OUT = 23;
// I2C: VL53L0X (0x29) + MPU6050 (0x68)
static const uint8_t PIN_SDA = 21, PIN_SCL = 22;
// Servos de la pinza, LED de estado y medición de batería
static const uint8_t PIN_SERVO_I = 16, PIN_SERVO_D = 17, PIN_LED = 5, PIN_VBAT = 33;

// ---- mecánica / odometría [CALIBRAR] -------------------------------------------------
static const float RUEDA_D_MM = 42.0f;
static const float TROCHA_MM = 110.0f;
static const float CUENTAS_POR_VUELTA = 1400.0f;       // 7 pulsos x 100:1 x 2 flancos de A. Ajustar al motor real.
static const float MM_POR_CUENTA = (PI * RUEDA_D_MM) / CUENTAS_POR_VUELTA;
static const int8_t SIGNO_ENC_I = +1, SIGNO_ENC_D = -1; // el motor derecho gira al revés visto desde el encoder
static const float V_MAX_MM_S = 250.0f;                // velocidad de crucero
static const float PWM_MAX_FRAC = 0.80f;               // N20 de 6 V alimentados con 7.4 V: limitar a 80 %

// ---- arena (mismas celdas que swarm.py) -----------------------------------------------
static const int   GW = 42, GH = 24;
static const float CELDA_MM = 50.0f;
struct Rect { int x, y, w, h; };
static const Rect OBST[3] = {{18, 0, 2, 15}, {26, 9, 2, 15}, {33, 0, 2, 15}};
static const float NIDO_CX = 2, NIDO_CY = 12;
static const float ZONA_X = 34.0f;
// Celdas de salida de cada carrito (lámina 4 del plano de la arena); todos arrancan mirando hacia +x.
static const float SALIDA[5][2] = {{4, 3}, {4, 20}, {4, 12}, {7, 6}, {7, 17}};
static const int   CORR_N = 9;
static const float CORR[CORR_N][2] = {{2, 12}, {13, 12}, {15, 20}, {22, 20}, {24.5f, 4}, {29.5f, 4}, {31, 19}, {37, 19}, {38, 12}};

// ---- feromona (mismos valores que swarm.py) ------------------------------------------
static const float RHO = 0.045f;                       // evaporación por segundo
static const float DEPOSITO_BASE = 26.0f;
static const float TAU_MAX = 300.0f;

// ---- detección y lectura de color ----------------------------------------------------
static const float SENSOR_R_MM = 250.0f;               // alcance útil del VL53L0X
static const float DIST_LISTO_MM = 45.0f;              // lectura del VL53L0X con el vaso entre los dedos
static const float OFFSET_PINZA_MM = 115.0f;           // centro del carrito -> centro del vaso sujeto
static const float MARGEN_DUDA = 0.70f;                // (d2-d1)/d2 por debajo => relee
static const uint8_t MAX_LECTURAS = 5;
static const uint32_t T_LECTURA_MS = 1000, T_RELECTURA_MS = 800, T_RECAL_MS = 6000, T_VETO_MS = 45000;
static const uint8_t E_MAX = 2;                        // errores confirmados para ir a recalibrar
// Centroides de cromaticidad (r,g,b)/(r+g+b) de cada pegatina. VALORES POR DEFECTO de la simulación:
// [CALIBRAR] con el comando serial '0'..'4' (ver leerSerial) y pegar aquí la tabla que imprime 'p'.
static float CENT[5][3] = {
  {0.328f, 0.333f, 0.340f},   // $50   plateado
  {0.460f, 0.371f, 0.169f},   // $100  dorado
  {0.347f, 0.341f, 0.311f},   // $200  beige
  {0.665f, 0.209f, 0.126f},   // $500  rojo
  {0.124f, 0.446f, 0.430f},   // $1000 verde azulado
};

// ---- pinza (ángulos de servo) [CALIBRAR] ---------------------------------------------
static const int PINZA_ABIERTA = 35, PINZA_CERRADA = 95;   // grados; el servo derecho va espejado

// ---- batería ----------------------------------------------------------------------
static const float VBAT_MIN = 6.4f;                     // 3.2 V por celda: apagar motores
static const float DIVISOR = (100.0f + 47.0f) / 47.0f;  // R1 100k, R2 47k

// ============================================================================
// 2. ESTADO GLOBAL
// ============================================================================
enum Estado : uint8_t { EXPLORAR, ACERCAR, LEYENDO, TRANSPORTAR, ENTREGANDO, RETORNO, RECALIBRANDO, BATERIA_BAJA };
static const char* NOMBRE_ESTADO[] = {"explorar", "acercar", "leyendo", "transportar", "entregando", "retorno", "recalibrando", "bateria"};

struct Pose { float x, y, th; };                         // mm, mm, rad
static Pose pose = {NIDO_CX * CELDA_MM, NIDO_CY * CELDA_MM, 0};

static Estado estado = EXPLORAR;
static uint32_t tEstado = 0;                             // millis() al entrar al estado

// feromona
static float tau[GH][GW];

// sensores
static Adafruit_VL53L0X lox;
static bool tofOk = false;
static uint16_t tofMm = 8190;
static float gz_bias = 0;                                // °/s
static float gainRGB[3] = {1, 1, 1};                     // balance de blancos del TCS3200

// encoders
static volatile long encI = 0, encD = 0;

// errores y matriz de confusión local: conf[real][predicho]; solo se llena con vasos que ESTE carrito
// aceptó y que la báscula del nido verificó (predicho = MI_IDX siempre).
static uint16_t conf[5][5];
static uint8_t errores = 0, recalibraciones = 0;
static uint16_t entregadosOk = 0, entregadosErr = 0, rechazos = 0, dudosas = 0;
static uint8_t falsosPorReal[5];
static bool pidioRecal = false;

// vaso en curso
static float lectura[MAX_LECTURAS][3];
static uint8_t nLect = 0;
static bool primeraDuda = true;
static float vasoX = 0, vasoY = 0;                       // posición estimada del vaso candidato (mm)
static float vetoX[6], vetoY[6];
static uint32_t vetoHasta[6];
static uint8_t vetoN = 0;

// navegación
static float rumbo = 0;                                  // rumbo de exploración (rad)
static float v_cmd = 0, w_cmd = 0;                       // comandos de velocidad (mm/s, rad/s)
static float vObjI = 0, vObjD = 0, iI = 0, iD = 0;       // PI de velocidad por rueda
static int lastCX = -1, lastCY = -1;
static float acumDeposito = 0;

// periféricos
static Servo servoI, servoD;
static Adafruit_NeoPixel pixel(1, PIN_LED, NEO_GRB + NEO_KHZ800);

// comunicación
struct __attribute__((packed)) MsgDeposito { uint8_t tipo; uint8_t id; uint8_t cx; uint8_t cy; uint8_t cant; };
struct __attribute__((packed)) MsgTelem {
  uint8_t tipo; uint8_t id; uint8_t cx; uint8_t cy; uint8_t estado; uint8_t errores;
  uint16_t ok; uint16_t err; uint8_t falsos[5];
};
struct __attribute__((packed)) MsgVerif { uint8_t tipo; uint8_t id_dest; uint8_t denom_real_idx; };
enum : uint8_t { MSG_DEPOSITO = 1, MSG_TELEM = 2, MSG_VERIF = 3 };
static const uint8_t BCAST[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

struct Entrante { uint8_t buf[24]; uint8_t len; };
static Entrante cola[16];
static volatile uint8_t colaIn = 0, colaOut = 0;
static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
static struct { float cx, cy; uint32_t t; } pares[5];   // última posición conocida de los demás carritos
static bool verifLlego = false;
static uint8_t verifReal = 0;

// ============================================================================
// 3. UTILIDADES
// ============================================================================
static inline float envolver(float a) { while (a > PI) a -= 2 * PI; while (a < -PI) a += 2 * PI; return a; }
static inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

static bool enObstaculoCelda(float cx, float cy, float margen = 0.4f) {
  for (const Rect& r : OBST)
    if (cx >= r.x - margen && cx <= r.x + r.w + margen && cy >= r.y - margen && cy <= r.y + r.h + margen) return true;
  return !(cx >= 0 && cx <= GW && cy >= 0 && cy <= GH);
}

// ---- PWM de motores (compatible core 2.x y 3.x) ---------------------------------------
static const uint32_t PWM_FREQ = 20000;
static const uint8_t PWM_BITS = 8;
static const uint8_t CH_A = 4, CH_B = 5;                 // canales 4/5: no chocan con los timers del ESP32Servo
static void pwmIniciar(uint8_t pin, uint8_t ch) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  (void)ch; ledcAttach(pin, PWM_FREQ, PWM_BITS);
#else
  ledcSetup(ch, PWM_FREQ, PWM_BITS); ledcAttachPin(pin, ch);
#endif
}
static void pwmEscribir(uint8_t pin, uint8_t ch, uint32_t duty) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  (void)ch; ledcWrite(pin, duty);
#else
  (void)pin; ledcWrite(ch, duty);
#endif
}

// ============================================================================
// 4. MOTORES + ENCODERS + ODOMETRÍA
// ============================================================================
static void IRAM_ATTR isrEncI() { if (digitalRead(PIN_ENC_I_A) == digitalRead(PIN_ENC_I_B)) encI++; else encI--; }
static void IRAM_ATTR isrEncD() { if (digitalRead(PIN_ENC_D_A) == digitalRead(PIN_ENC_D_B)) encD++; else encD--; }

// duty en [-255, 255]
static void motorIzq(int duty) {
  duty = constrain(duty, -255, 255);
  digitalWrite(PIN_AIN1, duty > 0); digitalWrite(PIN_AIN2, duty < 0);
  pwmEscribir(PIN_PWMA, CH_A, abs(duty));
}
static void motorDer(int duty) {
  duty = constrain(duty, -255, 255);
  digitalWrite(PIN_BIN1, duty > 0); digitalWrite(PIN_BIN2, duty < 0);
  pwmEscribir(PIN_PWMB, CH_B, abs(duty));
}

static void parar() { v_cmd = 0; w_cmd = 0; }

// Comando de alto nivel: v (mm/s hacia adelante) y w (rad/s, positivo = th crece = giro horario)
static void conducir(float v, float w) { v_cmd = v; w_cmd = w; }

// Gyro Z del MPU6050 (° /s). Convención: th crece en sentido horario visto desde arriba => th' = -gz.
static const uint8_t MPU_ADDR = 0x68;
static float leerGyroZ() {
  Wire.beginTransmission(MPU_ADDR); Wire.write(0x47); Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (uint8_t)2);
  if (Wire.available() < 2) return 0;
  int16_t raw = (Wire.read() << 8) | Wire.read();
  return raw / 131.0f;                                   // ±250 °/s
}

static void calibrarGyro() {
  float s = 0; const int N = 300;
  for (int i = 0; i < N; i++) { s += leerGyroZ(); delay(3); }
  gz_bias = s / N;
}

static long encIprev = 0, encDprev = 0;
static float velI = 0, velD = 0;                         // mm/s medidas

// Se llama cada 20 ms: odometría + lazo PI de velocidad por rueda
static void lazoControl(float dt) {
  noInterrupts(); long ei = encI, ed = encD; interrupts();
  float dI = SIGNO_ENC_I * (ei - encIprev) * MM_POR_CUENTA;
  float dD = SIGNO_ENC_D * (ed - encDprev) * MM_POR_CUENTA;
  encIprev = ei; encDprev = ed;
  velI = dI / dt; velD = dD / dt;
  float ds = 0.5f * (dI + dD);
  float gz = leerGyroZ() - gz_bias;
  pose.th = envolver(pose.th - gz * DEG_TO_RAD * dt);    // giroscopio manda el rumbo
  pose.x += ds * cosf(pose.th);
  pose.y += ds * sinf(pose.th);

  // objetivos por rueda (w>0 = giro horario => rueda izquierda más rápida)
  vObjI = v_cmd + w_cmd * TROCHA_MM * 0.5f;
  vObjD = v_cmd - w_cmd * TROCHA_MM * 0.5f;
  if (estado == BATERIA_BAJA) { vObjI = vObjD = 0; }
  const float KP = 0.55f, KI = 1.8f, KFF = 255.0f / V_MAX_MM_S;   // [CALIBRAR] la ganancia directa KFF
  float eI = vObjI - velI, eD = vObjD - velD;
  iI = clampf(iI + eI * dt, -80, 80); iD = clampf(iD + eD * dt, -80, 80);
  float uI = KFF * vObjI + KP * eI + KI * iI;
  float uD = KFF * vObjD + KP * eD + KI * iD;
  if (fabsf(vObjI) < 1) { uI = 0; iI = 0; }
  if (fabsf(vObjD) < 1) { uD = 0; iD = 0; }
  const float tope = 255.0f * PWM_MAX_FRAC;
  motorIzq((int)clampf(uI, -tope, tope));
  motorDer((int)clampf(uD, -tope, tope));
}

// ============================================================================
// 5. NAVEGACIÓN
// ============================================================================
// Repulsión de obstáculos conocidos y paredes (campo potencial, igual que swarm.py)
static void repulsion(float x, float y, float& rx, float& ry) {
  const float R = 180.0f;
  rx = ry = 0;
  for (const Rect& r : OBST) {
    float x0 = r.x * CELDA_MM, x1 = (r.x + r.w) * CELDA_MM, y0 = r.y * CELDA_MM, y1 = (r.y + r.h) * CELDA_MM;
    float qx = clampf(x, x0, x1), qy = clampf(y, y0, y1);
    float dx = x - qx, dy = y - qy, d = sqrtf(dx * dx + dy * dy);
    if (d < R && d > 0.1f) { float w = (R - d) / R; rx += dx / d * w; ry += dy / d * w; }
  }
  float W = GW * CELDA_MM, H = GH * CELDA_MM;            // paredes del perímetro
  if (x < R) rx += (R - x) / R;
  if (W - x < R) rx -= (R - (W - x)) / R;
  if (y < R) ry += (R - y) / R;
  if (H - y < R) ry -= (R - (H - y)) / R;
}

// Va hacia (tx,ty) en mm. Devuelve la distancia que falta.
static float irA(float tx, float ty, float vmax, bool evitar = true) {
  float dx = tx - pose.x, dy = ty - pose.y, d = sqrtf(dx * dx + dy * dy);
  if (d < 1) { parar(); return d; }
  float ux = dx / d, uy = dy / d;
  if (evitar) {
    float rx, ry; repulsion(pose.x, pose.y, rx, ry);
    ux += 1.6f * rx; uy += 1.6f * ry;
  }
  float err = envolver(atan2f(uy, ux) - pose.th);
  float w = clampf(3.0f * err, -2.5f, 2.5f);
  float v = vmax * fmaxf(0.0f, cosf(err));
  if (d < 100) v *= d / 100.0f;                          // frenar al llegar
  conducir(v, w);
  return d;
}

// Próximo punto del corredor dado (3 obstáculos). Devuelve false si ya no hace falta.
static bool hito(float xCelda, bool haciaZona, float& hx, float& hy) {
  if (haciaZona) {
    for (int i = 1; i < CORR_N; i++) if (CORR[i][0] > xCelda + 1.0f) { hx = CORR[i][0]; hy = CORR[i][1]; return true; }
    return false;
  }
  for (int i = CORR_N - 2; i >= 0; i--) if (CORR[i][0] < xCelda - 1.0f) { hx = CORR[i][0]; hy = CORR[i][1]; return true; }
  return false;
}

// ============================================================================
// 6. FEROMONA
// ============================================================================
static void depositar(int cx, int cy, float cant) {
  if (cx < 0 || cx >= GW || cy < 0 || cy >= GH) return;
  tau[cy][cx] = fminf(TAU_MAX, tau[cy][cx] + cant);
}
static void evaporar(float dt) {
  float f = fmaxf(0.0f, 1.0f - RHO * dt);
  for (int y = 0; y < GH; y++) for (int x = 0; x < GW; x++) tau[y][x] *= f;
}
static float gradiente(int cx, int cy, float& gx, float& gy) {
  float mejor = -1; gx = gy = 0;
  for (int dy = -1; dy <= 1; dy++) for (int dx = -1; dx <= 1; dx++) {
    if (!dx && !dy) continue;
    int nx = cx + dx, ny = cy + dy;
    if (nx < 0 || nx >= GW || ny < 0 || ny >= GH || enObstaculoCelda(nx, ny)) continue;
    if (tau[ny][nx] > mejor) { mejor = tau[ny][nx]; gx = dx; gy = dy; }
  }
  return mejor;
}
static void emitirDeposito(int cx, int cy, float cant) {
  MsgDeposito m = {MSG_DEPOSITO, CARRITO_ID, (uint8_t)cx, (uint8_t)cy, (uint8_t)constrain((int)cant, 1, 255)};
  esp_now_send(BCAST, (uint8_t*)&m, sizeof(m));
}

// ============================================================================
// 7. SENSOR DE COLOR + CLASIFICACIÓN
// ============================================================================
static float leerCanal(bool s2, bool s3) {
  digitalWrite(PIN_TCS_S2, s2); digitalWrite(PIN_TCS_S3, s3);
  delayMicroseconds(400);
  unsigned long suma = 0; int n = 0;
  for (int i = 0; i < 6; i++) { unsigned long t = pulseIn(PIN_TCS_OUT, LOW, 20000); if (t) { suma += t; n++; } }
  if (!n) return 0;
  return 1.0e6f / (2.0f * (float)suma / n);              // frecuencia en Hz (proporcional a la luz)
}
// Cromaticidad (r,g,b)/(r+g+b) con balance de blancos: casi no depende de cuánta luz haya.
static bool leerCromaticidad(float out[3]) {
  float r = leerCanal(LOW, LOW) * gainRGB[0];
  float b = leerCanal(LOW, HIGH) * gainRGB[2];
  float g = leerCanal(HIGH, HIGH) * gainRGB[1];
  float s = r + g + b;
  if (s <= 0) return false;
  out[0] = r / s; out[1] = g / s; out[2] = b / s;
  return true;
}
static float dist3(const float a[3], const float b[3]) {
  float d0 = a[0] - b[0], d1 = a[1] - b[1], d2 = a[2] - b[2];
  return sqrtf(d0 * d0 + d1 * d1 + d2 * d2);
}
// Centroide más cercano. Devuelve el índice de denominación y el margen de confianza.
static uint8_t clasificar(const float c[3], float& margen) {
  float d1 = 1e9f, d2 = 1e9f; uint8_t k1 = 0;
  for (uint8_t k = 0; k < 5; k++) {
    float d = dist3(c, CENT[k]);
    if (d < d1) { d2 = d1; d1 = d; k1 = k; } else if (d < d2) { d2 = d; }
  }
  margen = d2 > 0 ? (d2 - d1) / d2 : 1.0f;
  return k1;
}
static void balanceBlancos() {                           // con la tarjeta blanca del nido delante del sensor
  gainRGB[0] = gainRGB[1] = gainRGB[2] = 1;
  float r = leerCanal(LOW, LOW), b = leerCanal(LOW, HIGH), g = leerCanal(HIGH, HIGH);
  if (r > 0 && g > 0 && b > 0) { float m = (r + g + b) / 3; gainRGB[0] = m / r; gainRGB[1] = m / g; gainRGB[2] = m / b; }
}

// ============================================================================
// 8. PINZA, LED, BATERÍA
// ============================================================================
static void pinza(bool cerrar) {
  int a = cerrar ? PINZA_CERRADA : PINZA_ABIERTA;
  servoI.write(a); servoD.write(180 - a);
}
static void ponerLED(uint8_t r, uint8_t g, uint8_t b) { pixel.setPixelColor(0, pixel.Color(r, g, b)); pixel.show(); }
static void actualizarLED() {
  switch (estado) {
    case EXPLORAR:     ponerLED(0, 0, 40); break;
    case ACERCAR:      ponerLED(40, 30, 0); break;
    case LEYENDO:      ponerLED(40, 0, 40); break;
    case TRANSPORTAR:  ponerLED(0, 50, 0); break;
    case ENTREGANDO:   ponerLED(0, 40, 40); break;
    case RETORNO:      ponerLED(50, 15, 0); break;
    case RECALIBRANDO: ponerLED(40, 40, 40); break;
    case BATERIA_BAJA: ponerLED((millis() / 300) % 2 ? 60 : 0, 0, 0); break;
  }
}
static float leerVBat() { return analogReadMilliVolts(PIN_VBAT) / 1000.0f * DIVISOR; }

// ============================================================================
// 9. ESP-NOW
// ============================================================================
static void encolar(const uint8_t* data, int len) {
  if (len <= 0 || len > (int)sizeof(cola[0].buf)) return;
  portENTER_CRITICAL(&mux);
  uint8_t sig = (colaIn + 1) & 15;
  if (sig != colaOut) { memcpy(cola[colaIn].buf, data, len); cola[colaIn].len = len; colaIn = sig; }
  portEXIT_CRITICAL(&mux);
}
// El 1er parámetro del callback cambió entre core 2.x (MAC) y 3.x (info). NO se duplica la función dentro de
// un #if: el preprocesador de .ino genera prototipos sin respetar los #if y rompería la compilación.
static void alRecibir(NowOrigen, const uint8_t* data, int len) { encolar(data, len); }

static void procesarMensajes() {
  while (colaOut != colaIn) {
    Entrante e = cola[colaOut]; colaOut = (colaOut + 1) & 15;
    if (e.buf[0] == MSG_DEPOSITO && e.len >= (int)sizeof(MsgDeposito)) {
      MsgDeposito* m = (MsgDeposito*)e.buf;
      if (m->id != CARRITO_ID) depositar(m->cx, m->cy, m->cant);     // la feromona de las demás hormigas
    } else if (e.buf[0] == MSG_TELEM && e.len >= (int)sizeof(MsgTelem)) {
      MsgTelem* m = (MsgTelem*)e.buf;
      if (m->id < 5 && m->id != CARRITO_ID) { pares[m->id].cx = m->cx; pares[m->id].cy = m->cy; pares[m->id].t = millis(); }
    } else if (e.buf[0] == MSG_VERIF && e.len >= (int)sizeof(MsgVerif)) {
      MsgVerif* m = (MsgVerif*)e.buf;
      if (m->id_dest == CARRITO_ID && m->denom_real_idx < 5) { verifLlego = true; verifReal = m->denom_real_idx; }
    }
  }
}
static void enviarTelemetria() {
  MsgTelem m;
  m.tipo = MSG_TELEM; m.id = CARRITO_ID;
  m.cx = constrain((int)(pose.x / CELDA_MM), 0, GW - 1); m.cy = constrain((int)(pose.y / CELDA_MM), 0, GH - 1);
  m.estado = estado; m.errores = errores; m.ok = entregadosOk; m.err = entregadosErr;
  memcpy(m.falsos, falsosPorReal, 5);
  esp_now_send(BCAST, (uint8_t*)&m, sizeof(m));
}
static bool hayParCerca(float x, float y, float radio_mm) {
  for (uint8_t i = 0; i < 5; i++) {
    if (i == CARRITO_ID || millis() - pares[i].t > 2000) continue;
    float dx = pares[i].cx * CELDA_MM - x, dy = pares[i].cy * CELDA_MM - y;
    if (dx * dx + dy * dy < radio_mm * radio_mm) return true;
  }
  return false;
}

// ============================================================================
// 10. MÁQUINA DE ESTADOS (se ejecuta cada 100 ms)
// ============================================================================
static void cambiar(Estado e) { estado = e; tEstado = millis(); }

static void registrarError() {
  errores++;
  if (errores >= E_MAX) pidioRecal = true;
}
static bool vetado(float x, float y) {
  for (uint8_t i = 0; i < vetoN; i++)
    if (millis() < vetoHasta[i] && hypotf(vetoX[i] - x, vetoY[i] - y) < 120) return true;
  return false;
}
static void vetar(float x, float y) {
  uint8_t i = vetoN < 6 ? vetoN++ : 0;
  vetoX[i] = x; vetoY[i] = y; vetoHasta[i] = millis() + T_VETO_MS;
}
// Al llegar al nido el carrito viene del corredor, o sea mirando hacia -x (th = PI): se corrige la deriva de la odometría.
static void resetPoseNido() { pose.x = NIDO_CX * CELDA_MM; pose.y = NIDO_CY * CELDA_MM; pose.th = PI; }
// Maniobra corta sin bloquear (p. ej. retroceder tras rechazar un vaso): decidir() la ejecuta antes que nada.
static uint32_t tManiobraFin = 0;
static float vManiobra = 0;

static void decidir(float dt) {
  float cxF = pose.x / CELDA_MM, cyF = pose.y / CELDA_MM;
  int cx = constrain((int)cxF, 0, GW - 1), cy = constrain((int)cyF, 0, GH - 1);
  uint32_t enEstado = millis() - tEstado;

  if (estado != BATERIA_BAJA && leerVBat() < VBAT_MIN) { parar(); cambiar(BATERIA_BAJA); }
  if (millis() < tManiobraFin) { conducir(vManiobra, 0); return; }
  if (vManiobra != 0) { parar(); vManiobra = 0; }

  switch (estado) {
    case EXPLORAR: {
      if (pidioRecal) { cambiar(RETORNO); break; }
      // ¿el VL53L0X ve algo que NO es una pared, un obstáculo conocido ni otro carrito?
      if (tofOk && tofMm < SENSOR_R_MM) {
        float hx = pose.x + (tofMm + 20) * cosf(pose.th), hy = pose.y + (tofMm + 20) * sinf(pose.th);
        bool estatico = enObstaculoCelda(hx / CELDA_MM, hy / CELDA_MM, 1.2f);
        if (!estatico && !hayParCerca(hx, hy, 180) && !vetado(hx, hy)) {
          vasoX = hx; vasoY = hy; cambiar(ACERCAR); parar(); break;
        }
      }
      float hxc, hyc;
      if (cxF < ZONA_X && hito(cxF, true, hxc, hyc)) {   // aún no cruza los 3 obstáculos: corredor dado
        irA(hxc * CELDA_MM, (hyc + (random(-6, 7) / 10.0f)) * CELDA_MM, V_MAX_MM_S);
        break;
      }
      float gx, gy, val = gradiente(cx, cy, gx, gy);     // dentro de la zona: feromona + caminata correlacionada
      if (val > 2.0f) rumbo = atan2f(gy, gx);
      else rumbo += random(-70, 71) / 100.0f;
      float tx = clampf(pose.x + cosf(rumbo) * 160, (ZONA_X - 2) * CELDA_MM, (GW - 1) * CELDA_MM);
      float ty = clampf(pose.y + sinf(rumbo) * 160, 0, (GH - 1) * CELDA_MM);
      irA(tx, ty, V_MAX_MM_S * 0.8f);
      break;
    }
    case ACERCAR: {
      pinza(false);
      if (!tofOk || tofMm > SENSOR_R_MM + 150 || enEstado > 9000) { vetar(vasoX, vasoY); cambiar(EXPLORAR); break; }
      if (tofMm <= DIST_LISTO_MM) { parar(); nLect = 0; primeraDuda = true; cambiar(LEYENDO); break; }
      float vel = clampf((tofMm - DIST_LISTO_MM) * 1.5f, 40.0f, 120.0f);   // despacio al final
      conducir(vel, 0);
      break;
    }
    case LEYENDO: {
      parar();
      uint32_t espera = T_LECTURA_MS + (nLect > 1 ? (nLect - 1) * T_RELECTURA_MS : 0);
      if (nLect == 0) { if (leerCromaticidad(lectura[0])) nLect = 1; break; }
      if (enEstado < espera) break;
      float prom[3] = {0, 0, 0};
      for (uint8_t i = 0; i < nLect; i++) for (uint8_t k = 0; k < 3; k++) prom[k] += lectura[i][k] / nLect;
      float margen; uint8_t pred = clasificar(prom, margen);
      if (margen < MARGEN_DUDA && nLect < MAX_LECTURAS) {     // lectura dudosa: releer y promediar
        if (primeraDuda) { dudosas++; primeraDuda = false; }
        if (leerCromaticidad(lectura[nLect])) nLect++;
        break;
      }
      if (pred == MI_IDX) {
        pinza(true); lastCX = -1; acumDeposito = 0; cambiar(TRANSPORTAR);
      } else {
        rechazos++; vetar(vasoX, vasoY);
        pinza(false); rumbo = pose.th + HALF_PI;
        vManiobra = -80; tManiobraFin = millis() + 700;      // retrocede 0,7 s sin bloquear el lazo de control
        cambiar(EXPLORAR);
      }
      break;
    }
    case TRANSPORTAR: {
      if (enEstado < 600) { parar(); break; }          // deja que la pinza cierre antes de arrancar
      float hxc, hyc;
      float objX = NIDO_CX * CELDA_MM, objY = NIDO_CY * CELDA_MM;
      if (hito(cxF, false, hxc, hyc)) { objX = hxc * CELDA_MM; objY = hyc * CELDA_MM; }
      irA(objX, objY, V_MAX_MM_S * 0.8f);                // con carga, más despacio
      // marca de feromona: más fuerte cuanto más lejos del nido
      float lejos = fminf(1.0f, hypotf(cxF - NIDO_CX, cyF - NIDO_CY) / 35.0f);
      acumDeposito += DEPOSITO_BASE * dt * 4 * (0.5f + 1.5f * lejos);
      if (cx != lastCX || cy != lastCY) {
        if (lastCX >= 0 && acumDeposito >= 1) { depositar(lastCX, lastCY, acumDeposito); emitirDeposito(lastCX, lastCY, acumDeposito); }
        acumDeposito = 0; lastCX = cx; lastCY = cy;
      }
      if (hypotf(cxF - NIDO_CX, cyF - NIDO_CY) < 0.9f) { parar(); resetPoseNido(); cambiar(ENTREGANDO); verifLlego = false; }
      break;
    }
    case ENTREGANDO: {
      parar();
      if (enEstado < 300) { pinza(false); break; }
      if (enEstado < 1300) { conducir(-100, 0); break; }  // retrocede ~100 mm para soltar el vaso
      parar();
      // la báscula HX711 del nido pesa el vaso y manda la denominación REAL (MSG_VERIF)
      if (!verifLlego && enEstado < 4300) break;
      if (verifLlego) {
        conf[verifReal][MI_IDX]++;
        if (verifReal == MI_IDX) entregadosOk++;
        else { entregadosErr++; falsosPorReal[verifReal]++; registrarError(); }
      } else {
        entregadosOk++;                                  // sin verificación: se asume correcto
      }
      depositar((int)NIDO_CX, (int)NIDO_CY, DEPOSITO_BASE * 6);
      emitirDeposito((int)NIDO_CX, (int)NIDO_CY, DEPOSITO_BASE * 6);
      cambiar(pidioRecal ? RECALIBRANDO : EXPLORAR);
      break;
    }
    case RETORNO: {                                      // demasiados errores: va al OBJETIVO (nido)
      float hxc, hyc;
      float objX = NIDO_CX * CELDA_MM, objY = NIDO_CY * CELDA_MM;
      if (hito(cxF, false, hxc, hyc)) { objX = hxc * CELDA_MM; objY = hyc * CELDA_MM; }
      irA(objX, objY, V_MAX_MM_S);
      if (hypotf(cxF - NIDO_CX, cyF - NIDO_CY) < 0.9f) { parar(); resetPoseNido(); cambiar(RECALIBRANDO); }
      break;
    }
    case RECALIBRANDO: {
      parar();
      if (enEstado > T_RECAL_MS) {
        balanceBlancos();                                // tarjeta blanca montada en el muro del nido
        errores = 0; pidioRecal = false; recalibraciones++; vetoN = 0;
        cambiar(EXPLORAR);
      }
      break;
    }
    case BATERIA_BAJA: parar(); break;
  }
}

// ============================================================================
// 11. SERIAL (calibración y diagnóstico)
// ============================================================================
static void imprimirCentroides() {
  Serial.println(F("static float CENT[5][3] = {"));
  for (int k = 0; k < 5; k++) Serial.printf("  {%.3ff, %.3ff, %.3ff},   // $%u\n", CENT[k][0], CENT[k][1], CENT[k][2], DENOMS[k]);
  Serial.println(F("};"));
}
static void leerSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c >= '0' && c <= '4') {                          // pon la pegatina de esa denominación frente al sensor
      float acc[3] = {0, 0, 0}, v[3]; int n = 0;
      for (int i = 0; i < 20; i++) if (leerCromaticidad(v)) { for (int k = 0; k < 3; k++) acc[k] += v[k]; n++; delay(30); }
      if (n) { for (int k = 0; k < 3; k++) CENT[c - '0'][k] = acc[k] / n; Serial.printf("centroide $%u guardado (%d lecturas)\n", DENOMS[c - '0'], n); }
    } else if (c == 'p') imprimirCentroides();
    else if (c == 'w') { balanceBlancos(); Serial.printf("ganancias RGB %.3f %.3f %.3f\n", gainRGB[0], gainRGB[1], gainRGB[2]); }
    else if (c == 't') { float v[3]; leerCromaticidad(v); Serial.printf("ToF %u mm | rgb %.3f %.3f %.3f | vbat %.2f V | th %.1f°\n", tofMm, v[0], v[1], v[2], leerVBat(), pose.th * RAD_TO_DEG); }
    else if (c == 'm') {                                 // prueba de motores y encoders (levanta el carrito)
      long a = encI, b = encD; motorIzq(120); motorDer(120); delay(1000); motorIzq(0); motorDer(0);
      Serial.printf("cuentas en 1 s: izq %ld der %ld\n", encI - a, encD - b);
    } else if (c == 'd') {
      Serial.printf("[%u] %s x=%.0f y=%.0f th=%.1f° errores=%u ok=%u mal=%u rechazos=%u dudosas=%u recal=%u\n", CARRITO_ID,
                    NOMBRE_ESTADO[estado], pose.x, pose.y, pose.th * RAD_TO_DEG, errores, entregadosOk, entregadosErr, rechazos, dudosas, recalibraciones);
      Serial.println(F("matriz de confusión local [real][predicho]:"));
      for (int i = 0; i < 5; i++) { for (int j = 0; j < 5; j++) Serial.printf("%4u", conf[i][j]); Serial.println(); }
    }
  }
}

// ============================================================================
// 12. SETUP / LOOP
// ============================================================================
void setup() {
  Serial.begin(115200);
  pinMode(PIN_AIN1, OUTPUT); pinMode(PIN_AIN2, OUTPUT); pinMode(PIN_BIN1, OUTPUT); pinMode(PIN_BIN2, OUTPUT);
  pinMode(PIN_STBY, OUTPUT); digitalWrite(PIN_STBY, LOW);
  pwmIniciar(PIN_PWMA, CH_A); pwmIniciar(PIN_PWMB, CH_B);
  motorIzq(0); motorDer(0);
  pinMode(PIN_ENC_I_A, INPUT); pinMode(PIN_ENC_I_B, INPUT); pinMode(PIN_ENC_D_A, INPUT); pinMode(PIN_ENC_D_B, INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_I_A), isrEncI, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_D_A), isrEncD, CHANGE);
  pinMode(PIN_TCS_S2, OUTPUT); pinMode(PIN_TCS_S3, OUTPUT); pinMode(PIN_TCS_OUT, INPUT);
  pixel.begin(); pixel.setBrightness(40); ponerLED(40, 40, 0);

  Wire.begin(PIN_SDA, PIN_SCL); Wire.setClock(400000);
  Wire.beginTransmission(MPU_ADDR); Wire.write(0x6B); Wire.write(0); Wire.endTransmission();   // despierta el MPU6050
  tofOk = lox.begin();
  if (tofOk) lox.startRangeContinuous(50);
  else Serial.println(F("VL53L0X no responde: revisa SDA/SCL"));

  servoI.setPeriodHertz(50); servoD.setPeriodHertz(50);
  servoI.attach(PIN_SERVO_I, 500, 2400); servoD.attach(PIN_SERVO_D, 500, 2400);
  pinza(false);

  analogSetPinAttenuation(PIN_VBAT, ADC_11db);
  Serial.printf("Carrito %u, objetivo $%u. Dejar QUIETO 1 s para calibrar el giroscopio...\n", CARRITO_ID, DENOMS[MI_IDX]);
  delay(500); calibrarGyro();

  WiFi.mode(WIFI_STA); WiFi.disconnect();
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);        // todos los carritos y el nido en el canal 1
  if (esp_now_init() == ESP_OK) {
    esp_now_register_recv_cb(alRecibir);
    esp_now_peer_info_t peer = {}; memcpy(peer.peer_addr, BCAST, 6); peer.channel = 0; peer.encrypt = false;
    esp_now_add_peer(&peer);
  } else Serial.println(F("ESP-NOW no inició"));

  randomSeed(esp_random());
  pose.x = SALIDA[CARRITO_ID][0] * CELDA_MM; pose.y = SALIDA[CARRITO_ID][1] * CELDA_MM; pose.th = 0;   // posición de salida (plano de la arena)
  rumbo = 0;
  digitalWrite(PIN_STBY, HIGH);                          // habilita el puente H
  tEstado = millis();
  imprimirCentroides();
}

void loop() {
  static uint32_t tCtrl = 0, tDec = 0, tEvap = 0, tTelem = 0, tLed = 0;
  uint32_t now = millis();

  leerSerial();
  procesarMensajes();
  if (tofOk && lox.isRangeComplete()) {                  // lectura continua del VL53L0X (no bloquea)
    uint16_t r = lox.readRange();
    tofMm = (lox.readRangeStatus() == 0) ? r : 8190;
  }
  if (now - tCtrl >= 20) { lazoControl((now - tCtrl) / 1000.0f); tCtrl = now; }
  if (now - tDec >= 100) { decidir(0.1f); tDec = now; }
  if (now - tEvap >= 1000) { evaporar(1.0f); tEvap = now; }
  if (now - tTelem >= 500) { enviarTelemetria(); tTelem = now; }
  if (now - tLed >= 100) { actualizarLED(); tLed = now; }
}
