
FROM python:3.10.4
WORKDIR /main
COPY requirements.txt /main/
RUN pip install -r requirements.txt
RUN  apt-get -y update && apt-get install -y ffmpeg 
COPY . /main
CMD python main.py