# Tool Usage Guide

## Username Investigation

### Maigret
```bash
python -m maigret username
```

### Sherlock
```bash
python sherlock.py username --timeout 10
```

## Email Investigation

### Holehe
```bash
holehe email@example.com
```

### HaveIBeenPwned
```bash
curl -s https://haveibeenpwned.com/api/v3/breachedaccount/test@test.com
```

## Automation & Recon

### SpiderFoot
```bash
python -m sf -s target.com
```

### recon-ng
```bash
recon-ng
```

## Social Media

### snscrape
```bash
snscrape twitter-user username
```

## Infrastructure

### Shodan
```bash
shodan host 1.1.1.1
shodan search "apache"
```