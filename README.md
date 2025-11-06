# Rocket With Aerodynamic (3D Simulation - BETA)

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![PyGame](https://img.shields.io/badge/PyGame-2.0%2B-green)](https://www.pygame.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Simulasi roket 3D real-time dengan fisika aerodinamika lengkap menggunakan **PyGame** dan **OpenGL**.  
Menyediakan visualisasi roket, efek asap, partikel api, serta data telemetri secara langsung.

## Fitur

- Fisika: drag, lift, thrust vectoring, angle of attack, dynamic pressure (Max Q)
- Visual 3D dengan pencahayaan dan efek panas pada nozzle
- Sistem partikel untuk api mesin dan jejak asap
- HUD lengkap: kecepatan, ketinggian, Mach, TWR, G-force, dll
- Kontrol interaktif menggunakan keyboard dan mouse
- Kamera orbit, zoom, dan auto-rotate
- Infinite grid sebagai referensi posisi

## Requirements

```bash
pip install numpy pyopengl pyopengl-accelerate pygame
```

## Cara Menjalankan

```bash
git clone https://github.com/MalikTzys/Rocket-With-Aerodynamic.git
cd Rocket-With-Aerodynamic
py rocket-aero.py
```

## Kontrol

| Tombol          | Fungsi                          |
|-----------------|---------------------------------|
| Arrow Keys      | Pitch & Yaw                     |
| 1 / 2           | Roll                            |
| A / D           | Kurangi / Tambah thrust         |
| W / S           | Kurangi / Tambah massa          |
| + / -           | Percepat / Perlambat simulasi   |
| SPACE           | Pause                           |
| R               | Reset                           |
| TAB             | Buka panel pengaturan           |
| V               | Tampilkan/sembunyikan vektor    |
| F               | Wireframe mode                  |
| Mouse drag      | Rotasi kamera                   |
| Scroll          | Zoom                            |

## Parameter Roket

Semua parameter dapat diubah di dalam class `Rocket`:

```python
self.dry_mass = 2000.0          # kg
self.fuel_mass = 3000.0         # kg
self.thrust = 75000.0           # N
self.max_thrust = 200000.0      # N
self.drag_coefficient = 0.45
self.reference_area = 10.0      # m²
```

## License

Proyek ini menggunakan lisensi **MIT**.  
Silakan gunakan, modifikasi, dan bagikan dengan bebas.
