#!/usr/bin/env python3
"""
Enrichment layer applied on top of the AST-derived tools_manifest.json entries.

Everything here is *derived or curated*, never required for the manifest to
work - if a tool isn't covered by a rule below it just keeps its plain text
input and generic explanation. Three things are added per tool:

  - param["doc"]:      the parameter's own description, pulled out of the
                        function's docstring (works for "Args:" style and
                        for bare "name: description" lines).
  - param["options"]:  a short list of valid choices for a dropdown, when
                        the docstring itself enumerates them (e.g. "(e.g.,
                        -sS, -sT, -sU)", "(baseline, full, api)",
                        "query|body|headers|cookie") or the type is bool.
                        Never invented - only ever taken from what the
                        author of hexstrike_mcp.py already wrote down.
  - tool["eli5"]:      a one-paragraph "explain it to a 7 year old"
                        description. Curated by hand for the tools people
                        reach for most; everything else gets a template
                        built from its category and its own doc line so
                        no tool is left without one.
"""
import re

# ---------------------------------------------------------------------------
# Per-parameter docstring parsing
# ---------------------------------------------------------------------------

_ARG_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")


def parse_param_docs(docstring, param_names):
    """Map param name -> its description, from any 'name: text' line in the
    docstring (Google-style Args: blocks, or bare inline notes)."""
    if not docstring:
        return {}
    wanted = set(param_names)
    out = {}
    current = None
    for raw_line in docstring.splitlines():
        m = _ARG_LINE_RE.match(raw_line)
        if m and m.group(1) in wanted:
            current = m.group(1)
            out[current] = m.group(2).strip()
        elif current and raw_line.strip() and not raw_line.strip().endswith(":"):
            # continuation of a wrapped description line
            if raw_line.strip() not in ("Returns:", "Args:"):
                out[current] = (out[current] + " " + raw_line.strip()).strip()
        else:
            current = None
    return out


# A token that looks like a real enum choice: short, no sentence punctuation.
_TOKEN_RE = re.compile(r"^-{0,2}[A-Za-z0-9][A-Za-z0-9_\-./]{0,24}$")


def extract_options(description):
    """Best-effort pull of an enumerated choice list out of a parameter's own
    description text. Only trusts parenthesised or pipe-separated groups the
    author already wrote; returns None rather than guess."""
    if not description:
        return None

    group = None
    paren = re.findall(r"\(([^)]+)\)", description)
    if paren:
        # prefer the group that actually looks like a list, not a stray aside
        for g in paren:
            if "," in g or "|" in g:
                group = g
                break
    if group is None and "|" in description:
        group = description

    if group is None:
        return None

    group = re.sub(r"^\s*e\.?g\.?,?\s*", "", group, flags=re.IGNORECASE)
    sep = "|" if "|" in group and "," not in group else ","
    raw_items = [i.strip().rstrip(".") for i in group.split(sep)]

    items = []
    for item in raw_items:
        if item.lower() in ("etc", "etc."):
            continue
        # An "e.g." list is examples, not an exhaustive set - a non-token
        # entry there just means we stop trusting the list, not that we
        # should silently drop the one odd entry and keep the rest (that
        # would present a partial example as if it were the full set).
        if not _TOKEN_RE.match(item):
            return None
        items.append(item)

    # de-dup, keep order
    seen = set()
    items = [i for i in items if not (i in seen or seen.add(i))]
    if len(items) < 2 or len(items) > 12:
        return None
    return items


# A couple of expand-able range hints that show up as "(T0-T5)" style text
# rather than a comma list - handled by param name since the pattern is
# ambiguous in general text.
_RANGE_OPTIONS = {
    "timing": [f"T{i}" for i in range(6)],
}

# Names where a safe, standard option set applies across tools even when the
# docstring doesn't spell it out (plain "HTTP method" with no examples, etc).
_FALLBACK_OPTIONS_BY_NAME = {
    "method": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    "http_method": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
}


def options_for_param(name, type_, description):
    if type_ == "bool":
        return ["true", "false"]
    if name in _RANGE_OPTIONS:
        return _RANGE_OPTIONS[name]
    opts = extract_options(description)
    if opts:
        return opts
    if name in _FALLBACK_OPTIONS_BY_NAME:
        return _FALLBACK_OPTIONS_BY_NAME[name]
    return None


# ---------------------------------------------------------------------------
# ELI5 explanations
# ---------------------------------------------------------------------------

