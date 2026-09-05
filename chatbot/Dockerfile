FROM python:3.10
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements.txt /code/
COPY constraints.txt /code/
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install -U -r constraints.txt
COPY . /code/
