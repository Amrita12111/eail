
import smtplib
from queue import Queue
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import pickle
import re
import signal
import threading
import time
# Install the 'dotenv' module using pip:
# pip install python-dotenv

from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('email_queue.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(file_handler)

class EmailQueue:
    def __init__(self, retry_count=3, queue_file='email_queue.pkl', num_threads=5):
        self.queue = Queue()
        self.retry_count = retry_count
        self.queue_file = queue_file
        self.num_threads = num_threads
        self._load_queue()

    def enqueue_email(self, subject, body, to_email):
        if self._is_valid_email(to_email):
            email_task = {
                "subject": subject,
                "body": body,
                "to_email": to_email,
                "retries": 0
            }
            self.queue.put(email_task)
            logging.info(f"Email to {to_email} enqueued.")
            self._save_queue()
        else:
            logging.error(f"Invalid email address: {to_email}")

    def send_email(self, from_email, password, smtp_server="smtp.gmail.com", smtp_port=587):
        def worker():
            while not self.queue.empty():
                email_task = self.queue.get()
                self._send_single_email(from_email, password, smtp_server, smtp_port, email_task)
                self.queue.task_done()
                self._save_queue()

        threads = []
        for _ in range(self.num_threads):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

    def _send_single_email(self, from_email, password, smtp_server, smtp_port, email_task):
        subject = email_task["subject"]
        body = email_task["body"]
        to_email = email_task["to_email"]
        retries = email_task["retries"]

        message = MIMEMultipart()
        message["From"] = from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(from_email, password)
                server.sendmail(from_email, to_email, message.as_string())
            logging.info(f"Email sent to {to_email}")
            # Print the sent email details to the console
            print(f"Email sent to {to_email}")
            print(f"Subject: {subject}")
            print(f"Body: {body}")
        except Exception as e:
            logging.error(f"Failed to send email to {to_email}: {str(e)}")
            if retries < self.retry_count:
                email_task["retries"] += 1
                self.queue.put(email_task)
                logging.info(f"Retrying email to {to_email} ({email_task['retries']} of {self.retry_count})")
                time.sleep(5)  # Delay before retrying
            else:
                logging.error(f"Giving up on email to {to_email} after {self.retry_count} retries")

    def _is_valid_email(self, email):
        regex = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
        return re.match(regex, email) is not None

    def _save_queue(self):
        with open(self.queue_file, 'wb') as f:
            pickle.dump(list(self.queue.queue), f)
        logging.debug("Queue state saved.")

    def _load_queue(self):
        if os.path.exists(self.queue_file):
            with open(self.queue_file, 'rb') as f:
                email_list = pickle.load(f)
                for email_task in email_list:
                    self.queue.put(email_task)
            logging.debug("Queue state loaded.")

def save_queue_on_exit(signum, frame):
    email_queue._save_queue()
    logging.info("Queue saved on exit.")
    exit(0)

signal.signal(signal.SIGINT, save_queue_on_exit)
signal.signal(signal.SIGTERM, save_queue_on_exit)



# Example usage:
if __name__ == "__main__":
    email_queue = EmailQueue(retry_count=3, num_threads=5)
    # Add emails to the queue
    email_queue.enqueue_email("Test Subject 1", "This is the body of email 1", "recipient120@gmail.com")
    email_queue.enqueue_email("Test Subject 2", "This is the body of email 2", "itsmee210021@gail.com")
    email_queue.enqueue_email("Test Subject 3", "This is the body of email 3", "invalid-email")
    
    # Set the 'from_email' variable using the environment variable 'EMAIL_ADDRESS'
    from_email = os.getenv('amritap200318@gailcom')
    password = os.getenv('Amrita2003')
    smtp_server = os.getenv('SMTP_SERVER', "smtp.gmail.com")
    smtp_port = int(os.getenv('SMTP_PORT', 587))

    # Call send_email method with email_queue
    email_queue.send_email(from_email, password, smtp_server, smtp_port)
