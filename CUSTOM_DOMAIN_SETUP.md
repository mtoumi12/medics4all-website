# Custom Domain Deployment Guide for medics4all.com

## ✅ COMPLETED: CNAME File Added to Repository

## 🔧 STEP 1: Configure DNS Settings (REQUIRED)

Where did you buy your domain `medics4all.com` from? (e.g., GoDaddy, Namecheap, Google Domains, etc.)

### DNS Configuration Required:
You need to add these DNS records in your domain registrar's control panel:

**Option A: Using CNAME (Recommended)**
```
Type: CNAME
Name: www
Value: mtoumi12.github.io
TTL: 3600 (or Auto)

Type: A (for apex domain)
Name: @ (or blank)
Value: 185.199.108.153
TTL: 3600

Type: A 
Name: @ (or blank)
Value: 185.199.109.153
TTL: 3600

Type: A
Name: @ (or blank) 
Value: 185.199.110.153
TTL: 3600

Type: A
Name: @ (or blank)
Value: 185.199.111.153
TTL: 3600
```

## 🔧 STEP 2: Configure GitHub Pages Custom Domain

1. Go to: https://github.com/mtoumi12/medics4all-website/settings/pages
2. In the "Custom domain" field, enter: `medics4all.com`
3. Click "Save"
4. Wait for DNS check to pass (may take a few minutes)
5. Once verified, check "Enforce HTTPS"

## 🔧 STEP 3: Wait for Propagation
- DNS changes can take 24-48 hours to fully propagate
- You can test with: `nslookup medics4all.com`

## 🎯 Final Result:
- Your website will be accessible at: https://medics4all.com
- And also at: https://www.medics4all.com

---

## 📝 DOMAIN REGISTRAR SPECIFIC GUIDES:

### GoDaddy:
1. Go to GoDaddy DNS Management
2. Add records as specified above
3. Save changes

### Namecheap:
1. Go to Domain List → Manage → Advanced DNS
2. Add records as specified above 
3. Save changes

### Google Domains:
1. Go to DNS settings
2. Add custom resource records as specified
3. Save changes

Let me know which registrar you used and I can provide more specific instructions!