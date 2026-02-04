CrowdLumen: Modular Crowd Safety Intelligence System
==================================================

CrowdLumen is a privacy-first, modular system designed for real-time crowd safety monitoring.
It consists of two completely independent modules that run on separate hardware (or separate terminals).

SYSTEM ARCHITECTURE:
--------------------
1. Audio Intelligence Module
   - Listens to ambient sound via microphone.
   - Analzyes loudness (RMS) and stability (Variance).
   - Detects panic screams, sudden crashes, or sustained chaos.
   - Privacy: No audio is recorded or stored. Analysis is purely numeric and live.

2. Visual Intelligence Module
   - Monitors video feed via webcam.
   - Analyzes crowd motion intensity and flow stability.
   - Detects stampedes, sudden dashes, or chaotic movement.
   - Privacy: No face detection or recognition. Analyzes global motion patterns only.

INSTRUCTIONS:
-------------
1. Navigate to 'Audio_Intelligence/' and follow the README.txt to start the Audio Monitor.
2. Navigate to 'Visual_Intelligence/' and follow the README.txt to start the Visual Monitor.
3. Observe the live status outputs on each module's display.

DEMO NOTES:
-----------
- The system is designed for a dual-laptop setup.
- Ensure dependency libraries are installed in each folder before running.
