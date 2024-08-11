# SlackBot

## Description

This project is a Python application that interacts with AWS services and Slack. It allows users to create monitoring
alerts (CW - CloudWatch) for AWS resources through a Slack bot. The bot communicates with the user through Slack,
collects necessary information, and creates the appropriate CloudWatch alarms.

## Architecture

The application uses a WebSocket connection to communicate with the Slack SDK. It listens for events from Slack,
processes them, and sends responses back through the WebSocket connection. The application uses the Slack's Socket Mode,
which allows it to receive events directly via a WebSocket connection.

The application also interacts with AWS services. It uses the AWS SDK to create and manage CloudWatch alarms based on
the information collected from the user through Slack.

![Architecture.png](photos%2FArchitecture.png)

## Installation

1. Clone the repository to your local machine.
2. Install the necessary Python packages by running `pip install -r requirements.txt`.
3. create .env file in the root directory of the project and add the required environment variables. (See below)

## Environment Variables

The following environment variables are required for the application to run:

- `SLACK_APP_TOKEN`: Your Slack App Token.
- `SLACK_BOT_TOKEN`: Your Slack Bot Token.
- `SNS_TOPIC_ARN`: The ARN of the SNS Topic for alarm notifications.

These can be set in a `.env` file in the root directory of the project.

## AWS Configuration

The application uses the default AWS profile configured on your machine. Make sure to configure your AWS credentials
before running the application. You can do this by running `aws configure` in your terminal and following the prompts.

## Usage

The application can be run with the command `python main.py`. Once running, the bot can be interacted with in Slack.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

