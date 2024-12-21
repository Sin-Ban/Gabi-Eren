FROM python:3.10.14-slim-buster
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y ffmpeg && apt-get install -y neofetch
RUN pip3 install -U pip
RUN apt-get install -y git
RUN mkdir /erenjaeger/
COPY . /erenjaeger
WORKDIR /erenjaeger
RUN pip3 install -r requirements.txt
RUN wget https://github.com/PAINBOI2008/PyMoe/releases/download/2.2/pymoe-2.2-py3-none-any.whl
RUN pip install pymoe-2.2-py3-none-any.whl
RUN rm pymoe-2.2-py3-none-any.whl
CMD ["python3", "-m", "FoundingTitanRobot"]
