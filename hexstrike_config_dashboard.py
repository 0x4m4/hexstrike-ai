import http.server
import socketserver
import json
import os
import webbrowser
import sys
from urllib.parse import urlparse, parse_qs

PORT = 8080
CONFIG_FILE = "mcp_tool_config.json"
CATEGORIES_FILE = "tool_categories.json"
PROFILES_FILE = "profiles.json"

class ConfigHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.get_html_content().encode("utf-8"))
        elif parsed_path.path == "/api/config":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            config = self.load_json(CONFIG_FILE, {"enabled_tools": []})
            categories = self.load_json(CATEGORIES_FILE, {})
            profiles = self.load_json(PROFILES_FILE, {"profiles": {}})
            response_data = {
                "config": config,
                "categories": categories,
                "profiles": profiles
            }
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
        else:
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode("utf-8"))
            
            if self.path == "/api/config":
                self.save_json(CONFIG_FILE, data)
                self.send_json_response({"status": "success", "message": "Configuration saved"})
                
            elif self.path == "/api/profiles":
                # Save a new profile or update existing
                profiles_data = self.load_json(PROFILES_FILE, {"profiles": {}})
                profile_name = data.get("name")
                tools = data.get("tools")
                
                if profile_name and tools:
                    profiles_data["profiles"][profile_name] = tools
                    self.save_json(PROFILES_FILE, profiles_data)
                    self.send_json_response({"status": "success", "message": f"Profile '{profile_name}' saved"})
                else:
                    self.send_error(400, "Missing name or tools")

            elif self.path == "/api/profiles/apply":
                # Apply a profile to the main config
                profile_name = data.get("name")
                profiles_data = self.load_json(PROFILES_FILE, {"profiles": {}})
                
                if profile_name in profiles_data["profiles"]:
                    new_config = {"enabled_tools": profiles_data["profiles"][profile_name]}
                    self.save_json(CONFIG_FILE, new_config)
                    self.send_json_response({"status": "success", "message": f"Profile '{profile_name}' applied"})
                else:
                    self.send_error(404, "Profile not found")
            
            elif self.path == "/api/profiles/delete":
                profile_name = data.get("name")
                profiles_data = self.load_json(PROFILES_FILE, {"profiles": {}})
                
                if profile_name in profiles_data["profiles"]:
                    del profiles_data["profiles"][profile_name]
                    self.save_json(PROFILES_FILE, profiles_data)
                    self.send_json_response({"status": "success", "message": f"Profile '{profile_name}' deleted"})
                else:
                    self.send_error(404, "Profile not found")

            else:
                self.send_error(404)
                
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def load_json(self, filename, default):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return default

    def save_json(self, filename, data):
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

    def get_html_content(self):
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HEXSTRIKE // COMMAND CENTER</title>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;600&family=Orbitron:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #050505;
            --panel-bg: #0a0a0a;
            --border-color: #1a1a1a;
            --text-primary: #e0e0e0;
            --text-secondary: #808080;
            
            /* Cyberpunk Palette */
            --neon-green: #00ff41;
            --neon-blue: #00f3ff;
            --neon-red: #ff003c;
            --matrix-green: #0d0;
            
            --accent: var(--neon-green);
            --glow: 0 0 10px rgba(0, 255, 65, 0.3);
        }

        * { box-sizing: border-box; }

        body {
            font-family: 'Fira Code', monospace;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 0;
            height: 100vh;
            display: flex;
            overflow: hidden;
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg-color); }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--accent); }

        /* Sidebar */
        .sidebar {
            width: 300px;
            background-color: var(--panel-bg);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            padding: 20px;
            z-index: 10;
        }

        .brand {
            font-family: 'Orbitron', sans-serif;
            font-size: 24px;
            color: var(--accent);
            text-shadow: var(--glow);
            margin-bottom: 30px;
            letter-spacing: 2px;
            text-align: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 20px;
        }

        .profile-section {
            flex: 1;
            overflow-y: auto;
        }

        .section-title {
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
        }
        .section-title::after {
            content: '';
            flex: 1;
            height: 1px;
            background: var(--border-color);
            margin-left: 10px;
        }

        .profile-item {
            padding: 12px;
            margin-bottom: 8px;
            background: rgba(255,255,255,0.03);
            border: 1px solid transparent;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .profile-item:hover {
            border-color: var(--accent);
            background: rgba(0, 255, 65, 0.05);
            box-shadow: var(--glow);
        }
        .profile-item.active {
            border-color: var(--accent);
            background: rgba(0, 255, 65, 0.1);
        }
        .profile-name { font-weight: 600; }
        .profile-count { font-size: 11px; color: var(--text-secondary); }

        .profile-actions {
            margin-top: 20px;
            display: flex;
            gap: 10px;
        }

        /* Main Content */
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
        }

        /* Scanline Effect */
        .main::before {
            content: " ";
            display: block;
            position: absolute;
            top: 0; left: 0; bottom: 0; right: 0;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
            z-index: 2;
            background-size: 100% 2px, 3px 100%;
            pointer-events: none;
        }

        .header {
            padding: 20px 30px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(10, 10, 10, 0.95);
        }

        .stats-bar {
            display: flex;
            gap: 20px;
            font-size: 14px;
        }
        .stat {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .stat-value { color: var(--accent); font-weight: bold; }

        .search-container {
            position: relative;
            width: 300px;
        }
        .search-input {
            width: 100%;
            background: #000;
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 10px 15px;
            font-family: 'Fira Code', monospace;
            outline: none;
        }
        .search-input:focus {
            border-color: var(--accent);
            box-shadow: var(--glow);
        }

        .content-area {
            flex: 1;
            overflow-y: auto;
            padding: 30px;
        }

        .category-block {
            margin-bottom: 40px;
        }
        .category-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }
        .cat-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 18px;
            color: var(--neon-blue);
        }
        .cat-actions button {
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 4px 10px;
            font-size: 11px;
            cursor: pointer;
            margin-left: 5px;
        }
        .cat-actions button:hover {
            color: var(--text-primary);
            border-color: var(--text-primary);
        }

        .tools-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 15px;
        }

        .tool-card {
            background: #0f0f0f;
            border: 1px solid var(--border-color);
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
            overflow: hidden;
        }
        .tool-card:hover {
            border-color: var(--text-secondary);
            transform: translateY(-2px);
        }
        .tool-card.enabled {
            border-color: var(--accent);
            background: rgba(0, 255, 65, 0.02);
        }
        .tool-card.enabled::before {
            content: '';
            position: absolute;
            left: 0; top: 0; bottom: 0;
            width: 3px;
            background: var(--accent);
            box-shadow: var(--glow);
        }

        .tool-name { font-size: 14px; }
        .tool-status {
            font-size: 10px;
            text-transform: uppercase;
            padding: 2px 6px;
            border-radius: 2px;
            background: #222;
            color: #555;
        }
        .tool-card.enabled .tool-status {
            background: rgba(0, 255, 65, 0.1);
            color: var(--accent);
        }

        /* Buttons */
        .btn {
            background: var(--panel-bg);
            border: 1px solid var(--accent);
            color: var(--accent);
            padding: 10px 20px;
            font-family: 'Fira Code', monospace;
            font-weight: bold;
            cursor: pointer;
            text-transform: uppercase;
            transition: all 0.2s;
            letter-spacing: 1px;
        }
        .btn:hover {
            background: var(--accent);
            color: #000;
            box-shadow: var(--glow);
        }
        .btn-danger {
            border-color: var(--neon-red);
            color: var(--neon-red);
        }
        .btn-danger:hover {
            background: var(--neon-red);
            color: #fff;
            box-shadow: 0 0 10px rgba(255, 0, 60, 0.3);
        }
        .btn-small {
            padding: 6px 12px;
            font-size: 12px;
        }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 100;
            justify-content: center;
            align-items: center;
        }
        .modal-content {
            background: var(--panel-bg);
            border: 1px solid var(--accent);
            padding: 30px;
            width: 400px;
            box-shadow: var(--glow);
        }
        .modal h2 { margin-top: 0; color: var(--accent); font-family: 'Orbitron'; }
        .modal input {
            width: 100%;
            background: #000;
            border: 1px solid var(--border-color);
            color: #fff;
            padding: 10px;
            margin: 20px 0;
            font-family: 'Fira Code';
        }
        .modal-actions {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }

        /* Toast */
        .toast {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: var(--panel-bg);
            border: 1px solid var(--accent);
            color: var(--accent);
            padding: 15px 25px;
            display: flex;
            align-items: center;
            gap: 10px;
            transform: translateY(100px);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 200;
            box-shadow: var(--glow);
        }
        .toast.show { transform: translateY(0); }
        .toast-icon { font-size: 20px; }

    </style>
