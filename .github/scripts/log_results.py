#!/usr/bin/env python3
import os
import json
import base64
from datetime import datetime


def log_results(config, health_results, dns_results):
    # Import requests here to avoid import errors when module is loaded
    import requests
    """Log results to repository"""
    if not config.get('logging', {}).get('enabled', False):
        return
    
    print("\n📝 Logging results to repository...")
    
    repo = config['logging'].get('repository')
    token = os.environ.get('GITHUB_TOKEN')
    
    if not repo or not token:
        print("❌ Missing repository or GITHUB_TOKEN for logging")
        return
    
    try:
        # Prepare log entries
        log_entries = []
        detailed_logs = []
        
        for service_name, health_result in health_results.items():
            # Find service by name in the list
            service = None
            for svc in config.get('services', []):
                if svc['name'] == service_name:
                    service = svc
                    break
            if not service:
                continue
            
            # Brief log entry
            log_entry = {
                'ts': datetime.utcnow().isoformat() + 'Z',
                'svc': service_name,
                'ok': len(health_result.get('healthy_servers', [])),
                'fail': health_result['failed_count'],
                'dns': dns_results.get(service_name, {}).get('status')
            }
            log_entries.append(log_entry)
            
            # Detailed logs for failures
            for failed_server in health_result.get('failed_server_details', []):
                detailed_logs.append({
                    'ts': datetime.utcnow().isoformat() + 'Z',
                    'type': 'failure',
                    'svc': service_name,
                    'server': failed_server.get('server'),
                    'ip': failed_server.get('ip'),
                    'error': failed_server.get('error')
                })
            
            # Detailed logs for DNS events
            if service_name in dns_results:
                dns_result = dns_results[service_name]
                if dns_result['status'] == 'mismatch' and dns_result.get('changes'):
                    detailed_logs.append({
                        'ts': datetime.utcnow().isoformat() + 'Z',
                        'type': 'dns_mismatch',
                        'svc': service_name,
                        'host': service['hostname'],
                        'current_dns': dns_result['changes'].get('previous', []),
                        'healthy_ips': dns_result['changes'].get('target', []),
                        'update_disabled': True
                    })
                elif dns_result['status'] == 'updated' and dns_result.get('changes'):
                    detailed_logs.append({
                        'ts': datetime.utcnow().isoformat() + 'Z',
                        'type': 'dns_updated',
                        'svc': service_name,
                        'host': service['hostname'],
                        'previous': dns_result['changes'].get('previous', []),
                        'current': dns_result['changes'].get('target', []),
                        'removed': dns_result['changes'].get('removed', []),
                        'added': dns_result['changes'].get('added', [])
                    })
        
        # Use daily log file
        timestamp = datetime.utcnow()
        log_filename = f"healthcheck-{timestamp.strftime('%Y%m%d')}.log"
        log_path = f"logs/{log_filename}"
        
        # Prepare log lines
        log_lines = []
        
        # Summary line (always logged)
        log_lines.append(json.dumps({
            'ts': timestamp.isoformat() + 'Z',
            'run': os.environ.get('GITHUB_RUN_ID', 'unknown'),
            'type': 'summary',
            'data': log_entries
        }, separators=(',', ':')))
        
        # Detailed lines (only for failures/issues)
        for detail in detailed_logs:
            log_lines.append(json.dumps(detail, separators=(',', ':')))
        
        # Join all lines
        log_content = '\n'.join(log_lines) + '\n'
        
        # GitHub API headers
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # First check if directory exists
        dir_path = "logs"
        dir_api_url = f"https://api.github.com/repos/{repo}/contents/{dir_path}"
        dir_check = requests.get(dir_api_url, headers=headers)
        
        # If directory doesn't exist, create a .gitkeep file to establish it
        if dir_check.status_code == 404:
            gitkeep_content = base64.b64encode(b"").decode()
            gitkeep_data = {
                'message': 'Create logs directory',
                'content': gitkeep_content,
                'branch': 'main'
            }
            gitkeep_url = f"https://api.github.com/repos/{repo}/contents/{dir_path}/.gitkeep"
            create_response = requests.put(gitkeep_url, headers=headers, json=gitkeep_data)
            if create_response.status_code not in [200, 201]:
                print(f"   ⚠️  Failed to create directory: {create_response.status_code} - {create_response.text}")
        
        # Get current file if it exists
        api_url = f"https://api.github.com/repos/{repo}/contents/{log_path}"
        existing_file = requests.get(api_url, headers=headers)
        
        # Prepare content
        if existing_file.status_code == 200:
            # File exists, append to it
            existing_content = base64.b64decode(existing_file.json()['content']).decode()
            new_content = existing_content + log_content
            content = base64.b64encode(new_content.encode()).decode()
            sha = existing_file.json()['sha']
        else:
            # New file
            content = base64.b64encode(log_content.encode()).decode()
            sha = None
        
        # Create or update file
        data = {
            'message': f'Log healthcheck - {timestamp.strftime("%Y-%m-%d %H:%M:%S")} UTC',
            'content': content,
            'branch': 'main'
        }
        
        if sha:
            data['sha'] = sha
        
        # Push the file
        response = requests.put(api_url, headers=headers, json=data)
        
        if response.status_code in [200, 201]:
            print(f"✅ Logged results to {log_path}")
            print(f"   View at: https://github.com/{repo}/blob/main/{log_path}")
        else:
            print(f"❌ Failed to log results: {response.status_code} - {response.text}")
            print(f"   API URL: {api_url}")
            print(f"   Repository: {repo}")
            
    except Exception as e:
        print(f"❌ Error logging results: {str(e)}")


if __name__ == "__main__":
    import sys
    
    # Read config
    with open('.github/ha-monitor-config.json', 'r') as f:
        config = json.load(f)
    
    # Read results from stdin
    data = json.loads(sys.stdin.read())
    health_results = data['health_results']
    dns_results = data['dns_results']
    
    # Log results
    log_results(config, health_results, dns_results)