# Hand-written for the tools people reach for first.
ELI5_BY_TOOL = {
    "nmap_scan": "Nmap knocks on a computer's doors (ports) one by one and listens "
                 "for an answer, so you can find out which doors are open and what's "
                 "behind them.",
    "nmap_advanced_scan": "Same idea as a regular Nmap knock, but you get to pick exactly "
                           "how loud you knock, how fast, and whether to also ask 'what "
                           "are you?' to whatever answers the door.",
    "rustscan_fast_scan": "Knocks on ALL the doors of a computer super fast, then hands the "
                           "short list of open ones to Nmap to take a closer look.",
    "masscan_high_speed": "Like Nmap's door-knocking, but built for speed - it can check "
                           "every door on the whole internet block in a hurry.",
    "sqlmap_scan": "Pokes at a website's search boxes and login forms to see if it "
                    "accidentally lets you talk directly to its database, like finding "
                    "a secret door behind a painting.",
    "nuclei_scan": "Runs through a giant checklist of known weak spots other people have "
                    "already found in websites, and tells you if this one has any of them.",
    "hydra_attack": "Tries lots and lots of password guesses on a login really fast, like "
                     "trying every key on a giant keyring until one opens the door.",
    "john_crack": "Takes a scrambled password (a hash) and tries to unscramble it by "
                   "guessing - starting with common passwords, like 'password123'.",
    "hashcat_crack": "Same job as John the Ripper - unscrambling passwords - but it uses "
                      "the graphics card to guess millions of passwords per second.",
    "ffuf_scan": "Throws a huge list of made-up webpage names at a website really fast to "
                  "find pages that exist but aren't linked from anywhere obvious.",
    "gobuster_scan": "Same idea as ffuf - guesses lots of folder and page names on a "
                      "website to find the ones that are hiding there.",
    "dirsearch_scan": "Walks through a big list of common file and folder names, checking "
                       "each one to see if the website actually has it.",
    "feroxbuster_scan": "Like gobuster, but it also automatically explores any new folders "
                         "it finds, going deeper and deeper on its own.",
    "nikto_scan": "Gives a website a quick health check, looking for old software versions "
                   "and common misconfigurations that are easy to fix but often forgotten.",
    "wpscan_analyze": "A nikto-style check made just for WordPress websites - looks for old "
                       "plugins, themes, and usernames that could be a way in.",
    "amass_scan": "Finds all the little sibling websites hiding under a big domain name, "
                   "like finding every room in a house you only knew the front door of.",
    "subfinder_scan": "Another way to find those hidden sibling websites (subdomains) under "
                       "a domain, by asking lots of different sources at once.",
    "metasploit_run": "A big toolbox of ready-made 'tricks' (exploits) for getting into "
                       "systems with known weaknesses, used to prove a weakness is real.",
    "msfvenom_generate": "Builds a small custom program (a payload) that, if it runs on a "
                          "target computer, phones home so you know you got in.",
    "ghidra_analysis": "Takes a program that's already built (just 1s and 0s) and turns it "
                        "back into something closer to readable code, so you can study it.",
    "radare2_analyze": "Like Ghidra - pulls a finished program apart to see how it works "
                        "inside, piece by piece.",
    "gdb_analyze": "Lets you run a program one tiny step at a time and peek inside its "
                    "brain (memory) while it's running, to see exactly what it's doing.",
    "binwalk_analyze": "Looks inside a single file to find other files hidden or packed "
                        "inside it, like finding toys hidden inside a cereal box.",
    "exiftool_extract": "Reads the hidden notes a file carries about itself - like when a "
                         "photo secretly remembers the camera and location it was taken.",
    "steghide_analysis": "Checks whether a secret message or file has been hidden inside a "
                          "picture or audio file, tucked away where you can't see it.",
    "volatility3_analyze": "Looks through a snapshot of a computer's memory (what it was "
                            "thinking about right when the snapshot was taken) to find clues.",
    "wireshark": "Watches the data flowing over a network and shows you every little "
                  "packet, like reading everyone's postcards as they go through the mail.",
    "tshark": "The same postcard-reading as Wireshark, but typed into the command line "
               "instead of a window with buttons.",
    "aircrack_ng": "Family of tools for Wi-Fi security testing - listening to wireless "
                    "signals and trying to recover the network password.",
    "responder": "Listens quietly on a network for computers asking 'who am I talking to?' "
                  "and can answer 'me!' to trick them into sending their login secrets.",
    "enum4linux_scan": "Asks a Windows-style file-sharing server lots of polite questions - "
                        "what users exist, what folders are shared - and writes down the answers.",
    "smbmap_scan": "Checks which shared folders on a Windows-style server you're allowed "
                    "to open, and whether you can read or even write files in them.",
    "trivy_scan": "Checks a container image or project's folder of ingredients (dependencies) "
                   "against a list of known weak spots, like checking food expiry dates.",
    "checkov_iac_scan": "Reads infrastructure 'recipe' files (like Terraform) before they're "
                         "ever run, and flags recipe steps that would build something unsafe.",
    "prowler_scan": "Goes through an AWS cloud account's settings room by room, checking "
                     "that doors are locked the way they're supposed to be.",
    "kube_hunter_scan": "Pokes around a Kubernetes cluster (a fleet of containers) looking "
                         "for doors left open that shouldn't be.",
    "jwt_analyzer": "Looks inside a JWT token - a little signed note websites use to "
                     "remember who you are - to see if it was built safely.",
    "burpsuite_alternative_scan": "Crawls a website like a visitor would, clicking around and "
                                    "filling in forms, while quietly checking each page for "
                                    "common security mistakes.",
    "arjun_parameter_discovery": "Guesses hidden form-field names a webpage secretly accepts, "
                                   "even though it doesn't show them anywhere on the page.",
}