</head>
<body>

    <div class="sidebar">
        <div class="brand">HEXSTRIKE</div>
        
        <div class="section-title">Profiles</div>
        <div class="profile-section" id="profileList">
            <!-- Profiles injected here -->
        </div>

        <div class="profile-actions">
            <button class="btn btn-small" onclick="showSaveProfileModal()">New Profile</button>
            <button class="btn btn-small btn-danger" onclick="deleteCurrentProfile()">Delete</button>
        </div>
    </div>

    <div class="main">
        <div class="header">
            <div class="stats-bar">
                <div class="stat">
                    <span>ACTIVE TOOLS:</span>
                    <span class="stat-value" id="activeCount">0</span>
                </div>
                <div class="stat">
                    <span>TOTAL:</span>
                    <span class="stat-value" id="totalCount">0</span>
                </div>
                <div class="stat">
                    <span>STATUS:</span>
                    <span class="stat-value" style="color: var(--neon-green)">ONLINE</span>
                </div>
            </div>

            <div class="search-container">
                <input type="text" class="search-input" placeholder="SEARCH_MODULES..." onkeyup="filterTools(this.value)">
            </div>

            <button class="btn" onclick="saveConfig()">DEPLOY CONFIG</button>
        </div>

        <div class="content-area" id="content">
            <!-- Tool Categories injected here -->
        </div>
    </div>

    <!-- Save Profile Modal -->
    <div class="modal" id="saveModal">
        <div class="modal-content">
            <h2>SAVE PROFILE</h2>
            <p>Enter a name for this configuration profile:</p>
            <input type="text" id="profileNameInput" placeholder="e.g., Red Team Ops">
            <div class="modal-actions">
                <button class="btn btn-small btn-danger" onclick="closeModal()">CANCEL</button>
                <button class="btn btn-small" onclick="confirmSaveProfile()">SAVE</button>
            </div>
        </div>
    </div>

    <div class="toast" id="toast">
        <span class="toast-icon">✓</span>
        <span id="toastMsg">System Updated</span>
    </div>

    <script>
        let currentConfig = { enabled_tools: [] };
        let categories = {};
        let profiles = {};
        let currentProfileName = null;

        async function init() {
            const response = await fetch('/api/config');
            const data = await response.json();
            currentConfig = data.config;
            categories = data.categories;
            profiles = data.profiles.profiles;
            
            renderProfiles();
            renderTools();
            updateStats();
        }

        function renderProfiles() {
            const list = document.getElementById('profileList');
            list.innerHTML = '';
            
            for (const [name, tools] of Object.entries(profiles)) {
                const item = document.createElement('div');
                item.className = `profile-item ${name === currentProfileName ? 'active' : ''}`;
                item.onclick = () => loadProfile(name);
                item.innerHTML = `
                    <span class="profile-name">${name}</span>
                    <span class="profile-count">[${tools.length}]</span>
                `;
                list.appendChild(item);
            }
        }

        function renderTools() {
            const content = document.getElementById('content');
            content.innerHTML = '';
            
            for (const [category, tools] of Object.entries(categories)) {
                const block = document.createElement('div');
                block.className = 'category-block';
                
                const header = document.createElement('div');
                header.className = 'category-header';
                header.innerHTML = `
                    <span class="cat-title">${category.replace(/_/g, ' ')}</span>
                    <div class="cat-actions">
                        <button onclick="toggleCategory('${category}', true)">ALL</button>
                        <button onclick="toggleCategory('${category}', false)">NONE</button>
                    </div>
                `;
                block.appendChild(header);

                const grid = document.createElement('div');
                grid.className = 'tools-grid';

                tools.forEach(tool => {
                    const isEnabled = currentConfig.enabled_tools.includes(tool);
                    const card = document.createElement('div');
                    card.className = `tool-card ${isEnabled ? 'enabled' : ''}`;
                    card.dataset.name = tool.toLowerCase();
                    card.onclick = () => toggleTool(tool);
                    card.innerHTML = `
                        <span class="tool-name">${tool}</span>
                        <span class="tool-status">${isEnabled ? 'ACTIVE' : 'OFF'}</span>
                    `;
                    grid.appendChild(card);
                });

                block.appendChild(grid);
                content.appendChild(block);
            }
        }

        function updateStats() {
            const enabled = currentConfig.enabled_tools.length;
            let total = 0;
            Object.values(categories).forEach(t => total += t.length);
            
            document.getElementById('activeCount').innerText = enabled;
            document.getElementById('totalCount').innerText = total;
        }

        function toggleTool(tool) {
            const index = currentConfig.enabled_tools.indexOf(tool);
            if (index > -1) {
                currentConfig.enabled_tools.splice(index, 1);
            } else {
                currentConfig.enabled_tools.push(tool);
            }
            renderTools();
            updateStats();
            currentProfileName = null; // Custom state
            renderProfiles();
        }

        function toggleCategory(category, enable) {
            const tools = categories[category];
            tools.forEach(tool => {
                const index = currentConfig.enabled_tools.indexOf(tool);
                if (enable && index === -1) {
                    currentConfig.enabled_tools.push(tool);
                } else if (!enable && index > -1) {
                    currentConfig.enabled_tools.splice(index, 1);
                }
            });
            renderTools();
            updateStats();
            currentProfileName = null;
            renderProfiles();
        }

        async function loadProfile(name) {
            if (profiles[name]) {
                // Apply profile locally first
                currentConfig.enabled_tools = [...profiles[name]];
                currentProfileName = name;
                renderTools();
                renderProfiles();
                updateStats();
                
                // Apply to backend
                await fetch('/api/profiles/apply', {
                    method: 'POST',
                    body: JSON.stringify({ name: name })
                });
                showToast(`Profile loaded: ${name}`);
            }
        }

        async function saveConfig() {
            await fetch('/api/config', {
                method: 'POST',
                body: JSON.stringify(currentConfig)
            });
            showToast('Configuration Deployed');
        }

        // Modal Functions
        function showSaveProfileModal() {
            document.getElementById('saveModal').style.display = 'flex';
            document.getElementById('profileNameInput').focus();
        }

        function closeModal() {
            document.getElementById('saveModal').style.display = 'none';
        }

        async function confirmSaveProfile() {
            const name = document.getElementById('profileNameInput').value;
            if (!name) return;
            
            await fetch('/api/profiles', {
                method: 'POST',
                body: JSON.stringify({
                    name: name,
                    tools: currentConfig.enabled_tools
                })
            });
            
            // Update local state
            profiles[name] = [...currentConfig.enabled_tools];
            currentProfileName = name;
            
            closeModal();
            renderProfiles();
            showToast(`Profile saved: ${name}`);
        }

        async function deleteCurrentProfile() {
            if (!currentProfileName) return;
            
            if(confirm(`Delete profile "${currentProfileName}"?`)) {
                await fetch('/api/profiles/delete', {
                    method: 'POST',
                    body: JSON.stringify({ name: currentProfileName })
                });
                
                delete profiles[currentProfileName];
                currentProfileName = null;
                renderProfiles();
                showToast('Profile deleted');
            }
        }

        function filterTools(query) {
            const cards = document.querySelectorAll('.tool-card');
            query = query.toLowerCase();
            cards.forEach(card => {
                const name = card.dataset.name;
                card.style.display = name.includes(query) ? 'flex' : 'none';
            });
        }

        function showToast(msg) {
            const toast = document.getElementById('toast');
            document.getElementById('toastMsg').innerText = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }

        init();
    </script>
</body>
</html>
        """

if __name__ == "__main__":
    Handler = ConfigHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print(f"Opening browser...")
        webbrowser.open(f"http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()
