from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILE = BASE_DIR / "tlevels.db"
PAGES = {"/": "index.html", "/index.html": "index.html", "/page2.html": "page2.html", "/page3.html": "page3.html", "/page4.html": "page4.html"}


def initialize_database():
	with sqlite3.connect(DATABASE_FILE) as database:
		database.execute("CREATE TABLE IF NOT EXISTS interest_submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL, submitted_at TEXT NOT NULL)")
		database.execute("CREATE TABLE IF NOT EXISTS contact_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL, message TEXT NOT NULL, received_at TEXT NOT NULL)")


class WebsiteHandler(BaseHTTPRequestHandler):
	def send_json(self, status, data):
		body = json.dumps(data).encode("utf-8")
		self.send_response(status)
		self.send_header("Content-Type", "application/json; charset=utf-8")
		self.send_header("Content-Length", str(len(body)))
		self.end_headers()
		self.wfile.write(body)

	def do_GET(self):
		path = urlparse(self.path).path
		if path == "/api/health":
			self.send_json(200, {"status": "ok"})
			return

		filename = PAGES.get(path)
		if filename is None:
			self.send_error(404, "Page not found")
			return

		body = (BASE_DIR / filename).read_bytes()
		self.send_response(200)
		self.send_header("Content-Type", "text/html; charset=utf-8")
		self.send_header("Content-Length", str(len(body)))
		self.end_headers()
		self.wfile.write(body)

	def do_POST(self):
		path = urlparse(self.path).path
		length = int(self.headers.get("Content-Length", 0))
		body = self.rfile.read(length).decode("utf-8")
		if self.headers.get("Content-Type", "").startswith("application/json"):
			data = json.loads(body or "{}")
		else:
			data = {key: values[0] for key, values in parse_qs(body).items()}

		if path == "/submit-form":
			name = str(data.get("name", "")).strip()
			email = str(data.get("email", "")).strip()
			if not name or not email:
				self.send_json(400, {"error": "Name and email are required."})
				return
			with sqlite3.connect(DATABASE_FILE) as database:
				database.execute("INSERT INTO interest_submissions (name, email, submitted_at) VALUES (?, ?, ?)", (name, email, datetime.now(timezone.utc).isoformat()))
			self.send_response(303)
			self.send_header("Location", "/page2.html")
			self.end_headers()
			return

		if path != "/api/contact":
			self.send_error(404, "Endpoint not found")
			return

		name = str(data.get("name", "")).strip()
		email = str(data.get("email", "")).strip()
		message = str(data.get("message", "")).strip()
		if not name or not email or not message:
			self.send_json(400, {"error": "Name, email and message are required."})
			return

		with sqlite3.connect(DATABASE_FILE) as database:
			database.execute("INSERT INTO contact_messages (name, email, message, received_at) VALUES (?, ?, ?, ?)", (name, email, message, datetime.now(timezone.utc).isoformat()))
		self.send_json(201, {"message": "Your message has been received."})


if __name__ == "__main__":
	initialize_database()
	print("Website running at http://127.0.0.1:3000")
	HTTPServer(("127.0.0.1", 3000), WebsiteHandler).serve_forever()