# Friendly openers per category, used to build a template ELI5 for every
# tool that doesn't have a hand-written one above.
_CATEGORY_METAPHOR = {
    "binary analysis & reverse engineering tools":
        "a tool for taking apart a finished program to see how it works inside",
    "additional security tools from original implementation":
        "a classic, well-known security tool brought into HexStrike's toolbox",
    "system monitoring & telemetry":
        "a tool for watching what the HexStrike server itself is doing right now",
    "cloud security tools":
        "a tool that checks whether an online cloud account's settings are safe",
    "enhanced http testing framework & browser agent (burp suite alternative)":
        "a tool for clicking around a website like a visitor while quietly checking for "
        "security mistakes",
    "intelligent decision engine tools":
        "a tool that uses AI to help pick the right next move during a security test",
    "advanced web security tools continued":
        "a tool for poking at websites to see how they're built and where they're weak",
    "bug bounty hunting specialized workflows":
        "a ready-made checklist for hunting the kind of bugs that earn a reward",
    "enhanced visual output tools":
        "a tool for turning scan results into a nicer-looking report",
    "file operations & payload generation":
        "a tool for reading, writing, or building files on the HexStrike server",
    "core network scanning tools":
        "a tool for peeking at computers and networks from the outside",
    "python environment management":
        "a tool for setting up a clean Python workspace to run other tools in",
}

_JARGON = [
    (r"\bvulnerabilit(y|ies)\b", "weak spot"),
    (r"\benumerat(e|ion|ing)\b", "list out"),
    (r"\bexploit(ation)?\b", "trick to get in"),
    (r"\bpayload\b", "little program"),
    (r"\bsubdomain(s)?\b", "part of a website's address"),
    (r"\bfuzz(ing)?\b", "throw lots of weird inputs at"),
    (r"\breconnaissance\b", "scouting"),
    (r"\bhash(es)?\b", "scrambled password"),
    (r"\bbrute[- ]force\b", "try every possibility"),
    (r"\bauthentication\b", "login check"),
    (r"\bmisconfiguration(s)?\b", "a setting that's set up wrong"),
    (r"\bmetadata\b", "hidden notes about a file"),
    (r"\bpacket(s)?\b", "little piece of network data"),
    (r"\bencod(e|ing|ed)\b", "disguise"),
]


def _simplify(text):
    out = text
    for pattern, repl in _JARGON:
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    return out


def eli5_for_tool(name, category, doc_first):
    if name in ELI5_BY_TOOL:
        return ELI5_BY_TOOL[name]
    metaphor = _CATEGORY_METAPHOR.get(category.lower())
    simple_doc = _simplify(doc_first.rstrip(".")) if doc_first else ""
    if metaphor and simple_doc:
        return f"This is {metaphor}. In short: {simple_doc[0].lower()}{simple_doc[1:]}."
    if simple_doc:
        return f"In short: {simple_doc[0].lower()}{simple_doc[1:]}."
    return "A HexStrike security tool - see its name and category for what it checks."


def enrich(tools, source_by_name):
    """Mutates each tool dict in place, adding param docs/options and eli5."""
    for tool in tools:
        docstring = source_by_name.get(tool["name"], "")
        param_names = [p["name"] for p in tool["params"]]
        docs_by_param = parse_param_docs(docstring, param_names)
        for p in tool["params"]:
            desc = docs_by_param.get(p["name"], "")
            p["doc"] = desc
            opts = options_for_param(p["name"], p["type"], desc)
            if opts:
                p["options"] = opts
        tool["eli5"] = eli5_for_tool(tool["name"], tool["category"], tool["doc"])
    return tools
