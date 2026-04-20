# Utvecklingsplan: Edge AI Anomaly Detection (Ericsson Hackathon)

## 1. Systemarkitektur
* **Edge Level (XIAO):** Kontinuerlig sampling av accelerationsdata. Kör enkel lokal signalbehandling.
* **Gateway Level (Raspberry Pi):** Mottagning av data via Serial, logik för händelsestyrd upplänk.
* **Presentation Level (Dashboard):** Visualisering av systemstatus och "6G-besparingar".

## 2. Fas 1: Hårdvarukonfiguration & Dataflöde (Deadline: 11:30)
- [ ] **XIAO nRF52840:** Skriv firmware för att läsa LSM6DS3 (IMU).
    - Samplingsfrekvens: ca 50-100Hz.
    - Format: Skicka CSV-strängar (`x,y,z
`) över `Serial`.
- [ ] **Raspberry Pi:** Skapa ett Python-skript som läser `/dev/ttyACM0`.
    - Använd `pyserial`.
    - Verifiera att rådata kan printas i terminalen.

## 3. Fas 2: Anomaly Detection Logik (Deadline: 13:30)
- [ ] **Algoritm:** Implementera en rullande tröskelvärdesanalys (t.ex. RMS eller absolut max-avvikelse).
    - *Logik:* Om `sqrt(x^2 + y^2 + z^2) > Threshold`, trigga "Event".
- [ ] **Event-Driven Uplink:**
    - Skapa en variabel `uplink_active`.
    - Om ingen anomali: Skicka endast ett "heartbeat" var 10:e sekund.
    - Vid anomali: Starta högfrekvent streaming till dashboarden i 5 sekunder.

## 4. Fas 3: Dashboard & UX (Deadline: 15:30)
- [ ] **Frontend:** Skapa en enkel webbsida (Streamlit eller Flask + Chart.js).
- [ ] **Visualisering:**
    - Graf över vibrationer i realtid.
    - Stor indikator: 🟢 NORMAL / 🔴 ANOMALI.
    - **6G Metric:** "Data Saved" (beräkna skillnaden mellan kontinuerlig streaming vs vår event-driven metod).

## 5. Fas 4: Pitch & Demo-förberedelse (Deadline: 16:30)
- [ ] **Story:** "Vi löser problemet med nätverksöverbelastning i framtidens fabriker."
- [ ] **Demo:** Ha en motor eller skaka på sensorn för att visa hur larmet går igång direkt.

## Teknisk Checklista (För domarna)
- **Scalability:** Systemet klarar tusentals sensorer eftersom vi sparar bandbredd.
- **Latency:** Lokala beslut tas på millisekunder (Edge AI).
- **Sustainability:** Mindre sändning = lägre energiförbrukning.
