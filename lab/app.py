from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "Enhanced Directory Fuzzer Test Server"


@app.route("/admin")
def admin():
    return "Admin Panel"


@app.route("/login")
def login():
    return "Login Page"


@app.route("/secret")
def secret():
    return "Test Secret Page"


@app.route("/backup.zip")
def backup():
    return "FAKE BACKUP FILE FOR LAB TESTING"

@app.route("/rate-limited/<path:test_id>")
def rate_limited(test_id):
    return "Too Many Requests", 429

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )