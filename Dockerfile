
FROM python:3.10.4
WORKDIR /main
COPY requirements.txt /main/
RUN pip install -r requirements.txt
COPY . /main
CMD python main.py