#!/usr/bin/env python3
import sys
import json
from pydbus import SystemBus

def print_usage():
    print("Usage: omen <command> <subcommand> [args]")
    print("\nCommands:")
    print("  fan max             - Set fan to max speed")
    print("  fan auto            - Set fan to auto mode")
    print("  mode <profile>      - Set power profile (performance, balanced, quiet, eco)")
    print("  mux <mode>          - Set GPU mode (hybrid, discrete)")
    print("\nExamples:")
    print("  omen fan max")
    print("  omen mode performance")
    print("  omen mux discrete")

def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    bus = SystemBus()
    cmd = sys.argv[1]

    try:
        if cmd == "fan":
            if len(sys.argv) < 3:
                print("Error: fan command requires a subcommand (max, auto)")
                sys.exit(1)
            
            sub = sys.argv[2]
            if sub not in ("max", "auto"):
                print(f"Error: invalid fan subcommand '{sub}'")
                sys.exit(1)
            
            fan_svc = bus.get("com.yyl.hpmanager.fan")
            res = fan_svc.SetFanMode(sub)
            print(f"Fan mode set to {sub}: {res}")

        elif cmd == "mode":
            if len(sys.argv) < 3:
                print("Error: mode command requires a profile (performance, balanced, quiet, eco)")
                sys.exit(1)
            
            profile = sys.argv[2]
            # Map eco/quiet to what the service expects
            mapping = {
                "performance": "performance",
                "balanced": "balanced",
                "quiet": "power-saver",
                "eco": "power-saver"
            }
            target = mapping.get(profile)
            if not target:
                print(f"Error: invalid power profile '{profile}'")
                sys.exit(1)
            
            power_svc = bus.get("com.yyl.hpmanager.power")
            res = power_svc.SetPowerProfile(target)
            print(f"Power profile set to {profile}: {res}")

        elif cmd == "mux":
            if len(sys.argv) < 3:
                print("Error: mux command requires a mode (hybrid, discrete)")
                sys.exit(1)
            
            mode = sys.argv[2]
            if mode not in ("hybrid", "discrete"):
                print(f"Error: invalid mux mode '{mode}'")
                sys.exit(1)
            
            mux_svc = bus.get("com.yyl.hpmanager.mux")
            res = mux_svc.SetGpuMode(mode)
            print(f"GPU mode set to {mode}: {res}")
            if "REBOOT_REQUIRED" in res:
                print("Warning: A reboot or session restart is required for changes to take effect.")

        else:
            print(f"Error: unknown command '{cmd}'")
            print_usage()
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
