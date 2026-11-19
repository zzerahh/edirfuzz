# Enhanced Directory Fuzzer

A Python-based ethical hacking tool for authorized web directory and file enumeration with real-time request-rate control, adaptive backoff, scope enforcement, and structured reporting.

This project was developed for the IKB31603 Ethical Hacking course at UniKL MIIT.

## Features

- Web directory and file enumeration
- Real-time request-rate control during an active scan
- Adaptive request-rate reduction when the target shows signs of stress
- HTTP response classification
- Authorization confirmation before scanning
- Target scope enforcement
- Safe localhost default target
- Dry-run mode
- Ctrl+C emergency stop
- Partial report generation after interruption
- JSON reporting
- CSV reporting
- Local Flask testing environment
- Automated testing with pytest

## Main Enhancement

Traditional directory fuzzers often use a fixed request rate during a scan.

The main enhancement implemented in this project is a centralized request scheduler that allows the request rate to be changed while the scan is running.

For example:

```text
Initial rate: 2 req/s

User enters:
10

Rate changed to 10 req/s
```

The scan continues without restarting.

The tool also supports adaptive rate control. When repeated server-pressure responses such as HTTP 429 are detected, the adaptive controller reduces the request rate automatically.

Example observed during testing:

```text
10 req/s
↓
5 req/s
↓
2.5 req/s
↓
1.25 req/s
↓
1 req/s
```

## Architecture

```text
User
 |
 v
main.py
CLI / orchestration
 |
 v
scope.py
Authorization and scope checking
 |
 v
scheduler.py
Centralized request-rate control
 |
 v
scanner.py
HTTP request engine
 |----------------------|
 v                      v
analyzer.py          adaptive.py
Response             Adaptive rate
classification       controller
 |                      |
 |<---- rate update -----|
 |
 v
reporter.py
JSON / CSV reporting
```

## Project Structure

```text
enhanced-directory-fuzzer/
├── core/
│   ├── __init__.py
│   ├── adaptive.py
│   ├── analyzer.py
│   ├── reporter.py
│   ├── scanner.py
│   ├── scheduler.py
│   └── scope.py
├── demo/
│   └── rate_demo.py
├── lab/
│   └── app.py
├── output/
│   └── .gitkeep
├── tests/
├── wordlists/
│   ├── common.txt
│   ├── adaptive_test.txt
│   └── rate_test.txt
├── main.py
├── requirements.txt
├── LICENSE
└── README.md
```

## Requirements

- Python 3
- httpx
- rich
- flask
- pytest

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the Local Test Lab

The project includes a Flask server for safe local testing.

Start the lab:

```bash
python lab/app.py
```

The server runs at:

```text
http://127.0.0.1:5000
```

Example test routes include:

```text
/admin
/login
/secret
/backup.zip
/rate-limited/<id>
```

The `/rate-limited/<id>` route is used to simulate HTTP 429 responses for testing adaptive rate control.

## Running the Fuzzer

Basic scan:

```bash
python main.py
```

Or specify a wordlist:

```bash
python main.py -w wordlists/common.txt
```

The default target is:

```text
http://127.0.0.1:5000
```

## Command-Line Options

Display help:

```bash
python main.py --help
```

Important options include:

```text
-t, --target
-w, --wordlist
--initial-rate
--max-rate
--timeout
--adaptive
--dry-run
--format
-o, --output-dir
--allow-host
--yes
```

## Live Request-Rate Control

Start a scan with a low request rate:

```bash
python main.py -w wordlists/rate_test.txt --initial-rate 2 --max-rate 20
```

While the scan is running, type a new rate and press Enter:

```text
10
```

The tool updates the active scheduler:

```text
Rate changed to 10 req/s
```

The scan continues without restarting.

## Adaptive Rate Control

Adaptive mode can be enabled using:

```bash
python main.py -w wordlists/adaptive_test.txt --initial-rate 10 --max-rate 20 --adaptive
```

During testing against the local HTTP 429 endpoint, the tool automatically reduced the request rate:

```text
Adaptive rate changed: 10 -> 5 req/s
Adaptive rate changed: 5 -> 2.5 req/s
Adaptive rate changed: 2.5 -> 1.25 req/s
Adaptive rate changed: 1.25 -> 1 req/s
```

This reduces request pressure when the target begins returning rate-limiting responses.

## Response Classification

The analyzer classifies responses into categories such as:

```text
200  FOUND
301  REDIRECT
302  REDIRECT
307  REDIRECT
308  REDIRECT
401  AUTH_REQUIRED
403  FORBIDDEN
404  NOT_FOUND
429  RATE_LIMITED
5xx  SERVER_ERROR
```

A successful response does not automatically indicate a vulnerability. The classification is intended to assist enumeration and analysis.

## Reporting

The tool supports JSON and CSV reporting.

JSON:

```bash
python main.py --format json
```

CSV:

```bash
python main.py --format csv
```

Both:

```bash
python main.py --format both
```

Reports are stored locally in:

```text
output/
```

Example:

```text
output/scan_127.0.0.1_20261119_173906.json
output/scan_127.0.0.1_20261119_173906.csv
```

Only scan metadata is stored. Response bodies, cookies, authentication credentials, and other sensitive response content are not intentionally stored by default.

## Emergency Stop

Press:

```text
Ctrl+C
```

during an active scan.

The tool stops sending further requests and generates a partial report containing the results collected before interruption.

Example:

```text
Kill switch: stopping, no further requests will be sent.

Partial scan summary

NOT_FOUND  7
```

Partial reports are saved using filenames such as:

```text
scan_127.0.0.1_20261119_174013_partial.json
scan_127.0.0.1_20261119_174013_partial.csv
```

## Dry-Run Mode

Use dry-run mode to inspect the planned scan without sending requests:

```bash
python main.py --dry-run
```

Example output:

```text
Dry run: no requests were sent.
```

## Scope Enforcement

The tool uses safe default targets such as localhost and designated testing ranges.

An external target outside the authorized scope is rejected.

Example:

```bash
python main.py -t http://8.8.8.8
```

Output:

```text
Error: Target host '8.8.8.8' is outside the authorized scope.
If you have written permission, add it with --allow-host.
```

Additional hosts should only be added when explicit written authorization exists.

Example syntax:

```bash
python main.py -t http://192.0.2.10 --allow-host 192.0.2.10
```

## Authorization and Legal Notice

The tool displays an authorization notice before scanning.

Users must confirm that they have permission to test the target.

Unauthorized access to computer systems may violate Malaysia's Computer Crimes Act 1997 and other applicable laws.

This project is intended only for:

- Authorized security testing
- Controlled laboratory environments
- Academic cybersecurity research
- Systems owned by the tester
- Systems for which explicit permission has been granted

## Rules of Engagement

Before conducting a scan:

- Confirm the target is within the authorized scope.
- Obtain explicit permission from the system owner.
- Use an agreed testing time window where applicable.
- Begin with a conservative request rate.
- Avoid causing denial of service or service degradation.
- Stop immediately if unexpected instability occurs.
- Do not attempt exploitation unless explicitly authorized.
- Do not attempt authentication bypass.
- Do not exfiltrate sensitive information.
- Store only the minimum information required for testing.

The emergency stop can be activated at any time using Ctrl+C.

## Testing

Run the automated test suite:

```bash
python -m pytest -q
```

Current verified test result:

```text
24 passed
```

Manual integration testing has also verified:

- Standard directory enumeration
- Live request-rate changes during an active scan
- Adaptive reduction after repeated HTTP 429 responses
- HTTP response classification
- JSON report generation
- CSV report generation
- Ctrl+C emergency stop
- Partial report generation
- Dry-run mode
- Unauthorized-scope rejection

## Ethical Design

The project includes several ethical safeguards:

- Authorization confirmation
- Safe localhost default
- Explicit scope validation
- Conservative rate configuration
- Maximum-rate control
- Adaptive rate reduction
- Emergency stop
- Dry-run mode
- Local-only report storage
- Data-minimizing reporting
- No automatic exploitation

The tool is designed for enumeration and defensive security testing rather than exploitation.

## Team Responsibilities

### Zu
Core Scanner and Analyzer

- HTTP request handling
- Wordlist processing
- Response data structure
- Response classification
- Scanner integration

### Irfan
Request Scheduler

- Centralized request-rate scheduler
- Live rate modification
- Rate measurement
- Scheduler testing

### Zaquan
Adaptive Controller

- Response monitoring
- Rate-limit detection
- Latency monitoring
- Adaptive backoff
- Recovery logic

### Haziq
Safety, CLI, Reporting and Lab

- Scope enforcement
- Legal and authorization controls
- CLI integration
- JSON and CSV reporting
- Local Flask testing environment

All team members contributed to integration, testing, documentation and evaluation.

## Attack Lifecycle Mapping

The tool primarily supports the early stages of an authorized security assessment:

```text
Planning and Authorization
          ↓
Reconnaissance
          ↓
Enumeration
          ↓
Analysis
          ↓
Reporting
```

It does not automatically perform exploitation.

## Limitations

Current limitations include:

- The scanner is intended primarily for controlled academic testing.
- It does not perform vulnerability exploitation.
- It does not attempt WAF evasion.
- It does not perform authentication bypass.
- It does not use distributed scanning.
- Adaptive behavior currently focuses on simple observable indicators such as HTTP 429, HTTP 503, response latency and request failures.
- Results should still be reviewed by a human tester.

## Future Improvements

Possible future improvements include:

- Improved concurrency while maintaining centralized rate control
- Interactive terminal dashboard
- Pause and resume support
- Scan checkpointing
- More advanced response similarity analysis
- Additional adaptive-control metrics
- Improved rate visualization
- Expanded integration testing
- Configurable scan profiles

## Disclaimer

This software is provided for educational and authorized security-testing purposes only.

The developers are not responsible for misuse of the tool.

Users are responsible for ensuring that all testing is performed legally, ethically, and with explicit authorization.

## License

This project is licensed under the MIT License.

See:

```text
LICENSE
```

for details.