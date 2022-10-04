FROM python:3.10-alpine

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

EXPOSE 8081

ENTRYPOINT [ "./scripts/start_server.sh" ]
