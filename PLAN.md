# 3GPP UE Log Analyzer — Implementation Plan

## Overview

A desktop tool for ingesting, parsing, analyzing, and visualizing 3GPP UE (User Equipment) protocol logs across all radio access layers (NAS, RRC, PDCP, RLC, MAC, PHY). Targets engineers doing LTE/NR drive testing, lab debugging, and field issue triage.

---

## Phase 1: Requirements & Architecture

### Step 1 — Scope: Supported Log Formats

| Format | Source |
|---|---|
| Qualcomm QXDM/QCAT `.dlf`, `.isf`, `.hdf` | Snapdragon modems |
| MediaTek MTK Logger | MTK modems |
| Android `logcat` with modem logs | Generic Android |
| Wireshark `.pcap` / `.pcapng` | LTE/NR dissectors |
| Plain text / AT command logs | Generic |

### Step 1 — Scope: Protocol Layers

| Layer | Spec | Key Content |
|---|---|---|
| NAS | TS 24.301 (LTE), TS 24.501 (NR) | Attach, PDN/PDU Session, TAU, Auth, Security |
| RRC | TS 36.331 (LTE), TS 38.331 (NR) | Setup, Reconfiguration, Handover, MeasReport |
| PDCP / RLC / MAC | TS 36.3xx / 38.3xx | Throughput, retransmissions, HARQ |
| PHY | TS 36.2xx / 38.2xx | RSRP, RSRQ, SINR, BLER, MCS, CQI |

---

### Step 2 — Technology Stack

| Component | Library / Tool |
|---|---|
| Language | Python 3.11+ |
| GUI | PyQt6 |
| 3GPP ASN.1 decoding | `pycrate` |
| Parsing helpers | `pyparsing`, `construct` |
| Data processing | `pandas`, `numpy` |
| Visualization | `plotly` (charts), `pyqtgraph` (real-time) |
| Database | SQLite via `SQLAlchemy` |
| Packaging | `pyinstaller` |
| Testing | `pytest` |

---

### Step 3 — High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                     UI Layer                        │
│   File Loader │ Timeline View │ Filter Panel │ Plots│
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                  Analysis Engine                    │
│  Event Classifier │ Anomaly Detector │ KPI Engine   │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                  Parser Layer                       │
│  NAS Parser │ RRC Parser │ PHY Parser │ Format Mux  │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│               Log Ingestion Layer                   │
│  File Reader │ Format Detector │ Preprocessor       │
└─────────────────────────────────────────────────────┘
```

---

## Phase 2: Log Ingestion & Parsing

### Step 4 — Log Ingestion Layer

**Responsibilities:**
- Auto-detect file format via magic bytes, file extension, and content heuristics
- Handle encoding differences (UTF-8, binary, hex-dump, base64)
- Stream large files line-by-line to avoid memory exhaustion
- Emit a unified `LogEntry` object per message

**`LogEntry` data class:**
```python
@dataclass
class LogEntry:
    timestamp: datetime
    layer: str          # NAS, RRC, MAC, PHY, etc.
    direction: str      # UL / DL
    message_type: str   # e.g., "Attach Request"
    raw_bytes: bytes
    decoded: dict       # parsed fields key → value
    source_file: str
    source_line: int
