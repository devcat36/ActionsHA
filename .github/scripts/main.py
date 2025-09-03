#!/usr/bin/env python3
import json
import subprocess
import sys
import os


def main():
    """Main orchestrator for HA Monitor"""
    # Read config
    with open('.github/ha-monitor-config.json', 'r') as f:
        config = json.load(f)
    
    # Step 1: Health checks
    print("=== Running Health Checks ===\n")
    health_process = subprocess.run(
        ['python3', '.github/scripts/healthcheck.py'],
        capture_output=True,
        text=True
    )
    
    # Extract JSON from output (last line)
    health_output_lines = health_process.stdout.strip().split('\n')
    
    # Debug: Check if we have output
    if not health_output_lines or len(health_output_lines) == 0:
        print("ERROR: No output from health check script")
        sys.exit(1)
    
    try:
        health_results = json.loads(health_output_lines[-1])
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse health check JSON: {e}")
        print(f"Last line was: {health_output_lines[-1]}")
        sys.exit(1)
    
    # Print health check output (except JSON line)
    for line in health_output_lines[:-1]:
        print(line)
    
    # Step 2: DNS updates
    print("\n=== Checking/Updating DNS ===")
    dns_process = subprocess.run(
        ['python3', '.github/scripts/dns_update.py'],
        input=json.dumps(health_results),
        capture_output=True,
        text=True
    )
    
    if dns_process.returncode != 0:
        print(f"DNS update script failed with error:\n{dns_process.stderr}")
        sys.exit(1)
    
    # Extract JSON from output (last line if exists)
    dns_output_lines = dns_process.stdout.strip().split('\n') if dns_process.stdout else []
    dns_results = {}
    if dns_output_lines and dns_output_lines[-1].startswith('{'):
        dns_results = json.loads(dns_output_lines[-1])
        # Print DNS output (except JSON line)
        for line in dns_output_lines[:-1]:
            print(line)
    else:
        # No JSON output, print everything
        for line in dns_output_lines:
            print(line)
    
    # Combine results for logging and dashboard
    combined_results = {
        'health_results': health_results,
        'dns_results': dns_results
    }
    
    # Step 3: Logging
    if config.get('logging', {}).get('enabled', False):
        logging_process = subprocess.run(
            ['python3', '.github/scripts/log_results.py'],
            input=json.dumps(combined_results),
            capture_output=True,
            text=True
        )
        if logging_process.returncode != 0:
            print(f"Logging script failed with error:\n{logging_process.stderr}")
            sys.exit(1)
        print(logging_process.stdout)
    
    # Step 4: Dashboard generation
    print("\n=== Generating Dashboard ===")
    dashboard_process = subprocess.run(
        ['python3', '.github/scripts/dashboard.py'],
        input=json.dumps(combined_results),
        capture_output=True,
        text=True
    )
    if dashboard_process.returncode != 0:
        print(f"Dashboard script failed with error:\n{dashboard_process.stderr}")
        sys.exit(1)
    print(dashboard_process.stdout)
    
    # Check if any health checks failed
    any_failed = any(result['failed_count'] > 0 for result in health_results.values())
    
    # Check for no healthy IPs warnings
    for service_name, result in health_results.items():
        # Find service by name in the list
        service = None
        for svc in config.get('services', []):
            if svc['name'] == service_name:
                service = svc
                break
        if service and not result.get('healthy_servers', []) and service.get('cloudflare', {}).get('update_dns', False):
            print(f"::warning title=No Healthy Servers::Service {service_name} has no healthy servers but DNS updates are enabled")
    
    # Exit with error if any health checks failed
    if any_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()