#!/usr/bin/env python3
import subprocess
import json


def check_service_health(service, servers):
    """Check health of all servers for a service"""
    print(f"📁 {service['name']}")
    print(f"   Hostname: {service['hostname']}")
    
    # Check if healthcheck_path is specified
    healthcheck_path = service.get('healthcheck_path')
    if healthcheck_path:
        print(f"   Endpoint: {service['scheme']}://{service['hostname']}{healthcheck_path}")
    else:
        port = str(service.get('port', '443' if service.get('scheme') == 'https' else '80'))
        print(f"   TCP Port Check: {service['hostname']}:{port}")
    print()
    
    failed_count = 0
    total_count = 0
    healthy_servers = []
    failed_server_details = []
    
    # Resolve server references by matching name field
    service_servers = []
    for server_name in service.get('servers', []):
        server_found = False
        for server in servers:
            if server['name'] == server_name:
                service_servers.append(server)
                server_found = True
                break
        if not server_found:
            print(f"   ⚠️ Warning: Server '{server_name}' not found in server definitions")
    
    for server in service_servers:
        total_count += 1
        ip = server['ip']
        server_name = server['name']
        
        # Use port from config, or default based on scheme
        if 'port' in service:
            port = str(service['port'])
        else:
            port = '443' if service.get('scheme') == 'https' else '80'
        
        print(f"   {server_name} ({ip}) - ", end='', flush=True)
        
        if healthcheck_path:
            # HTTP/HTTPS health check
            url = f"{service['scheme']}://{service['hostname']}{healthcheck_path}"
            
            # Perform healthcheck using --resolve
            cmd = [
                'curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                '--resolve', f"{service['hostname']}:{port}:{ip}",
                '-X', 'GET', url,
                '--max-time', '10'
            ]
            
            # Add --insecure only for https
            if service.get('scheme') == 'https':
                cmd.append('--insecure')
            
            try:
                response = subprocess.run(cmd, capture_output=True, text=True)
                status_code = response.stdout.strip()
                
                if response.returncode != 0:
                    error_detail = response.stderr or "Connection failed"
                    print(f"❌ Failed ({error_detail})")
                    failed_count += 1
                    failed_server_details.append({'server': server_name, 'ip': ip, 'error': error_detail})
                elif status_code == '200':
                    print(f"✅ Healthy (HTTP {status_code})")
                    healthy_servers.append(server_name)
                else:
                    print(f"❌ Failed (HTTP {status_code})")
                    failed_count += 1
                    failed_server_details.append({'server': server_name, 'ip': ip, 'error': f'HTTP {status_code}'})
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                failed_count += 1
                failed_server_details.append({'server': server_name, 'ip': ip, 'error': str(e)})
        else:
            # TCP port check only
            import socket
            import time
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                start_time = time.time()
                result = sock.connect_ex((ip, int(port)))
                response_time = time.time() - start_time
                sock.close()
                
                if result == 0:
                    print(f"✅ Port {port} open ({response_time:.2f}s)")
                    healthy_servers.append(server_name)
                else:
                    print(f"❌ Port {port} closed or unreachable")
                    failed_count += 1
                    failed_server_details.append({'server': server_name, 'ip': ip, 'error': f'Port {port} closed'})
            except socket.timeout:
                print(f"❌ Connection timeout")
                failed_count += 1
                failed_server_details.append({'server': server_name, 'ip': ip, 'error': 'Connection timeout'})
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                failed_count += 1
                failed_server_details.append({'server': server_name, 'ip': ip, 'error': str(e)})
    
    print()
    print(f"Summary for {service['name']}: {total_count - failed_count}/{total_count} healthy")
    
    return {
        'healthy_servers': healthy_servers,
        'failed_count': failed_count,
        'total_count': total_count,
        'failed_server_details': failed_server_details
    }


if __name__ == "__main__":
    # Read config
    with open('.github/ha-monitor-config.json', 'r') as f:
        config = json.load(f)
    
    # Process all services
    results = {}
    servers = config.get('servers', [])
    for service in config.get('services', []):
        service_name = service['name']
        results[service_name] = check_service_health(service, servers)
        print("\n" + "="*60 + "\n")
    
    # Output results as JSON for other scripts
    print(json.dumps(results))