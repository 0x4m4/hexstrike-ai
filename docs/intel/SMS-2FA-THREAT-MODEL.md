# SMS-2FA Threat Model (Defensive)

| Field | Value |
| --- | --- |
| Document | `docs/intel/SMS-2FA-THREAT-MODEL.md` |
| Status | Living threat intel — **defense / remediation only** |
| Audience | Operators, product security, Samson purple-team planners |
| Related | `docs/ARCHITECTURE.md` (trust boundaries), NIST deprecation of SMS OTP |

**Policy:** This document describes how SMS-2FA fails and how to replace it. It is **not** an operational playbook for SS7 access, IMSI catchers, or SMS interception against real subscribers.

---

## 1. Why SMS-2FA is deprecated

SMS one-time codes inherit the trust model of mobile signalling and the subscriber lifecycle. Compromise is possible at **network, operator, device, and radio** layers. NIST and peer guidance treat SMS OTP as **deprecated / restricted** for high-assurance authentication — prefer phishing-resistant factors (FIDO2/WebAuthn, hardware tokens, bound push).

---

## 2. Conceptual interception (SS7 / UpdateLocation) — overview only

High-level failure mode (for risk communication, not execution):

1. **Subscriber identity** — attacker needs IMSI + home HLR routing context.
2. **Spoofed UpdateLocation** — via unauthorized SS7/SIGTRAN exposure, home network is told the subscriber “roamed” to attacker-controlled MSC/VLR.
3. **SMS reroute** — MO/MT SMS (including bank OTP) is delivered to the attacker’s signalling endpoint instead of the victim handset.
4. **Victim symptoms** — brief loss of service and/or missing OTP SMS.

**SIM800C / cheap GSM modules:** not an SS7 “hack from the radio.” They are commodity receivers/modems. In abuse reports they appear as **downstream OTP collectors** after signalling already redirected, or as adjuncts in local rogue-BTS research — not as a standalone SS7 gateway.

Other SMS-2FA failure modes (non-SS7):

| Mode | Summary |
| --- | --- |
| SIM-swapping | Social engineering of carrier retail / support to reissue SIM |
| Device malware | Android bankers / notification listeners read OTP on-device |
| Diameter (4G) | Signalling-plane analogues to SS7 class bugs on LTE interconnect |

---

## 3. Attack method → layer → defense

| Method | Layer | Description | Defense |
| --- | --- | --- | --- |
| **SS7 UpdateLocation spoof** | Network interconnect (SS7/SIGTRAN) | Spoofed location update → SMS delivered to attacker MSC/VLR | **Retire SMS-2FA**; push-2FA; hardware tokens; FIDO2/WebAuthn |
| **SIM-swapping** | Carrier / retail process | Social engineering to reissue SIM to attacker | SIM PIN; strong IDV; port-out / SIM-change locks; protected eSIM; out-of-band confirm |
| **Phishing / malware on device** | User device | Malware or overlay steals SMS / notifications | OS sandbox; avoid sideload; MDM where applicable; **FIDO2/WebAuthn** (not SMS) |
| **IMSI-catcher (rogue BTS)** | Radio access | Fake cell forces/attracts UE; may intercept legacy SMS paths | Prefer modern RAT (VoLTE/NR); carrier integrity; again: **do not rely on SMS OTP** |
| **Diameter weaknesses (4G)** | Network interconnect (LTE) | Interconnect abuse analogous to SS7 class issues | Same as SS7 row: push / OTP over app channel / FIDO2; retire SMS |

---

## 4. Comparative 2FA methods (reliability vs UX)

Scores are qualitative for product security planning (`H` high / `M` medium / `L` low). “Phishing-resistant” follows modern auth guidance (bound authenticator, not OTP relayable by attacker).

| Method | Phishing-resistant | Resists SS7 / SIM-swap | Resists device malware* | UX / recovery | Deploy cost | Verdict for high-value (banking, wallet, admin) |
| --- | --- | --- | --- | --- | --- | --- |
| **SMS OTP** | No | No | No | High UX, fragile recovery | Low | **Do not use** as primary MFA |
| **Voice OTP** | No | No (same numbering plane) | Partial | Medium | Low | Avoid |
| **Email OTP** | No | N/A (mailbox threats) | Partial | Medium | Low | Weak secondary only |
| **TOTP app** (offline) | No (prompt phishing / fatigue) | Yes vs SS7/SIM-swap | Partial (seed theft) | Medium | Low | Acceptable interim; prefer upgrade |
| **Push approve** (bound app) | Partial (MFA fatigue / prompt bombing) | Yes vs SS7 | Partial | High | Medium | OK with number-matching + rate limits |
| **Push + number matching** | Better than bare push | Yes vs SS7 | Partial | High | Medium | Good transitional control |
| **Hardware token** (OTP/display) | Partial | Yes | Yes (if not on phone) | Lower UX | Medium–High | Strong for admins |
| **FIDO2 / WebAuthn** (platform or roaming) | **Yes** | Yes | Strong (origin-bound) | High (platform) / Medium (roaming) | Medium | **Preferred** |
| **Passkeys** | **Yes** | Yes | Strong | High | Medium | **Preferred** default |

\* Device malware can still target session cookies / overlay / accessibility; phishing-resistant MFA reduces OTP theft but does not replace endpoint hygiene.

### Recommendation ladder

