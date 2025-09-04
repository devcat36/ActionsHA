# ActionsHA - Automatic High Availability for Your Services

**Zero-infrastructure high availability monitoring and automatic failover powered by GitHub Actions**

## 🚀 Why ActionsHA?

ActionsHA provides high availability without the complexity or cost:

- **Zero Infrastructure Required** - No monitoring servers, databases, or third-party services needed
- **Automatic Failover** - Instantly removes unhealthy servers from DNS when they fail
- **Free Forever(ish)** - Runs entirely on GitHub Actions free tier (up to 2000 minutes/month)
- **Self-Healing** - Automatically re-adds servers to DNS when they recover
- **Dynamic IP Support** - Handles servers with changing IPs (home labs, dynamic DNS)
- **Real-time Dashboard** - Auto-updating status dashboard in your repository

## 📊 What You Get

- **Configurable health checks** (default 5 minutes) across all your servers
- **Automatic DNS updates** via Cloudflare when servers fail/recover  
- **Visual dashboard** showing service health at a glance
- **Historical logs** of all health checks and DNS changes
- **Automatic IP updates** when your servers' IPs change
- **TCP port monitoring** for non-HTTP services

## 🔧 Quick Start

### Step 1: Create Your Repository

For a **private repository** (recommended to keep your server IPs private):
1. Clone this repository locally: `git clone https://github.com/devcat36/ActionsHA.git`
2. Create a new private repository on your GitHub account
3. Push the code to your new private repository

For a public repository:
- Simply fork this repository to your GitHub account

### Step 2: Add Your Cloudflare API Token

1. Go to your forked repo's Settings → Secrets and variables → Actions
2. Add a new repository secret called `CLOUDFLARE_API_TOKEN`
3. Get your token from [Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens) with these permissions:
   - Zone:DNS:Edit
   - Zone:Zone:Read

### Step 3: Configure Your Services

Edit `.github/ha-monitor-config.json` in your repository. Here's the complete structure:

```json
{
  "logging": {
    "enabled": true,                           // Enable logging to repository
    "repository": "yourusername/yourrepo"      // Your GitHub repository path
  },
  "cloudflare": {
    "enabled": true,                           // Enable Cloudflare DNS updates
    "api_token": "${{ secrets.CLOUDFLARE_API_TOKEN }}"  // NEVER put actual token here, use GitHub secrets
  },
  "servers": [
    {
      "name": "server-01",                     // Unique server identifier
      "ip": "1.2.3.4"                         // Server's IP address (updated automatically if using DDNS)
    },
    {
      "name": "server-02",
      "ip": "5.6.7.8"
    }
  ],
  "services": [
    {
      "name": "my-api",                       // Service identifier
      "hostname": "api.example.com",          // Domain to manage
      "port": 8080,                           // Port (optional, defaults to 80/443)
      "scheme": "https",                      // Protocol: http or https (optional)
      "healthcheck_path": "/health",          // Path for HTTP check (optional, omit for TCP-only)
      "servers": ["server-01", "server-02"],  // Servers running this service
      "cloudflare": {
        "update_dns": true,                   // Enable automatic DNS failover
        "zone_id": "your_cloudflare_zone_id", // Find in Cloudflare dashboard
        "proxied": true,                      // Use Cloudflare proxy (orange cloud)
        "ttl": 120                            // TTL in seconds (120 = Auto)
      }
    }
  ]
}
```

### Step 4: Enable GitHub Actions

1. Go to the Actions tab in your repository and enable workflows.
2. Enable Actions HA workflow. The monitoring will start automatically according to cron schedule (default every 5 minutes).
3. Run the Actions HA workflow manually to test if your configuraions are properly set.

> **Note**: GitHub Actions' cron scheduler may have delays during peak times. For more consistent timing, you can use external cron services like cron-job.org to trigger your workflows.

## 📖 Configuration Reference

### Complete Configuration Example

Here's a full example with multiple services showing all available options:

```json
{
  "logging": {
    "enabled": true,
    "repository": "yourusername/ActionsHA"
  },
  "cloudflare": {
    "enabled": true,
    "api_token": "${{ secrets.CLOUDFLARE_API_TOKEN }}"
  },
  "servers": [
    {
      "name": "vps-primary",
      "ip": "192.0.2.1"
    },
    {
      "name": "vps-backup",
      "ip": "203.0.113.5"
    },
    {
      "name": "home-server",
      "ip": "198.51.100.42"
    }
  ],
  "services": [
    {
      "name": "website",
      "hostname": "www.example.com",
      "scheme": "https",
      "healthcheck_path": "/",              // HTTP health check
      "servers": ["vps-primary", "vps-backup"],
      "cloudflare": {
        "update_dns": true,
        "zone_id": "abc123def456",
        "proxied": true,
        "ttl": 120
      }
    },
    {
      "name": "api",
      "hostname": "api.example.com",
      "port": 3000,                         // Custom port
      "scheme": "http",
      "healthcheck_path": "/api/health",
      "servers": ["vps-primary", "vps-backup", "home-server"],
      "cloudflare": {
        "update_dns": true,
        "zone_id": "abc123def456",
        "proxied": false,                   // Direct connection (gray cloud)
        "ttl": 300
      }
    },
    {
      "name": "database",
      "hostname": "db.example.com",
      "port": 5432,                         // PostgreSQL port
      // No healthcheck_path = TCP port check only
      "servers": ["vps-primary", "vps-backup"],
      "cloudflare": {
        "update_dns": true,
        "zone_id": "abc123def456",
        "proxied": false,
        "ttl": 120
      }
    }
  ]
}
```

### Configuration Field Reference

| Field | Required | Description | Default |
|-------|----------|-------------|---------|
| **logging.enabled** | Yes | Enable result logging | - |
| **logging.repository** | Yes | GitHub repository (user/repo) | - |
| **cloudflare.enabled** | Yes | Enable DNS updates | - |
| **cloudflare.api_token** | Yes | GitHub secret reference (always use `${{ secrets.CLOUDFLARE_API_TOKEN }}`) | - |
| **servers[].name** | Yes | Unique server identifier | - |
| **servers[].ip** | Yes | Server IP address | - |
| **services[].name** | Yes | Service identifier | - |
| **services[].hostname** | Yes | Domain name to manage | - |
| **services[].port** | No | Port number | 80 (http) or 443 (https) |
| **services[].scheme** | No | Protocol (http/https) | http |
| **services[].healthcheck_path** | No | HTTP endpoint to check | None (TCP check only) |
| **services[].servers** | Yes | List of server names | - |
| **services[].cloudflare.update_dns** | Yes | Enable DNS failover | - |
| **services[].cloudflare.zone_id** | Yes | Cloudflare zone ID | - |
| **services[].cloudflare.proxied** | No | Use Cloudflare proxy | true |
| **services[].cloudflare.ttl** | No | DNS TTL in seconds | 120 |

### Finding Your Cloudflare Zone ID

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select your domain
3. On the Overview page, scroll down to the API section
4. Copy the Zone ID

## 🔄 Automatic IP Updates (Optional)

If your servers have dynamic IPs (home lab, residential internet), deploy the DDNS reporter:

### On Your Server

1. Clone this repository to your server
2. Navigate to the `ddns-reporter` directory
3. Create a `.env` file:

```bash
GITHUB_TOKEN=your_github_pat_token
GITHUB_OWNER=yourusername
GITHUB_REPO=ActionsHA
SERVER_NAME=server-01
CHECK_INTERVAL=300
```

4. Run the container:

```bash
docker-compose up -d
```

The reporter will automatically update your server's IP in the configuration whenever it changes.

## 📈 How It Works

1. **Scheduled checks** run at your configured interval (default every 5 minutes)
2. **For each service**, it checks the health endpoint on all configured servers
3. **If a server fails**, it's immediately removed from Cloudflare DNS
4. **If a server recovers**, it's automatically added back to DNS
5. **Dashboard updates** show current status of all services
6. **Logs are saved** for historical tracking and debugging

## 📊 Monitoring Dashboard

After your first workflow run, check your repository's README for a live dashboard showing:

- Overall service health
- Individual server status
- Recent failover events
- DNS sync status
- Historical uptime

[View Example Dashboard](https://github.com/devcat36/ActionsHA/blob/main/example_dashboard.md)

## 🔍 Viewing Logs

All health checks and DNS updates are logged to the `logs/` directory in your repository:

- `logs/YYYY-MM-DD/` - Daily log directories
- Each run creates a detailed JSON log file
- Track patterns and debug issues

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## 📄 License

This project is open source and available under the MIT License.

## ⚠️ Disclaimer

This software is provided "as is", without warranty of any kind, express or implied. The author is not responsible for any damages, data loss, downtime, or other issues that may arise from using this code. Use at your own risk.

---

**Start monitoring in under 5 minutes** - Fork this repo and add your configuration!