```

**Format detector logic:**
```
if extension in (.pcap, .pcapng)  → pcap reader
elif extension in (.dlf, .isf)    → QXDM binary reader
elif "AT+" in first 100 lines     → AT command reader
elif hex-dump pattern detected    → hex log reader
else                              → plain text reader
```

---

### Step 5 — NAS Parser

**Standards:** 3GPP TS 24.301 (LTE EMM/ESM), TS 24.501 (NR 5GMM/5GSM)

**LTE EMM messages to parse:**
- `Attach Request` / `Accept` / `Reject` / `Complete`
- `Detach Request` / `Accept`
- `Authentication Request` / `Response` / `Failure`
- `Security Mode Command` / `Complete` / `Reject`
- `TAU Request` / `Accept` / `Reject` / `Complete`
- `Service Request` / `Reject`
- `EMM Information`
- `EMM Status`

**LTE ESM messages:**
- `PDN Connectivity Request` / `Accept` / `Reject`
- `Bearer Resource Allocation Request` / `Accept` / `Reject`
- `Activate Default/Dedicated EPS Bearer Context Request` / `Accept`
- `Deactivate EPS Bearer Context Request` / `Accept`

**NR 5GMM messages:**
- `Registration Request` / `Accept` / `Reject` / `Complete`
- `Deregistration Request` / `Accept`
- `Authentication Request` / `Response` / `Failure` / `Result`
- `Security Mode Command` / `Complete` / `Reject`
- `PDU Session Establishment Request` / `Accept` / `Reject`
- `Configuration Update Command` / `Complete`

**Decoder approach:**
- Use `pycrate` NAS modules for ASN.1/TLV decoding
- Fallback: manual IE (Information Element) parsing for common message types
- Extract key IEs: IMSI/SUCI/GUTI, cause codes, bearer IDs, APN/DNN, security algorithms

---

### Step 6 — RRC Parser

**Standards:** 3GPP TS 36.331 (LTE), TS 38.331 (NR)

**LTE RRC messages:**
- `RRCConnectionRequest` / `Setup` / `SetupComplete` / `Reject`
- `RRCConnectionReconfiguration` / `Complete`
- `RRCConnectionRelease`
- `RRCConnectionReestablishmentRequest` / `Reestablishment` / `Complete` / `Reject`
- `MeasurementReport`
- `HandoverCommand` (embedded in Reconfiguration)
- `UECapabilityEnquiry` / `Information`
- `SystemInformation` / `SystemInformationBlockType1`

**NR RRC messages:**
- `RRCSetupRequest` / `Setup` / `SetupComplete`
- `RRCReconfiguration` / `Complete`
- `RRCRelease`
- `RRCReestablishmentRequest` / `Reestablishment` / `Complete`
- `MeasurementReport`
- `UECapabilityEnquiry` / `Information`

**Decoder approach:**
- ASN.1 PER (Packed Encoding Rules) — use `pycrate` or `asn1tools` with 3GPP ASN.1 schema files
- Download ASN.1 schemas from 3GPP TS 36.331 / 38.331 spec ZIP files
- Cache compiled schemas to avoid reparse overhead on startup

---

### Step 7 — PHY / Radio Measurement Parser

**Key fields to extract:**
```
RSRP   (Reference Signal Received Power)      dBm
RSRQ   (Reference Signal Received Quality)    dB
SINR   (Signal-to-Interference-plus-Noise)    dB
CQI    (Channel Quality Indicator)            0–15
MCS    (Modulation and Coding Scheme)         0–31
BLER   (Block Error Rate)                     %
PCI    (Physical Cell ID)                     0–503
EARFCN / ARFCN  (Frequency channel number)
Timing Advance                                Ts units
```

**Approach:**
- Parse structured log lines with regex patterns per vendor format
- Build a time-series buffer: `{timestamp → {field → value}}`
- Feed directly into KPI engine and chart data model

---

## Phase 3: Analysis Engine

### Step 8 — Event Classification

```
Events
├── Connection Events
│   ├── Attach Success
│   ├── Attach Failure (with cause code + description)
│   ├── PDN/PDU Session Setup Success / Failure
│   ├── Handover Success
│   └── Handover Failure
├── Failure Events
│   ├── Attach Reject
│   ├── Authentication Failure
│   ├── RRC Connection Failure
│   ├── Radio Link Failure (RLF)
│   ├── T3410 / T3411 / T3402 timer expiry
│   └── RRC Reestablishment
├── Measurement Events
│   ├── Serving Cell Change
│   ├── Intra-frequency Handover
│   ├── Inter-frequency Handover
│   └── Inter-RAT Handover (LTE ↔ NR)
└── Session Events
    ├── Bearer Activation / Deactivation
    ├── TAU / Registration Update
    └── Detach (normal / abnormal)