```text
Legacy:     SMS OTP / voice OTP     → retire
Interim:    TOTP + number-matched push
Target:     Passkeys / WebAuthn (+ hardware key for privileged roles)
```

---

## 5. Security invariants (product / Samson engagements)

1. **Never** treat SMS delivery as a confidential channel.  
2. High-value actions (fund transfer, key export, admin login) must not gate solely on SMS.  
3. If SMS remains for legacy users: risk-accept explicitly; add step-up WebAuthn for sensitive operations.  
4. Purple-team scenarios may **simulate** OTP theft consequences (session takeover drills) without performing live SS7/radio attacks.  
5. Incident response for suspected SIM-swap: freeze accounts, rotate sessions, force WebAuthn enrollment, carrier port lock.

---

## 6. Mapping to Samson / HexStrike scope

| Samson / HexStrike control | Relevance |
| --- | --- |
| Financial guardrail + HITL | Compensating control when OTP/channel abuse suspected on money movement |
| ScopeEnforcer / operator approval | Keeps any telephony research authorized and in-scope |
| Architecture trust boundaries | SMS channel = **untrusted** signalling path (like untrusted RPC proxy) |
| Out of scope here | Buying SS7 access, operating rogue BTS, weaponized intercept tooling |

---

## 7. References (defensive reading)

- NIST SP 800-63B — authenticator types; SMS restricted/deprecated context  
- ENISA / GSMA public materials on interconnect signalling risks (SS7/Diameter) — awareness level  
- W3C WebAuthn / FIDO Alliance — phishing-resistant MFA  

---

## 8. SIM800C AT-команды (lab / authorized SIM only)

Commodity GSM modems (SIM800C and family) speak **Hayes AT**. Below is the public SMS subset used in IoT labs and in abuse reports as a **downstream OTP collector** on a line the operator already controls.

**Scope lock:** use only on **your** SIM / authorized test numbers. This section does **not** cover SS7, IMSI-catchers, or redirecting a third party’s SMS.

### 8.1 Serial / UART baseline

Typical USB-UART: `115200 8N1` (module-dependent; some boards `9600`).

| Command | Meaning |
| --- | --- |
| `AT` | Smoke: expect `OK` |
| `ATE0` | Echo off (cleaner logs) |
| `AT+CPIN?` | SIM status (`READY` / need PIN) |
| `AT+CPIN="xxxx"` | Enter SIM PIN (if required) |
| `AT+CSQ` | Signal quality (`rssi,ber`) |
| `AT+CREG?` | Network registration |
| `AT+COPS?` | Current operator |
| `AT+CMEE=2` | Verbose CME errors |

### 8.2 SMS mode and receive

| Command | Meaning |
| --- | --- |
| `AT+CMGF=1` | Text mode (PDU = `0`) |
| `AT+CSCS="GSM"` | Character set (or `"UCS2"` for Unicode) |
| `AT+CNMI=2,2,0,0,0` | New SMS forwarded to UART as `+CMT: ...` (live) |
| `AT+CNMI=2,1,0,0,0` | New SMS stored; UART gets `+CMTI: "SM",index` |
| `AT+CPMS="SM","SM","SM"` | Prefer SIM storage |
| `AT+CMGL="ALL"` | List all stored SMS |
| `AT+CMGL="REC UNREAD"` | List unread |
| `AT+CMGR=index` | Read SMS at index |
| `AT+CMGD=index` | Delete one SMS |
| `AT+CMGD=1,4` | Delete all (SIM800 family variant — verify on device) |

**Live indication example (text mode):**

```text
+CMT: "+79001234567","","26/07/16,16:00:00+12"
Your code is 482193
```

**Stored indication:**

```text
+CMTI: "SM",3
AT+CMGR=3
+CMGR: "REC UNREAD","+79001234567",,"26/07/16,16:00:00+12"
Your code is 482193
```

### 8.3 Send SMS (lab self-test only)

| Command | Meaning |
| --- | --- |
| `AT+CMGS="+79001234567"` | Prompt `>`; type body; end with `Ctrl+Z` (`0x1A`) |
| `AT+CMSS=index` | Send from storage |

Self-test loop: module A → SMS → module B → parse on UART → proves collector path without touching foreign subscribers.

### 8.4 Defender / purple-team notes

| Signal | Why it matters |
| --- | --- |
| Host process holding `/dev/ttyUSB*` + `AT+CNMI` + regex on `\b\d{4,8}\b` | Classic OTP harvester pattern |
| Sudden SMS silence on victim handset + auth success elsewhere | Consistent with redirect **or** SIM-swap — respond with MFA upgrade, not SMS resend |
| Product dependency on SMS OTP | Architectural debt — see §4 ladder (WebAuthn/passkeys) |

Samson mapping: treat UART OTP collectors as **untrusted channel endpoints** (same class as “untrusted proxy” in `docs/ARCHITECTURE.md`). No Samson runtime module drives SIM800C in-repo by default.

### 8.5 What this module is *not*

- Not an SS7 gateway  
- Not an IMSI-catcher / rogue BTS  
- Not a tool to request foreign IMSI / UpdateLocation  

---

## Document history

| Version | Change |
| --- | --- |
| 1.0 | Attack→layer→defense table; comparative 2FA matrix; remediation ladder; no operational SS7 guidance |
| 1.1 | Appendix: SIM800C AT SMS command reference (authorized lab / defender awareness) |
