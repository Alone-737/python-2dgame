# SDL3 Python Game Port

This repository contains a **Python** port of a game originally developed in **C/C++** using **SDL3**.

The original project can be found here: [constref/sdl3-gamedev](https://github.com/constref/sdl3-gamedev)

---

## About

- The original game is written in C/C++ with SDL3.
- This version reimplements the game logic and functionality in Python.
- The port aims to preserve the gameplay and feel of the original while taking advantage of Python’s simplicity and flexibility.

---

## Features

- Complete game logic reimplemented using **Python** and **SDL3 bindings**.
- Faithful recreation of the original gameplay mechanics.
- **Newly added features in the Python port:**
  - **Infinite gameplay** – the game continues endlessly, offering replay value. 
  - **Player HP and Enemy HP system** for combat dynamics.
  - **Random terrain generation** on every run to increase replayability.
  - **4 background music tracks** – switchable.
  - **Extended control scheme**:
    - `A` – Move backward  
    - `D` – Move forward  
    - `J` – Fire weapon  
    - `K` – Jump  
    - `F11` – Toggle fullscreen  
    - `F12` – Open debug window  
    - `F10` – Choose debug mode
- Easier to customize and extend due to Python’s high-level nature.

---

## How to Run

1. **Install required dependencies** (using `pip`, `pipx`, or your preferred method):
    - `sdl3`
    - `sdl3.SDL_image`
    - `sdl2.sdlmixer`
    - `ctypes`
    - `glm`
    - `numpy`

2. **Run the game**:
    ```bash
    python3 game.py
    ```

3. **Troubleshooting**:
    - If the game fails to run, check that all dependencies are installed and their paths are properly set in your environment variables.
    - SDL-related libraries may require additional setup depending on your operating system.

---

## License

This project is licensed under the [MIT License](LICENSE).