```

Each event gets a `severity` tag:
- `INFO` — normal, expected behavior
- `WARNING` — recoverable issue (e.g., TAU reject with retry)
- `ERROR` — failed procedure (e.g., Attach Reject, RLF)
- `CRITICAL` — repeated failures or service loss

---

### Step 9 — KPI Computation Engine

| KPI | Formula | Unit |
|---|---|---|
| Attach Success Rate | Attach Accept / Attach Request × 100 | % |
| Attach Setup Time | Time(PDN Accept) − Time(Attach Request) | ms |
| Handover Success Rate | HO Complete / HO Command × 100 | % |
| RLF Rate | RLF count / hour | count/hr |
| Reestablishment Success Rate | Reest Complete / Reest Request × 100 | % |
| Average RSRP | Mean RSRP over time window | dBm |
| Average RSRQ | Mean RSRQ over time window | dB |
| Average SINR | Mean SINR over time window | dB |
| PDU Session Setup Time | Time(PDU Accept) − Time(PDU Request) | ms |
| NAS Signaling Overhead | NAS message count per hour | msg/hr |

KPIs are computed over configurable sliding time windows (default: full log, 1-min, 5-min).

---

### Step 10 — Anomaly Detection

**Rules engine** (each rule fires an event with severity WARNING or ERROR):

| Rule | Trigger | Severity |
|---|---|---|
| Repeated Attach Failures | ≥3 Attach Rejects in 5 min | ERROR |
| Authentication Loop | Auth Failure → Auth Request cycle ≥3 | ERROR |
| Ping-Pong Handover | HO between same 2 cells ≥3 in 2 min | WARNING |
| Prolonged RRC Idle | No RRC activity for >30s during data session | WARNING |
| Missing Security Mode | PDN Accept without prior Security Mode Complete | CRITICAL |
| Short-lived Bearer | Bearer activated then deactivated in <2s | WARNING |
| Signaling Storm | >50 NAS messages in 10s | WARNING |
| RLF Cluster | ≥2 RLFs in 5 min | ERROR |
| T3410 Expiry | Timer expiry detected in log | ERROR |

Rules are configurable via a YAML config file.

---

### Step 11 — Cause Code Decoder

Full lookup tables for:

**EMM Cause Codes (TS 24.301 §9.9.3.9):**
```
#2  IMSI unknown in HSS
#3  Illegal UE
#6  Illegal ME
#7  EPS services not allowed
#8  EPS and non-EPS services not allowed
#11 PLMN not allowed
#12 Tracking area not allowed
#13 Roaming not allowed in this TA
#14 EPS services not allowed in this PLMN
#15 No suitable cells in TA
#22 Congestion
#25 Not authorized for this CSG
#35 Requested service option not authorized in this PLMN
```

**5GMM Cause Codes (TS 24.501 §9.11.3.2):**
```
#3  Illegal UE
#5  PEI not accepted
#6  Illegal ME
#7  5GS services not allowed
#9  UE identity cannot be derived
#10 Implicitly deregistered
#11 PLMN not allowed
#12 Tracking area not allowed
#13 Roaming not allowed in TA
#15 No suitable cells in TA
#22 Congestion
#27 N1 mode not allowed
#31 Redirection to EPC required
#76 IAB node not authorized
```

Each entry includes:
- Numeric code
- Short name
- Full description from spec
- Recommended action for engineer

---

## Phase 4: Data Storage & Querying

### Step 12 — SQLite Schema

```sql
CREATE TABLE log_files (
    id      INTEGER PRIMARY KEY,
    path    TEXT NOT NULL,
    format  TEXT,
    loaded_at TEXT
);

CREATE TABLE log_entries (
    id          INTEGER PRIMARY KEY,
    file_id     INTEGER REFERENCES log_files(id),
    timestamp   TEXT NOT NULL,
    layer       TEXT,          -- NAS, RRC, MAC, PHY
    direction   TEXT,          -- UL, DL
    message_type TEXT,
    raw_hex     TEXT,
    source_line INTEGER
);

CREATE TABLE decoded_fields (
    entry_id    INTEGER REFERENCES log_entries(id),
    field_name  TEXT,
    field_value TEXT
);

CREATE TABLE events (
    id          INTEGER PRIMARY KEY,
    timestamp   TEXT,
    event_type  TEXT,
    severity    TEXT,          -- INFO, WARNING, ERROR, CRITICAL
    description TEXT,
    entry_id    INTEGER REFERENCES log_entries(id)
);

CREATE TABLE kpis (
    id          INTEGER PRIMARY KEY,
    timestamp   TEXT,
    window_sec  INTEGER,       -- time window in seconds
    kpi_name    TEXT,
    value       REAL,
    unit        TEXT
);

