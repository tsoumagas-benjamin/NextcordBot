
FROM python:3.10-alpine
WORKDIR /main
COPY requirements.txt /main/
RUN pip install -r requirements.txt
RUN apk add ffmpeg
COPY . /main
CMD python main.py