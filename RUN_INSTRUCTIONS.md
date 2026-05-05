# Running HospitalIQ

To run the application efficiently and prevent system hangs, use a 3-terminal setup. This allows you to monitor the frontend and backend logs independently, and leaves one terminal free for other commands.

## Open 3 Terminals in VS Code (or your preferred terminal)

**Terminal 1: Backend Server**
1. Run the backend startup script:
   ```cmd
   .\start_backend.bat
   ```
2. Leave this terminal running. It will start the Python backend API on `http://localhost:8000`.

**Terminal 2: Frontend Server**
1. Run the frontend startup script:
   ```cmd
   .\start_frontend.bat
   ```
2. Leave this terminal running. It will start the Next.js frontend on `http://localhost:3000`.

**Terminal 3: Free Terminal**
1. Use this terminal for Git commands, AI interactions, running tests, or installing new packages.

---

### Troubleshooting
- If either script crashes, the terminal window will stay open (due to the `pause` command) so you can read the error message.
- You can stop either server by pressing `Ctrl + C` in its respective terminal.