CREATE TABLE radio_measurements (
    id          INTEGER PRIMARY KEY,
    entry_id    INTEGER REFERENCES log_entries(id),
    timestamp   TEXT,
    pci         INTEGER,
    earfcn      INTEGER,
    rsrp        REAL,
    rsrq        REAL,
    sinr        REAL,
    cqi         INTEGER,
    mcs         INTEGER,
    bler        REAL
);
```

**Indexes:** timestamp, layer, message_type, severity for fast filtering.

---

### Step 13 — Query Interface

- Filter by time range (start/end datetime)
- Filter by layer (NAS / RRC / MAC / PHY, multi-select)
- Filter by message type (autocomplete dropdown)
- Filter by direction (UL / DL)
- Filter by severity (multi-select checkboxes)
- Full-text search on `decoded_fields.field_value`
- Export filtered results to CSV, JSON, or Excel

---

## Phase 5: UI Development

### Step 14 — Main Window Layout

```
┌──────────────────────────────────────────────────────────┐
│  File | View | Filters | Analysis | Export | Help        │
├────────────┬─────────────────────────────────────────────┤
│  Files     │              Timeline View                  │
│  Panel     │  [swim-lane event timeline]                 │
│            │  NAS  ─●──────●────●──                     │
│  log1.txt  │  RRC  ──●───────────●──                    │
│  log2.pcap │  PHY  ─────────────────                    │
├────────────┼─────────────────────────────────────────────┤
│  Filters   │           Message Detail Panel              │
│            │  Message: Attach Request                    │
│  Layer     │  Timestamp: 2024-01-15 10:23:45.123        │
│  Severity  │  ├── EPS Mobile Identity: IMSI             │
│  Time      │  ├── ESM Message Container                 │
│  Search    │  │   └── PDN Connectivity Request          │
│            │  └── Last Visited TAI: MCC=310 MNC=410     │
├────────────┴─────────────────────────────────────────────┤
│              KPI Dashboard / Charts                      │
│  [RSRP/RSRQ over time]  [Attach stats]  [HO success]   │
└──────────────────────────────────────────────────────────┘
```

---

### Step 15 — Timeline View

- Horizontal swim-lane layout with one lane per protocol layer
- Events rendered as colored dots/markers on a time axis:
  - Green = success / normal
  - Yellow = warning / retransmission
  - Red = failure / reject / RLF
- Zoom in/out with `Ctrl+Scroll` (minimum resolution: 1ms, max: full log)
- Pan by click-drag on the timeline
- Click any event to populate the Message Detail Panel
- Hover tooltip shows: timestamp, message type, direction, brief summary
- "Fit to window" button resets zoom to show full log duration
- Ruler at top shows absolute timestamps

---

### Step 16 — Filter & Search Panel

- **Time range**: dual datetime pickers with "Last 1 min / 5 min / All" quick buttons
- **Layer**: checkboxes for NAS, RRC, MAC, PHY
- **Severity**: checkboxes for INFO, WARNING, ERROR, CRITICAL
- **Direction**: UL / DL / Both radio buttons
- **Message type**: searchable dropdown with autocomplete
- **Cause code**: dropdown of known cause codes
- **Text search**: searches decoded field values; highlights matches in detail panel
- "Apply" button updates timeline and message list in real-time
- "Reset" button clears all filters

---

### Step 17 — KPI Dashboard

**Charts (all rendered with `plotly` for interactivity):**

1. **Radio Quality Over Time** — RSRP, RSRQ, SINR line charts on shared time axis
2. **Attach Procedure Timeline** — bar chart showing attach attempts, successes, failures per 1-min bucket
3. **Cause Code Distribution** — pie chart of reject/failure cause codes
4. **Handover Statistics** — grouped bar chart: success vs failure per HO type
5. **Throughput Estimate** — line chart from MAC layer if available
6. **KPI Summary Cards** — large-number display for ASR, HO Success Rate, RLF count, Avg RSRP

All charts are exportable as PNG via right-click context menu.

---

### Step 18 — Message Sequence Chart (Ladder Diagram)

- Renders standard 3GPP-style MSC/ladder diagram
- Entities shown as vertical lines: **UE** | **eNB/gNB** | **MME/AMF** | **SGW/UPF**
- Arrows between entities show message direction and name
- Failed or rejected messages shown in red with cause code annotation
- Controllable zoom and pan
- Filterable by procedure type (e.g., show only Attach procedure)
- Export to SVG or PNG

---

## Phase 6: Project File Structure

```
3gpp-ue-log-analyzer/
├── main.py                    # Entry point, launches PyQt6 app
├── requirements.txt
├── PLAN.md                    # This file
│
├── core/
│   ├── __init__.py
│   ├── log_entry.py           # LogEntry dataclass
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── detector.py        # Format auto-detection
│   │   ├── text_reader.py     # Plain text / AT log reader
│   │   ├── pcap_reader.py     # PCAP reader via scapy
│   │   └── qxdm_reader.py     # QXDM binary reader
│   │
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── nas_parser.py      # NAS EMM/ESM + 5GMM/5GSM
│   │   ├── rrc_parser.py      # RRC LTE + NR
│   │   └── phy_parser.py      # PHY measurements
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── classifier.py      # Event classification
│   │   ├── kpi_engine.py      # KPI computation
│   │   ├── anomaly.py         # Anomaly detection rules
│   │   └── cause_codes.py     # Cause code lookup tables
│   │
│   └── storage/
│       ├── __init__.py
│       ├── schema.py          # SQLAlchemy models
│       └── repository.py      # Query interface
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py         # Top-level QMainWindow
│   ├── timeline_view.py       # Swim-lane timeline widget
│   ├── detail_panel.py        # Message field tree view
│   ├── filter_panel.py        # Filter/search sidebar
│   ├── kpi_dashboard.py       # KPI charts tab
│   ├── msc_view.py            # Message sequence chart
│   └── file_panel.py          # Loaded files list
│
├── config/
│   ├── anomaly_rules.yaml     # Configurable anomaly rules
│   └── cause_codes.yaml       # Cause code lookup tables
│
└── tests/
    ├── fixtures/              # Sample log snippets
    ├── test_nas_parser.py
    ├── test_rrc_parser.py
    ├── test_kpi_engine.py
    └── test_anomaly.py
