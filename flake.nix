{
  description = "HexStrike AI Nix flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    pyproject-nix = {
      url = "github:nix-community/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    autorecon-src = {
      url = "github:Tib3rius/AutoRecon";
      flake = false;
    };
    paramspider-src = {
      url = "github:devanshbatham/ParamSpider/790eb91213419e9c4ddec2c91201d4be5399cb77";
      flake = false;
    };
    scout-suite-src = {
      url = "github:nccgroup/ScoutSuite/7909f2fc6186063e5c9e7ddef8c4d7d1072c8f3d";
      flake = false;
    };
    docker-bench-security-src = {
      url = "github:docker/docker-bench-security";
      flake = false;
    };
  };

  outputs =
    inputs@{
      self,
      nixpkgs,
      flake-utils,
      pyproject-nix,
      autorecon-src,
      paramspider-src,
      scout-suite-src,
      docker-bench-security-src,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        # webdriver-manager (in requirements.txt) in nixpkgs has a platforms definition that excludes darwin
        # we drop this along with linux-specific tests with this overlay
        overlayWebdriverManager = (final: prev: {
          python3 = prev.python3.override {
            packageOverrides = self: super: {
              "webdriver-manager" =
                super."webdriver-manager".overridePythonAttrs (old: {
                  # Allow on macOS (remove the platforms restriction)
                  meta = builtins.removeAttrs old.meta [ "platforms" ];

                  # Skip tests and avoid test deps (prevents pybrowsers/mdfind path)
                  doCheck = false;
                  nativeCheckInputs = [ ];
                  checkInputs = [ ];
                  checkPhase = "true";
                  pythonImportsCheck = [ ];
                });
            };
          };

          # expose the updated package set so anything using pkgs.python3Packages sees it
          python3Packages = final.python3.pkgs;
        });

        pkgs = import nixpkgs {
          inherit system;
          config = {
            allowUnfree = true;
          };
          overlays = [ overlayWebdriverManager ];
        };

        python = pkgs.python3;
        pythonPackages = pkgs.python3Packages;

        # Below are dependencies not packaged in nixpkgs
        #autorecon-project = pyproject-nix.lib.project.loadPyproject { projectRoot = autorecon-src; };
        #ar-attrs = autorecon-project.renderers.buildPythonPackage { inherit python; };
        #autorecon = python.pkgs.buildPythonApplication (ar-attrs // {
        #  name = "autorecon";
        #});

        #paramspider = python.pkgs.buildPythonApplication {
        #  name = "paramspider";
        #  version = "790eb91";

        #  src = paramspider-src;
        #};

        #scout-suite = python.pkgs.buildPythonApplication {
        #  name = "scout-suite";
        #  version = "7909f2f";

        #  src = scout-suite-src;
        #};

        docker-bench-security = pkgs.stdenv.mkDerivation {
          name = "docker-bench-security";
          builder = pkgs.bash;
          buildInputs = [ pkgs.jq ];
          args = let
            buildScript = pkgs.writeShellScript "build" ''
              ${pkgs.coreutils}/bin/mkdir -p $out/bin
              ${pkgs.coreutils}/bin/cp ${docker-bench-security-src}/docker-bench-security.sh $out/bin/docker-bench-security.sh
            '';
          in [ buildScript ];
        };
        # End of custom packages

        corepkgs = with pkgs; [
          # Network & Reconnaissance
          nmap
          masscan
          rustscan
          amass
          subfinder
          nuclei
          fierce
          dnsenum
          aircrack-ng
          metasploit
          #autorecon # TODO
          responder
          enum4linux-ng
          theharvester
          # Web Application Security
          gobuster
          feroxbuster
          pythonPackages.dirsearch
          ffuf
          dirb
          httpx
          katana
          nikto
          sqlmap
          wpscan
          arjun
          ##paramspider # TODO
          dalfox
          wafw00f
          # Password & Authentication
          john
          hashcat
          medusa
          ##pythonPackages.patator # TODO: marked broken in nixpkgs
          evil-winrm
          hash-identifier
          # Binary Analysis & Reverse Engineering
          gdb
          radare2
          binwalk
          ghidra-bin
          binutils
          volatility3
          foremost
          steghide
          exiftool
          # Cloud Security Tools
          ##prowler # TODO broken in nixpkgs
          trivy
          ##scout-suite # TODO
          kube-hunter
          kube-bench
          docker-bench-security
        ] ++ lib.optionals pkgs.stdenv.isLinux [
          # Linux specific tooling
          # Network & Reconnaissance
          netexec
          # Web Application Security
          # Password & Authentication
          hydra
          ophcrack
          # Binary Analysis & Reverse Engineering
          checksec
          u-root-cmds
          # Browser Agent Requirements
          chromium
          chromedriver
        ] ++ lib.optionals pkgs.stdenv.isDarwin [
          # macOS specific tooling
          # Browser Agent Requirements
          google-chrome
        ];

        hexstrike-ai-project = pyproject-nix.lib.project.loadRequirementsTxt {
          projectRoot = ./.;
        };
        hexstrike-attrs = hexstrike-ai-project.renderers.buildPythonPackage { inherit python; };
        hexstrike-ai-server-pkg = python.pkgs.buildPythonApplication (hexstrike-attrs // {
          name = "hexstrike-ai-server";
          nativeBuildInputs = [ pkgs.makeWrapper ];
          installPhase = ''
            runHook preInstall

            mkdir -p $out/bin
            cp ${self}/hexstrike_server.py $out/bin/hexstrike_server.py
            chmod +x $out/bin/hexstrike_server.py

            wrapProgram $out/bin/hexstrike_server.py \
              --prefix PATH : ${pkgs.lib.makeBinPath corepkgs}

            runHook postInstall
          '';
          meta = {
            mainProgram = "hexstrike_server.py";
          };
        });

        hexstrike-ai-mcp-pkg = python.pkgs.buildPythonApplication (hexstrike-attrs // {
          name = "hexstrike-ai-mcp";
          installPhase = ''
            runHook preInstall

            mkdir -p $out/bin
            cp ${self}/hexstrike_mcp.py $out/bin/hexstrike_mcp.py
            chmod +x $out/bin/hexstrike_mcp.py
            runHook postInstall
          '';
          meta = {
            mainProgram = "hexstrike_mcp.py";
          };
        });

      in
      {
        devShell = pkgs.mkShell {
          name = "HexStrike AI Dev Shell";
          buildInputs = [ hexstrike-ai-server-pkg hexstrike-ai-mcp-pkg ];
        };

        packages = rec {
          hexstrike-ai-server = hexstrike-ai-server-pkg;
          hexstrike-ai-mcp = hexstrike-ai-mcp-pkg;
          default = hexstrike-ai-server;
        };

        formatter = pkgs.nixfmt-rfc-style;
      }
    );
}
