FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Data volume for SQLite
RUN mkdir -p /data/testmailbox
VOLUME /data/testmailbox

# API port
EXPOSE 8501
# SMTP port
EXPOSE 2525

ENV DB_PATH=/data/testmailbox/mailbox.db
ENV API_PORT=8501
ENV SMTP_PORT=2525
ENV DOMAIN=testmailbox.dev

CMD ["python", "run.py"]
