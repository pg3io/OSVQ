FROM python:3

ADD ./requirements.txt .
RUN pip3 install -r requirements.txt

RUN mkdir /app
ADD . /app
WORKDIR /app
VOLUME [ "/app/data" ]

CMD ["python3", "-m", "flask", "run", "--host", "0.0.0.0"]