```

---

## Phase 7: Testing & Validation

### Step 19 — Unit Tests

- Test each parser with known-good log snippets from spec examples
- Validate NAS message decoding field-by-field against TS 24.301/24.501
- Test KPI calculations with synthetic controlled datasets
- Test anomaly rules fire correctly on crafted input sequences
- Use `pytest` with parametrized fixtures

### Step 20 — Integration Tests

- End-to-end: load sample log → parse → analyze → verify correct events in DB
- Round-trip: encode a NAS message, parse it back, verify field equality
- Use real anonymized log samples where available

### Step 21 — Performance Tests

- 100MB log file: parse in <30s
- UI timeline render: 10,000 events in <1s
- KPI computation: full recalculation on filter change in <500ms
- SQLite query with time-range filter: <100ms on 1M rows

---

## Phase 8: Packaging & Distribution

### Step 22 — Packaging

```bash
# Install build deps
pip install pyinstaller

# Build single-file executable
pyinstaller --onefile --windowed --name "UE-Log-Analyzer" main.py

# Output: dist/UE-Log-Analyzer.exe (Windows) or dist/UE-Log-Analyzer (Linux/macOS)
```

Optional Docker target for server-based deployment:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["python", "main.py", "--headless", "--port", "8080"]
```

---

## Phase 9: Development Roadmap

### Milestone Order

| Priority | Milestone | Deliverable |
|---|---|---|
| 1 | Log ingestion + NAS parser | Parse attach/detach/TAU from text logs |
| 2 | SQLite storage + basic list UI | View parsed messages in scrollable table |
| 3 | Event classification + cause codes | Detect and annotate failures with cause codes |
| 4 | RRC parser + timeline view | Full swim-lane timeline with NAS+RRC events |
| 5 | PHY parser + KPI charts | RSRP/RSRQ charts and KPI summary cards |
| 6 | Anomaly detection + MSC view | Auto-flag issues, ladder diagram export |
| 7 | PCAP support + QXDM support | Broader log format coverage |
| 8 | Packaging + docs + installer | Distributable executable |

---

## Key 3GPP Specifications Reference

| Spec | Title |
|---|---|
| TS 24.301 | NAS protocol for EPS (LTE) |
| TS 24.501 | NAS protocol for 5GS (NR) |
| TS 36.331 | RRC protocol for LTE |
| TS 38.331 | RRC protocol for NR |
| TS 36.321 | MAC protocol for LTE |
| TS 38.321 | MAC protocol for NR |
| TS 36.211 | Physical channels for LTE |
| TS 38.211 | Physical channels for NR |
| TS 23.401 | EPS Architecture (LTE) |
| TS 23.501 | 5GS Architecture (NR) |

All specs are freely available at **3gpp.org** under the Specifications portal.
