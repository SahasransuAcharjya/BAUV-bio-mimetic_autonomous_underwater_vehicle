# BAUV: Bio-Mimetic Autonomous Underwater Vehicle

This project focuses on the development of a bio-mimetic autonomous underwater vehicle (BAUV) that utilizes a tail-driven propulsion system modeled after the locomotion of a fish. The system integrates real-time hardware control via a Python-based Dash dashboard and an Arduino-powered servo-actuation system with inertial sensing.

---

## 🚀 System Architecture

The BAUV framework consists of three primary layers:
1.  **Hardware Control (Firmware):** An Arduino script (`servo_controller.ino`) that manages high-frequency servo oscillations and streams motion data from an MPU6050 sensor.
2.  **Real-Time Dashboard (Software):** A Python Dash application (`dashboard.py`) that provides a graphical user interface (GUI) for controlling the vehicle and visualizing live sensor telemetry.
3.  **Configuration & Data:** A centralized `config.json` for managing serial port settings, servo constraints, and logging parameters.


---

## ✨ Key Features

* **Bio-Mimetic Propulsion:** Implements sine-wave-based tail oscillation with adjustable frequency, amplitude, and base positioning.
* **Dual-Sensing Telemetry:** Provides live streaming of linear acceleration and angular velocity via the MPU6050 IMU.
* **Interactive Control:** * **Oscillation Control:** Dynamically start, stop, or calibrate the servo motion.
    * **Live Tuning:** Adjust base angles, frequencies (Hz), and amplitudes (deg) in real-time through the dashboard sliders and inputs.
* **Data Visualization:** Dark-themed, responsive Plotly graphs tracking servo angles and 6-axis IMU data.
* **Robust Communication:** Multi-threaded serial handling with automatic reconnection and status monitoring.

---

## 🛠️ Tech Stack

* **Microcontroller:** Arduino (C++) using `Servo.h` and `MPU6050.h`.
* **Backend:** Python 3.13 with `pyserial` for communication.
* **Frontend:** `Dash` by Plotly for the interactive web UI.
* **Data Management:** `deque` for efficient real-time data handling and `JSON` for system configuration.

---

## ⚙️ Configuration

The system is highly configurable via `config/config.json`. Key parameters include:

| Category | Key | Description |
| :--- | :--- | :--- |
| **Serial** | `port` | The COM port for the Arduino (Default: `COM7`) |
| | `baudrate` | Data transmission speed (Recommended: `115200` for IMU streaming) |
| **Servo** | `max_frequency_hz` | Software limit for tail oscillation speed |
| | `max_amplitude_deg` | Maximum sweep angle to prevent mechanical strain |
| **Logging** | `enable_position_log` | Records servo trajectory to `servo_positions.csv` |

---

## 🚦 Getting Started

### 1. Firmware Setup
1.  Connect your Arduino and MPU6050 (SDA to A4, SCL to A5 on Uno).
2.  Open `servo_controller/servo_controller.ino`.
3.  Ensure the `Servo` and `MPU6050` libraries are installed in your Arduino IDE.
4.  Upload the code to your board.

### 2. Software Installation
1.  Install the required Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Verify the serial port in `config.json` matches your device.
3.  Run the dashboard:
    ```bash
    python dashboard.py
    ```
4.  Access the interface at `http://127.0.0.1:8050`.

---

## 📡 Serial Protocol

The system uses a custom comma-separated protocol for bi-directional communication:

* **Outbound (To Arduino):**
    * `CAL,angle`: Sets a fixed servo position.
    * `OSC,base,freq,amp`: Begins sinusoidal oscillation.
    * `STOP`: Halts oscillation and returns to base.
    * `MPU_START/STOP`: Toggles IMU data streaming.

* **Inbound (To Python):**
    * `SERVO,val`: Current calculated servo position.
    * `MPU,ax,ay,az,gx,gy,gz`: Raw 6-axis motion data.
    * `SYS,status`: System boot and initialization alerts.


---

## 🛡️ Safety Constraints
The firmware includes safety checks to prevent mechanical damage:
* **Angle Constraining:** All servo movements are constrained between 0 and 180 degrees.
* **Amplitude Clipping:** The system automatically reduces oscillation amplitude if it would exceed the servo's physical range based on the current base position.