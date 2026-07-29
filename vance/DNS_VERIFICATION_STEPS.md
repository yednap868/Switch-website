# DNS Configuration Verification for api.relayy.world

## ✅ DNS Status (From GoDaddy)

**Current DNS Records:**
- `api.relayy.world` → A record → `34.30.52.249` ✅

This is **correct** - the DNS is pointing to the right IP.

## ⚠️ Next Steps: Verify Server Configuration

Since DNS is correct but the domain is still unreachable, the issue is on the **server side**.

### Step 1: Verify IP Address

On your GCP instance (`relay-backend`), check if `34.30.52.249` is the correct external IP:

```bash
curl -s ifconfig.me
# OR
curl -s https://api.ipify.org
```

**Expected:** Should return `34.30.52.249` (or confirm it matches your GCP instance's external IP)

### Step 2: Check if Server is Listening

On the server, verify uvicorn is running and accessible:

```bash
# Check if process is running
ps aux | grep uvicorn

# Test locally
curl -s http://127.0.0.1:8000/api/docs | head

# Test from external IP (should work if firewall allows)
curl -s http://34.30.52.249:8000/api/docs | head
```

### Step 3: Check NGINX Configuration (if using)

If you're using NGINX as a reverse proxy, check:

```bash
# Check if NGINX is installed and running
sudo systemctl status nginx

# Check NGINX config
sudo cat /etc/nginx/sites-available/api.relayy.world
# OR
sudo cat /etc/nginx/sites-enabled/api.relayy.world

# Test NGINX config
sudo nginx -t
```

**Required NGINX config for api.relayy.world:**

```nginx
server {
    listen 80;
    listen 443 ssl;
    server_name api.relayy.world;

    # SSL configuration (if using Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.relayy.world/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.relayy.world/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Step 4: Check Firewall Rules (GCP)

On Google Cloud Platform:

1. Go to **VPC Network → Firewall Rules**
2. Ensure there's a rule allowing:
   - **Ingress** on port **80** (HTTP)
   - **Ingress** on port **443** (HTTPS)
   - Source: `0.0.0.0/0` (all IPs)

### Step 5: Test from Your Laptop

After verifying above, test from your laptop:

```bash
# Test DNS resolution
nslookup api.relayy.world
# Should return: 34.30.52.249

# Test HTTP (if NGINX redirects to HTTPS, you'll get a redirect)
curl -I http://api.relayy.world/api/docs

# Test HTTPS
curl -I https://api.relayy.world/api/docs

# Test OTP endpoint
curl -s -X POST https://api.relayy.world/api/candidate-onboarding/signup \
  -H "Content-Type: application/json" \
  -d '{"country_code":"91","phone":"8368828660"}'
```

### Step 6: Check SSL Certificate (if using HTTPS)

If you need HTTPS (recommended):

```bash
# Install certbot if not installed
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d api.relayy.world

# Auto-renewal
sudo certbot renew --dry-run
```

## 🎯 Quick Fix Checklist

- [ ] Verify `34.30.52.249` is the correct GCP instance IP
- [ ] Check GCP firewall allows ports 80 and 443
- [ ] Install/configure NGINX to forward api.relayy.world → localhost:8000
- [ ] Set up SSL certificate (Let's Encrypt)
- [ ] Test from browser: `https://api.relayy.world/api/docs`
- [ ] Test OTP endpoint from browser/curl

## 📝 Current Status

- ✅ **DNS:** Correctly configured in GoDaddy
- ❓ **Server:** Need to verify NGINX/proxy configuration
- ❓ **Firewall:** Need to verify GCP firewall rules
- ❓ **SSL:** Need to verify HTTPS certificate

Once all above are verified, `https://api.relayy.world` will be reachable and OTP will work end-to-end.
