# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.8-slim-buster

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /admin-shuffle
COPY . /admin-shuffle

# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
RUN useradd admin-shuffler && chown -R admin-shuffler /admin-shuffle
USER admin-shuffler

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "Bot.py"]
