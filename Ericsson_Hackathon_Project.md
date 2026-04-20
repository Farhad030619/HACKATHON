# Projekt: Edge Anomaly Detection med Event-Driven 6G Uplink
**Ericsson Hackathon 2026**

## 🎯 Översikt
Detta projekt demonstrerar framtidens industriella övervakning genom att flytta intelligensen till nätverkets ytterkant (Edge). Genom att använda **Edge AI** för att detektera anomalier lokalt kan vi minimera dataöverföring, spara energi och utnyttja 6G-nätets förmåga för händelsestyrd kommunikation.

## 🛠 Teknisk Stack
* **Sensor:** Seeed XIAO nRF52840 Sense (LSM6DS3 IMU).
* **Edge Gateway:** Raspberry Pi.
* **Kommunikation:** Seriell (USB) -> Edge Parsing -> 6G Simulation (Event-driven).
* **Analys:** Lokal tröskelvärdesdetektering för realtidsanalys av vibrationer.

## 🚀 6G-Vinkeln: Varför detta är relevant för Ericsson
I en värld med miljontals sensorer (Massive IoT) är det ohållbart att streama rådata konstant. Vår lösning adresserar tre nyckelområden i 6G-visionen:
1.  **Energy Efficiency:** Radion aktiveras endast vid anomalier, vilket maximerar batteritid.
2.  **Bandwidth Optimization:** Endast relevant data (avvikelser) skickas till molnet.
3.  **URLLC (Ultra-Reliable Low Latency):** Vid kritiska fel utnyttjas 6G-länkens låga latens för omedelbara säkerhetsåtgärder (t.ex. nödstopp).

## 🏭 Use Case: Predictive Maintenance
Vi fokuserar på övervakning av industrimotorer och kullager.
* **Normal drift:** Lokala mätningar sker kontinuerligt men tyst.
* **Anomali:** Systemet detekterar ett begynnande lagerfel, aktiverar upplänken och skickar varningsdata till en kontrollpanel.

## 📊 Dashboard & Visualisering
Vår dashboard visar:
* Realtidsdata från accelerometern (X, Y, Z).
* **Status:** "System Healthy" vs "Anomaly Detected".
* **Besparing:** Visualisering av sparad bandbredd genom att inte sända under normal drift.

---
*Utvecklat under Ericsson Hackathon 2026, Kista HQ.*
