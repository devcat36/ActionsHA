#!/usr/bin/env python3
import os
import json


def update_dns_for_service(service, healthy_servers, config):
    # Import requests here to avoid import errors when module is loaded
    import requests
    """Check and update DNS records for a service"""
    cf_config = service.get('cloudflare', {})
    if not cf_config.get('zone_id') or not config.get('cloudflare', {}).get('enabled', False):
        return None
    
    should_update = cf_config.get('update_dns', False)
    
    print()
    if should_update:
        print("🔄 Checking and updating Cloudflare DNS...")
    else:
        print("🔍 Checking Cloudflare DNS state (updates disabled)...")
    
    api_token = os.environ.get('CLOUDFLARE_API_TOKEN')
    zone_id = cf_config['zone_id']
    hostname = service['hostname']
    
    if not api_token:
        print("❌ No Cloudflare API token found")
        return None
    
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    }
    
    # Convert healthy server names to IPs
    servers_list = config.get('servers', [])
    healthy_ips = []
    for server_name in healthy_servers:
        for server in servers_list:
            if server['name'] == server_name:
                healthy_ips.append(server['ip'])
                break
    
    # Get existing A records
    response = requests.get(
        f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records',
        headers=headers,
        params={'type': 'A', 'name': hostname}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch DNS records: {response.text}")
        return None
    
    existing_records = response.json()['result']
    existing_ips = {record['content']: record['id'] for record in existing_records}
    
    # Check if DNS state matches healthy IPs
    dns_ips = set(existing_ips.keys())
    healthy_set = set(healthy_ips)
    
    dns_changes = {}
    dns_status = 'ok'
    
    if dns_ips != healthy_set:
        print(f"   ⚠️  WARNING: DNS state mismatch detected!")
        print(f"      Current DNS IPs: {', '.join(sorted(dns_ips)) if dns_ips else 'None'}")
        print(f"      Healthy IPs: {', '.join(sorted(healthy_set)) if healthy_set else 'None'}")
        
        # Show what needs to change
        to_remove = dns_ips - healthy_set
        to_add = healthy_set - dns_ips
        
        if to_remove:
            print(f"      IPs to remove: {', '.join(sorted(to_remove))}")
        if to_add:
            print(f"      IPs to add: {', '.join(sorted(to_add))}")
        
        # Store DNS change details
        dns_changes = {
            'previous': sorted(dns_ips),
            'target': sorted(healthy_set),
            'removed': sorted(to_remove),
            'added': sorted(to_add)
        }
        
        # GitHub Actions workflow warning
        warning_msg = f"DNS mismatch for {hostname}: Current [{', '.join(sorted(dns_ips))}] != Healthy [{', '.join(sorted(healthy_set))}]"
        print(f"::warning title=DNS State Mismatch::{warning_msg}")
        
        dns_status = 'mismatch'
    else:
        print(f"   ✅ DNS state already matches healthy IPs: {', '.join(sorted(dns_ips))}")
    
    # Only perform updates if enabled
    if should_update and dns_ips != healthy_set:
        # Delete records for unhealthy IPs
        for ip, record_id in existing_ips.items():
            if ip not in healthy_ips:
                delete_response = requests.delete(
                    f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}',
                    headers=headers
                )
                if delete_response.status_code == 200:
                    print(f"   ➖ Removed unhealthy IP: {ip}")
                else:
                    print(f"   ❌ Failed to remove {ip}: {delete_response.text}")
        
        # Add records for new healthy IPs
        for ip in healthy_ips:
            if ip not in existing_ips:
                create_response = requests.post(
                    f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records',
                    headers=headers,
                    json={
                        'type': 'A',
                        'name': hostname,
                        'content': ip,
                        'ttl': cf_config.get('ttl', 120),
                        'proxied': cf_config.get('proxied', False)
                    }
                )
                if create_response.status_code == 200:
                    print(f"   ➕ Added healthy IP: {ip}")
                else:
                    print(f"   ❌ Failed to add {ip}: {create_response.text}")
        
        print("✅ DNS update complete!")
        dns_status = 'updated'
    elif not should_update and dns_ips != healthy_set:
        print("   ⚠️  DNS updates are disabled for this service. Enable 'update_dns' to sync.")
        print(f"::warning title=DNS Updates Disabled::DNS mismatch for {hostname} but update_dns is false")
    
    return {
        'status': dns_status,
        'changes': dns_changes
    }


if __name__ == "__main__":
    import sys
    
    # Read config
    with open('.github/ha-monitor-config.json', 'r') as f:
        config = json.load(f)
    
    # Read health check results from stdin
    stdin_data = sys.stdin.read()
    if not stdin_data:
        print("ERROR: No input data received from stdin")
        sys.exit(1)
    
    try:
        health_results = json.loads(stdin_data)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON input: {e}")
        print(f"Input was: {stdin_data[:100]}...")
        sys.exit(1)
    
    # Process DNS updates
    dns_results = {}
    for service in config.get('services', []):
        service_name = service['name']
        if service_name in health_results:
            healthy_servers = health_results[service_name].get('healthy_servers', [])
            dns_result = update_dns_for_service(service, healthy_servers, config)
            if dns_result:
                dns_results[service_name] = dns_result
            print("\n" + "="*60 + "\n")
    
    # Output results
    print(json.dumps(dns_results))