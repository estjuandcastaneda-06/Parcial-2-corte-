/*
 * Contador de monedas colombianas + servidor JSON por WiFi (ESP32)
 * SIN PROBAR EN HARDWARE: revisa pines y calibración antes de usar.
 *
 * Sensores:
 *   - Diámetro: potenciómetro lineal (slider con resorte) en PIN_DIAM (ADC1)
 *   - Peso    : celda de carga 100 g + HX711 (PIN_HX_DT / PIN_HX_SCK)
 *   - Barrera IR de paso de moneda en PIN_IR (dispara la medición)
 * Librería: HX711 de Bogdan Necula (Library Manager).
 *
 * La app Streamlit hace GET http://<ip>/data cada ~1 s.
 */
#include <WiFi.h>
#include <WebServer.h>
#include "HX711.h"

const char* WIFI_SSID = "TU_RED";
const char* WIFI_PASS = "TU_CLAVE";

const int PIN_DIAM = 34, PIN_IR = 27, PIN_HX_DT = 16, PIN_HX_SCK = 17;
const int VASO_CAP = 10;

// Calibración: diámetro_mm = D0 + ADC * D_K ; peso_g = (raw - W_OFFSET) / W_SCALE
float D0 = 12.0, D_K = 0.0043;
float W_OFFSET = 0, W_SCALE = 420.0;
// Tolerancias de aceptación (mm, g) por eje
const float TOL_D = 0.30, TOL_W = 0.15;

struct Coin { int denom; bool nueva; float d, w; };
const Coin CAT[] = {
  {50, true, 17.0, 2.00}, {100, true, 20.3, 3.34}, {200, true, 22.4, 4.61},
  {500, true, 23.7, 7.14}, {1000, true, 26.7, 9.95},
  {50, false, 21.0, 4.00}, {100, false, 23.0, 5.31},
  {200, false, 24.4, 7.10}, {500, false, 23.5, 7.40},
};
const int NCAT = sizeof(CAT) / sizeof(CAT[0]);

long conteo[NCAT] = {0};
long rechazadas = 0, enVaso = 0, vasosTotales = 0;
float ultD = 0, ultW = 0, pesoTotal = 0;
int ultClase = -1;

HX711 hx;
WebServer server(80);

int clasificar(float d, float w) {
  int best = -1; float bd = 1e9;
  for (int i = 0; i < NCAT; i++) {
    float dist = hypot((d - CAT[i].d) / TOL_D, (w - CAT[i].w) / TOL_W);
    if (dist < bd) { bd = dist; best = i; }
  }
  return bd <= 1.2 ? best : -1;
}

void medirMoneda() {
  delay(60);  // deja asentar la moneda en el slider y la balanza
  ultD = D0 + analogRead(PIN_DIAM) * D_K;
  ultW = (hx.get_value(3) - W_OFFSET) / W_SCALE;
  ultClase = clasificar(ultD, ultW);
  if (ultClase < 0) { rechazadas++; return; }
  conteo[ultClase]++;
  pesoTotal += CAT[ultClase].w;
  if (++enVaso >= VASO_CAP) { enVaso = 0; vasosTotales++; /* aquí: activar banda/brazo */ }
}

void handleData() {
  String j = "{\"ts\":" + String(millis() / 1000.0, 1) + ",\"uptime_s\":" + String(millis() / 1000);
  j += ",\"contador\":{\"conteo\":{";
  for (int i = 0; i < NCAT; i++) {
    j += "\"" + String(CAT[i].denom) + (CAT[i].nueva ? "_nueva" : "_antigua") + "\":" + String(conteo[i]);
    if (i < NCAT - 1) j += ",";
  }
  j += "},\"rechazadas\":" + String(rechazadas) + ",\"peso_g\":" + String(pesoTotal, 2);
  j += ",\"ultima\":{\"d_mm\":" + String(ultD, 2) + ",\"w_g\":" + String(ultW, 2) + ",\"clase\":";
  j += ultClase < 0 ? "null" : "\"" + String(CAT[ultClase].denom) + (CAT[ultClase].nueva ? "_nueva" : "_antigua") + "\"";
  j += "}},\"vaso\":{\"monedas\":" + String(enVaso) + ",\"capacidad\":" + String(VASO_CAP) + "}";
  // Completar con el estado real de banda/brazo/dron cuando estén integrados:
  j += ",\"embalaje\":{\"en_banda\":0,\"en_tapa\":0,\"listos\":0,\"brazo\":\"en reposo\",\"vasos_totales\":" + String(vasosTotales) + "}";
  j += ",\"dron\":{\"estado\":\"espera\",\"progreso\":0,\"obstaculos_superados\":0,\"vasos_cargados\":0,\"entregados\":0}}";
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", j);
}

void handleCmd() {
  if (server.arg("c") == "reset") {
    for (int i = 0; i < NCAT; i++) conteo[i] = 0;
    rechazadas = enVaso = vasosTotales = 0; pesoTotal = 0;
  }
  server.send(200, "application/json", "{\"ok\":true}");
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_IR, INPUT_PULLUP);
  hx.begin(PIN_HX_DT, PIN_HX_SCK);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(400); Serial.print("."); }
  Serial.println("\nIP: " + WiFi.localIP().toString());
  server.on("/data", handleData);
  server.on("/cmd", handleCmd);
  server.begin();
}

void loop() {
  server.handleClient();
  static bool prev = true;
  bool ir = digitalRead(PIN_IR);
  if (prev && !ir) medirMoneda();   // flanco de bajada: pasó una moneda
  prev = ir;
}
