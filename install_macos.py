import os
import subprocess
import sys
import shutil

def run_command(cmd, shell=True):
    print(f"[*] Executing: {cmd}")
    try:
        subprocess.check_call(cmd, shell=shell)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Error: {e}")
        return False

def install_tools():
    if sys.platform != 'darwin':
        print("[!] This script is intended for macOS.")
        return

    if not shutil.which('brew'):
        print("[!] Homebrew is not installed. Please install it first: https://brew.sh/")
        return

    print("[*] Installing security tools via Homebrew...")
    
    # Core Tools
    brew_tools = [
        "nmap", "gobuster", "nuclei", "sqlmap", "hydra", "john-jumbo", 
        "aircrack-ng", "amass", "binwalk", "bulk_extractor", "checkov",
        "dirb", "dirsearch", "dnsenum", "exiftool", "feroxbuster", "ffuf",
        "fierce", "foremost", "gdb", "hashcat", "httpx", "masscan", "medusa",
        "nikto", "prowler", "radare2", "subfinder", "trivy", "wafw00f", 
        "wfuzz", "wpscan", "sleuthkit", "exploitdb", "testdisk", "samba", "radare2",
        "steghide", "outguess", "scalpel", "bulk-extractor", "httpie"
    ]

    for tool in brew_tools:
        binary_name = tool.replace('-jumbo', '').replace('_', '-').replace('-app', '')
        if binary_name == "samba": binary_name = "rpcclient"
        if binary_name == "testdisk": binary_name = "photorec"
        
        if not shutil.which(binary_name):
            run_command(f"brew install {tool}")
        else:
            print(f"[+] {tool} is already installed.")

    # Python-based tools
    print("[*] Installing Python-based security tools...")
    pip_tools = [
        "arjun", "netexec", "pwntools", "responder", "enum4linux-ng", 
        "sherlock-project", "theharvester", "scoutsuite", "prowler",
        "trufflehog", "checkov", "shodan", "censys"
    ]
    
    for tool in pip_tools:
        run_command(f"pip3 install {tool}")

    # Special case tools that need git or specific taps
    print("[*] Installing specialized tools...")
    
    # anew
    if not shutil.which("anew"):
        run_command("brew install tomnomnom/tap/anew")
    
    # waybackurls
    if not shutil.which("waybackurls"):
        run_command("brew install tomnomnom/tap/waybackurls")

    # paramspider
    if not shutil.which("paramspider"):
        run_command("pip3 install git+https://github.com/devanshbatham/ParamSpider")

    # katana
    if not shutil.which("katana"):
        run_command("brew install projectdiscovery/tap/katana")

    # subfinder
    if not shutil.which("subfinder"):
        run_command("brew install projectdiscovery/tap/subfinder")

    # Cask tools
    print("[*] Installing GUI/Heavy tools via Homebrew Cask...")
    cask_tools = [
        "wireshark", "burp-suite", "metasploit", "postman", "owasp-zap"
    ]
    
    for tool in cask_tools:
        run_command(f"brew install --cask {tool}")

    print("[*] Creating local wordlists directory...")
    os.makedirs("wordlists", exist_ok=True)
    
    # Download some basic wordlists if they don't exist
    if not os.path.exists("wordlists/rockyou.txt"):
        print("[*] Downloading rockyou.txt...")
        run_command("curl -L https://github.com/brannondorsey/naive-hash-cat/releases/download/data/rockyou.txt -o wordlists/rockyou.txt")
    
    print("[*] Installation complete!")

if __name__ == "__main__":
    install_tools()
