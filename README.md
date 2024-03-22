# Spellbot

## Getting Started

### Setting up pip

#### Creating a virtual environment

Create a virtual environment in the folder `.venv`

```shell
$ python -m venv .venv
```

#### Enter the environment

```shell
# Linux, Fish
$ source .venv/bin/activate.fish
# Windows, cmd.exe
> .venv\Scripts\activate.bat
# Windows, PowerShell
> .venv\Scripts\activate.ps1
```

#### Install the dependencies

Dependencies required for development

```shell
$ pip install -r dev-requirements.txt
```

Dependencies for running

```shell
$ pip install -r requirements.txt
```

#### Exiting the environment

```shell
$ deactivate
```

### Running the bot

#### Lavalink

For music support you are going to need to download and run Lavalink before starting the bot
For more on Lavalink go to their official repo [here](https://github.com/freyacodes/Lavalink)
Make sure to add the application.yml in the root directory, it should look something like [this](https://github.com/freyacodes/Lavalink/blob/master/LavalinkServer/application.yml.example/)

#### Bot token

Before you run the bot you need to create a file called .env in the root directory.
In this file you need to add your bot's token, the file should look like this

```env
TOKEN="Whatever your token is"
```

#### Running the bot

```shell
# Linux
python3.11 ./src/main.py
# Windows
> py -3.11 .\src\main.py
```

### Before you commit

#### Sort your imports

Call ISort when in the project root via

```shell
$ isort .
```

#### Format your code

Call the Black formatter via

```shell
$ black .
```

#### Lint your code

Run flake8

```shell
$ flake8
```

if it complains fix whatever it complained about

#### Pre-Commit hooks

Install the pre-commit hooks via

```shell
$ pre-commit install
```

once you have done that the pre-commit checks should run before a commit but can be run manually via `pre-commit`
makes sure your code is ok to commit and if it isn't prevents the commit and tells you to fix it
