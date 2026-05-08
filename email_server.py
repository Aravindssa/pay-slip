"""
Payroll Email Server - Sends payslips via Gmail SMTP
Run this before using the Send feature: python email_server.py
Uses Gmail App Password for authentication.

To get a Gmail App Password:
1. Go to https://myaccount.google.com/apppasswords
2. Select 'Mail' and your device
3. Copy the 16-character password
4. Paste it in the Excel sheet under 'SMTP Password'
"""

import json
import smtplib
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

PORT = 3000


class EmailHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path == "/health":
            self.respond(200, {"status": "running"})
            return

        if self.path != "/send-payslip":
            self.respond(404, {"success": False, "error": "Not found"})
            return

        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)
        data = json.loads(body)

        smtp = data.get("smtp", {})
        to_email = data.get("to", "")
        subject = data.get("subject", "")
        html_body = data.get("body", "")
        pdf_base64 = data.get("pdfBase64", "")
        pdf_filename = data.get("pdfFilename", "payslip.pdf")

        host = smtp.get("SMTP Host", "smtp.gmail.com")
        port = int(smtp.get("SMTP Port", 587))
        user = smtp.get("SMTP User", "")
        password = smtp.get("SMTP Password", "")
        sender_name = smtp.get("Sender Name", "HR Department")
        sender_email = smtp.get("Sender Email", user)

        if not user or not password:
            self.respond(400, {"success": False, "error": "Gmail credentials missing in Excel sheet"})
            return

        try:
            msg = MIMEMultipart()
            msg["From"] = f"{sender_name} <{sender_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(html_body, "html"))

            if pdf_base64:
                pdf_bytes = base64.b64decode(pdf_base64)
                pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
                pdf_attachment.add_header("Content-Disposition", "attachment", filename=pdf_filename)
                msg.attach(pdf_attachment)

            if port == 465:
                server = smtplib.SMTP_SSL(host, port)
            else:
                server = smtplib.SMTP(host, port)
                server.starttls()

            server.login(user, password)
            server.sendmail(sender_email, to_email, msg.as_string())
            server.quit()

            print(f"[OK] Payslip sent to {to_email} ({pdf_filename})")
            self.respond(200, {"success": True})

        except smtplib.SMTPAuthenticationError:
            print(f"[ERROR] Gmail authentication failed for {user}")
            self.respond(401, {"success": False, "error": "Gmail authentication failed. Check email/app password in Excel."})
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            self.respond(500, {"success": False, "error": str(e)})

    def respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    print("=" * 50)
    print("  PAYROLL EMAIL SERVER")
    print("=" * 50)
    print(f"\n  Running on http://localhost:{PORT}")
    print("  Sends payslips via Gmail SMTP with PDF attached")
    print("\n  Keep this running while using the payslip manager.")
    print("  Press Ctrl+C to stop.\n")
    print("=" * 50 + "\n")

    server = HTTPServer(("localhost", PORT), EmailHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
