# Enhanced Directory Fuzzer

A Python-based web directory enumeration tool developed for the
IKB31603 Ethical Hacking course at UniKL MIIT.

The project extends traditional directory fuzzing by introducing
real-time and adaptive request-rate control. The scanner can adjust
its request rate during an active scan based on observed server
conditions such as response latency, HTTP 429 responses, timeouts,
and server errors.

> This tool is intended strictly for authorized security testing
> and educational use.

---

## Features

- Web directory and file enumeration
- Wordlist-based scanning
- HTTP response classification
- Shared request-rate scheduler
- Real-time request-rate adjustment
- Adaptive rate control
- Response latency monitoring
- HTTP 429 and server-error detection
- Configurable request timeout
- Reusable HTTP client
- Local testing environment
- Automated testing with pytest

Additional safety, reporting, and CLI functionality will be documented
as integration is completed.

---

## Project Architecture

```text
User / CLI
    |
    v
Scope & Authorization
    |
    v
Scanner
    |
    v
Request Scheduler
    |
    +-----------------------+
    |                       |
    v                       |
HTTP Request                |
    |                       |
    v                       |
HTTP Response               |
    |                       |
    +----> Adaptive Controller
    |              |
    |              +----> Adjust Request Rate
    |
    v
Response Analyzer
    |
    v
Reporter
```

---

## Project Structure

```text
enhanced-directory-fuzzer/
├── core/
│   ├── analyzer.py
│   ├── scanner.py
│   ├── scheduler.py
│   ├── adaptive.py
│   ├── scope.py
│   └── reporter.py
├── demo/
│   └── rate_demo.py
├── lab/
│   └── app.py
├── tests/
├── wordlists/
│   └── common.txt
├── output/
├── main.py
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

---

## Installation

### Requirements

- Python 3
- pip
- Git

Clone the repository:

```bash
git clone <repository-url>
cd enhanced-directory-fuzzer
```

Create a virtual environment:

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Linux / Kali Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Local Testing Lab

A local Flask application is provided for safe testing.

Start the test server:

```bash
python lab/app.py
```

The test application runs on:

```text
http://127.0.0.1:5000
```

Example test endpoints include:

```text
/admin
/login
/secret
/backup.zip
```

Testing should be performed against the provided local environment
unless explicit authorization has been obtained for another target.

---

## Running the Tool

> This section will be finalized after CLI integration.

The intended final execution command is:

```bash
python main.py
```

The scanner should support configuration such as:

- Target URL
- Wordlist
- Initial request rate
- Maximum request rate
- Request timeout
- Adaptive mode

---

## Adaptive Request-Rate Control

The primary enhancement of this project is the ability to modify the
request rate while scanning.

Traditional directory fuzzers commonly operate using a configured
request rate or concurrency level. This project introduces a shared
scheduler that allows the rate to be modified while the scan is
running.

The adaptive controller can monitor indicators such as:

- Response latency
- HTTP 429 responses
- HTTP 5xx responses
- Request timeouts

When signs of server stress or rate limiting are detected, the
controller can recommend a lower request rate. When conditions become
stable, the rate can gradually recover within the configured limit.

---

## Response Classification

Scanner responses are classified into categories such as:

| HTTP Status | Classification |
|---|---|
| 200 | FOUND |
| 301/302/307/308 | REDIRECT |
| 401 | AUTH_REQUIRED |
| 403 | FORBIDDEN |
| 404 | NOT_FOUND |
| 429 | RATE_LIMITED |
| 5xx | SERVER_ERROR |
| Request failure | ERROR |

A discovered resource does not automatically indicate a security
vulnerability.

---

## Testing

Run the automated test suite with:

```bash
python -m pytest -q
```

During current integration testing:

```text
24 passed
```

Some scanner tests require the local Flask test server to be running
at `127.0.0.1:5000`.

---

## Rules of Engagement

This tool must only be used against systems that the tester owns or
has explicit permission to assess.

### Permitted

- Authorized directory and file enumeration
- Localhost testing
- Controlled HTTP request-rate testing
- Collection of basic HTTP response metadata

### Prohibited

- Unauthorized scanning
- Denial-of-service activity
- Credential attacks
- Exploitation without explicit authorization
- Extraction of sensitive information
- Scanning systems outside the approved scope

### Scope

Before scanning, users should confirm:

1. The target is explicitly authorized.
2. The target is within the agreed testing scope.
3. Testing occurs during the permitted time window.
4. The configured request rate will not intentionally disrupt the target.

### Emergency Stop

An active scan must be stoppable using:

```text
Ctrl+C
```

The application should terminate cleanly without continuing background
requests.

---

## Ethical and Legal Notice

This project was developed for educational and authorized security
testing purposes.

Users are responsible for ensuring that they have explicit
authorization before testing any system. Unauthorized access or
interference with computer systems may violate applicable laws,
including Malaysia's Computer Crimes Act 1997.

The developers are not responsible for misuse of this software.

---

## License

This project is distributed under the license included in the
`LICENSE` file.

---

## Disclaimer

This software is provided for educational purposes and authorized
security testing only. Do not use it against systems without explicit
permission.
```
