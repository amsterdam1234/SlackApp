import os
import traceback
import boto3

from dotenv import load_dotenv
from slack_sdk.web import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.socket_mode.request import SocketModeRequest
from threading import Event
from variables import *

# Load the .env file to get the environment variables
load_dotenv()

try:
    web_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    # Initialize SocketModeClient with an app-level token + WebClient
    client = SocketModeClient(
        # This app-level token will be used only for establishing a connection
        app_token=os.environ["SLACK_APP_TOKEN"],
        # You will be using this WebClient for performing Web API calls in listeners
        web_client=web_client)

except Exception:
    traceback.print_exc()

try:
    aws_session = boto3.Session(region_name='us-east-1')
except Exception:
    traceback.print_exc()

user_name = None

# the path /create_monitoring will trigger the new_create_monitoring function
def new_create_monitoring(req: SocketModeRequest):
    global user_name
    user_name = req.payload['user_name']

    web_client.chat_postMessage(
        channel='C078BQGN1BP',
        text=f"*New process started!*\n Creation bot triggered by user: `{user_name}`"
    )


    # Get all the available resources from the variables.py file
    resources_options = [{"text": {"type": "plain_text", "text": key}, "value": key} for key in resources.keys()]
    # creating the block for the dropdown
    blocks = [
        {
            "type": "input",
            "block_id": "resources-dropdown",
            "dispatch_action": True,
            "element": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a resource type to monitor"
                },
                "options": resources_options,
                "action_id": "resources_options_action"
            },
            "label": {
                "type": "plain_text",
                "text": "Select the resource type to monitor"
            }
        }
    ]
    # Open the modal/form
    try:
        web_client.views_open(
            trigger_id=req.payload["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "resource_first_page",
                "title": {
                    "type": "plain_text",
                    "text": "New Monitoring Creation"
                },
                "submit": {
                    "type": "plain_text",
                    "text": "Next"
                },
                "blocks": blocks
            }
        )
    except Exception as e:
        traceback.print_exc()
        web_client.chat_postMessage(
            channel='C078BQGN1BP',
            text=f"*Exception Occurred!*\n{user_name} Happened during opening the new monitoring view : ```{e}```"
        )


# Handle the path/workflow to process
def pathe_to_process(client: SocketModeClient, req: SocketModeRequest):
    # Send the acknowledgment response
    response = SocketModeResponse(envelope_id=req.envelope_id)
    client.send_socket_mode_response(response)
    # choose the path/workflow to process
    if req.payload.get("command") == "/create_monitoring":
        new_create_monitoring(req)


# Get the list of resources names/IDs by the resource type
def resource_list_names(resource_type):
    if resource_type == 'AWS/ApplicationELB':
        TG_names = []
        try:
            response = aws_session.client('elbv2').describe_target_groups()
            for tg in response['TargetGroups']:
                if tg['Protocol'] in ['HTTP', 'HTTPS']:
                    TG_names.append({
                        "text": {
                            "type": "plain_text",
                            "text": tg["TargetGroupName"]
                        },
                        "value": tg["TargetGroupArn"]
                    })
        except Exception as e:
            print(e)
            web_client.chat_postMessage(
                channel='C078BQGN1BP',
                text=f"*Exception Occurred!*\n{user_name} Received An Error for describe tgs: ```{e}```"
            )
            return
        return TG_names
    elif resource_type == "AWS/EC2":
        EC2_IDs = []
        try:
            instances = aws_session.client('ec2').describe_instances()
            for instance in instances['Reservations']:
                if instance['Instances'][0]['State']['Name'] == 'running':
                    EC2_IDs.append({
                        "text": {
                            "type": "plain_text",
                            "text": instance['Instances'][0]['InstanceId']
                        },
                        "value": instance['Instances'][0]['InstanceId']
                    })
        except Exception as e:
            print(e)
            web_client.chat_postMessage(
                channel='C078BQGN1BP',
                text=f"*Exception Occurred!*\n{user_name} Happened during creation of EC2_IDs list : ```{e}```"
            )
            return
        return EC2_IDs
    elif resource_type == "AWS/RDS":
        RDS_names = []
        try:
            rds = aws_session.client('rds').describe_db_instances()
        except Exception as e:
            print(e)
            web_client.chat_postMessage(
                channel='C078BQGN1BP',
                text=f"*Exception Occurred!*\n{user_name} Happened during creation of RDS_names list : ```{e}```"
            )
            return
        for name in rds["DBInstances"]:
            RDS_names.append({
                "text": {
                    "type": "plain_text",
                    "text": name["DBInstanceIdentifier"]
                },
                "value": name["DBInstanceIdentifier"]
            })
        return RDS_names


# the second page of the modal - choose the resource name and the metrics to monitor
def choose_resource_name_metrics(client: SocketModeClient, req: SocketModeRequest):
    submit_text = ''
    try:
        resource_type = \
            req.payload["view"]["state"]["values"]["resources-dropdown"]["resources_options_action"]["selected_option"][
                "value"]
    except Exception as e:
        traceback.print_exc()
        web_client.chat_postMessage(
            channel='C078BQGN1BP',
            text=f"*Exception Occurred!*\n{user_name} Happened during choosing the resource type : ```{e}```"
        )
    #save the resource type in the global variable
    global resource_type_global
    resource_type_global = resource_type
    # get the list of the resources names/IDs
    options = resource_list_names(resource_type)
    # if no resources to monitor
    if not options:
        blocks = [
            {
                "type": "section",
                "block_id": "section-identifier",
                "text": {
                    "type": "mrkdwn",
                    "text": f'There are no {resource_type} resources to monitor'
                }
            }
        ]
        submit_text = "OK"
    # if resources to monitor
    else:
        submit_text = "Next"
        blocks = [
            # first block for choosing resource name
            {
                "type": "input",
                "block_id": "resource-name-dropdown",
                "dispatch_action": True,
                "element": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": f"Select a {resource_type} name"
                    },
                    "options": options,
                    "action_id": "resource_name_action"
                },
                "label": {
                    "type": "plain_text",
                    "text": f"Select the {resource_type} name"
                }
            }
        ]
        try:
            # second block for choosing the metrics
            blocks.append({
                "type": "input",
                "block_id": "metrics",
                "label": {
                    "type": "plain_text",
                    "text": f"Select the metrics to monitor for {resource_type}"
                },
                "element": {
                    "type": "checkboxes",
                    "action_id": "metrics_action",
                    "options": []
                }
            })

            for metric_dict in resources[resource_type]:
                for metric, description in metric_dict.items():
                    blocks[-1]["element"]["options"].append({
                        "text": {"type": "plain_text", "text": description},
                        "value": metric
                    })
        except Exception:
            traceback.print_exc()
    try:
        web_client.views_open(
            trigger_id=req.payload["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "resource_name_metrics_second_page",
                "title": {
                    "type": "plain_text",
                    "text": "New Monitoring Creation"
                },
                "submit": {
                    "type": "plain_text",
                    "text": submit_text
                },
                "blocks": blocks
            }
        )
    except Exception:
        traceback.print_exc()


# create the form regard the alerts details
def alerts_details(client: SocketModeClient, req: SocketModeRequest, error_messages=None):
    # Extract the submitted values from the request payload
    # extract the checked metrics to monitor
    try:
        # Extract the submitted values from the request payload
        values = req.payload["view"]["state"]["values"]
        # Extract the selected options from the checkboxes
        selected_options = values["metrics"]["metrics_action"]["selected_options"]
        # Extract the values of the selected options, which are the checked metrics to monitor
        checked_metrics = [option["value"] for option in selected_options]
        # extract the resource id/arn
        resource_arn_or_id = values["resource-name-dropdown"]["resource_name_action"]["selected_option"]["value"]
        # extract the resource name
        resource_name = values["resource-name-dropdown"]["resource_name_action"]["selected_option"]["text"]["text"]


    except Exception as e:
        traceback.print_exc()
        web_client.chat_postMessage(
            channel='C078BQGN1BP',
            text=f"*Exception Occurred!*\n{user_name} Happened during extracting the checked metrics : ```{e}```"
        )

    # create the blocks for the alerts details for each alert selected in the selected_options
    # using the dict of the alert variables form the variables.py file
    blocks = []
    # add the resource name and arn/id to the blocks
    blocks.append({
        "type": "section",
        "block_id": "resource-name",
        "text": {
            "type": "mrkdwn",
            "text": f"*Resource details:* \nResource name: `{resource_name}`\nResource id/arn: `{resource_arn_or_id}`"
        }
    })
    # for each metric to monitor create an alert block that will contain the alert details inputs for the user
    for metric in checked_metrics:
        blocks.append({
            "type": "divider"
        })
        blocks.append({
            "type": "section",
            "block_id": f"{metric}-alert",
            "text": {
                "type": "mrkdwn",
                "text": f"• Details for {metric} alert"
            }
        })
        # for each alert variable create an input block for the user to enter the alert details/parameters
        for variable, value in alert_vairables.items():
            # if the value is a list create a dropdown
            if type(value) == list:
                blocks.append({
                    "type": "input",
                    "block_id": f"{metric}-{variable}-dropdown",
                    "dispatch_action": True,
                    "element": {
                        "type": "static_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": f"Select the {variable}"
                        },
                        "options": [{"text": {"type": "plain_text", "text": option}, "value": option} for option in
                                    value],
                        "action_id": f"{metric}-{variable}-action"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": f"Select the {variable}"
                    }
                })
            # if the value is a number create a plain text input
            else:
                blocks.append({
                    "type": "input",
                    "block_id": f"{metric}-{variable}-input",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": f"{metric}-{variable}-action"
                    },
                    "label": {
                        "type": "plain_text",
                        "text": f"Enter the {variable}"
                    }
                })

    # create the alert details blocks
    try:
        web_client.views_open(
            trigger_id=req.payload["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "alerts_details_third_page",
                "title": {
                    "type": "plain_text",
                    "text": "New Monitoring Creation"
                },
                "submit": {
                    "type": "plain_text",
                    "text": "Submit for approval"
                },
                "blocks": blocks
            }
        )
    except Exception as e:
        traceback.print_exc()
        web_client.chat_postMessage(
            channel='C078BQGN1BP',
            text=f"*Exception Occurred!*\n{user_name} Received error during creating the alert details blocks : ```{e}```"
        )

def send_to_aprroval(client: SocketModeClient, req: SocketModeRequest):
    # Extract the submitted values from the request payload
    values = req.payload["view"]["state"]["values"]
    alert_properties = []
    try:
        for key, value in values.items():
            alarm, parameter, _ = key.split('-')
            parameter_value = value[f"{alarm}-{parameter}-action"][
                "value"] if parameter != "alarm condition" and parameter != "Missing data treatment" else \
                value[f"{alarm}-{parameter}-action"]["selected_option"]["value"]

            # Check if the alarm already exists in the list
            for alert in alert_properties:
                if alarm in alert:
                    # If the alarm exists, add the new parameter to it
                    alert[alarm][parameter] = parameter_value
                    break
            else:
                # If the alarm does not exist, create a new dictionary for it
                alert_properties.append({alarm: {parameter: parameter_value}})
    except Exception as e:
        traceback.print_exc()
        web_client.chat_postMessage(
            channel='C078BQGN1BP',
            text=f"*Exception Occurred!*\n{user_name} Happened while extracting the submitted values : ```{e}```"
        )
    # extract the resource name and arn/id
    try:
        # Extract the resource details
        resource_details_text = req.payload['view']['blocks'][0]['text']['text']

        # Split the text by newline to get the resource name and id/arn
        resource_name, resource_id_arn = resource_details_text.split('\n')[1:]

        # Remove the prefix from the resource name and id/arn
        resource_name = resource_name.replace('Resource name: ', '')
        resource_id_arn = resource_id_arn.replace('Resource id/arn: ', '')

    except Exception as e:
        traceback.print_exc()
        web_client.chat_postMessage(
            channel='C078BQGN1BP',
            text=f"*Exception Occurred!*\n{user_name} Happened while extracting the resource name and arnId and  : ```{e}```"
        )

    # extract the requestor details
    # test commit revert
    try:
        # Extract the user ID and username
        user_id = req.payload['user']['id']
    except Exception:
        traceback.print_exc()
    valid_user_input = input_validation(alert_properties)
    if valid_user_input != True:
        create_form_with_error_messages(client, req, valid_user_input)
    else:
        # send the inputs to the approval channel
        blocks = []
        try:
            # Add the request header and the requestor details
            blocks.append(
                {
                    "type": "header",
                    "block_id": "request-header",
                    "text": {
                        "type": "plain_text",
                        "text": "New monitoring creation request"
                    }
                })
            blocks.append(
                {
                    "type": "section",
                    "block_id": "request-header-details",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Requested by <@{user_id}>"
                    }
                })
            # Add the resource name and arn/id to the blocks
            blocks.append({
                "type": "section",
                "block_id": "resource-name",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Resource details:* \n"
                            f"Resource name: "
                            f"``{resource_name}``"
                            f"\nResource id/arn:"
                            f"``{resource_id_arn}``"
                }
            })
            # For each metric to monitor, create an alert block that will contain the alert details inputs for the user
            for alert in alert_properties:
                for metric, parameters in alert.items():
                    #
                    blocks.append({
                        "type": "divider"
                    })
                    blocks.append({
                        "type": "section",
                        "block_id": f"{metric}-alert-header",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"• Details for {metric} alert*"
                        }
                    })
                    # Initialize the fields list
                    fields = []
                    # For each alert variable, create a field with the parameter and its value
                    for parameter, value in parameters.items():
                        fields.append({
                            "type": "mrkdwn",
                            "text": f"*{parameter}:*\n{value}"
                        })
                    # Append a section block with the fields to the blocks list
                    blocks.append({
                        "type": "section",
                        "block_id": f"{metric}-alert-details",
                        "fields": fields
                    })
            # Add the approve and reject buttons
            blocks.append({
                "type": "actions",
                "block_id": "approve-reject",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Approve"
                        },
                        "style": "primary",
                        "value": "approve"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Reject"
                        },
                        "style": "danger",
                        "value": "reject"
                    }
                ]
            })
            # Send the request to the approval channel
            web_client.chat_postMessage(
                channel='C074TASRX7S',
                text="New monitoring creation request",
                blocks=blocks
            )
        except Exception as e:
            traceback.print_exc()
            web_client.chat_postMessage(
                channel='C078BQGN1BP',
                text=f"*Exception Occurred!*\n{user_name} Happened while sending the request to the approval channel : ```{e}```"
            )
        # Send a private message to the user who requested the monitoring creation
        try:
            web_client.chat_postMessage(
                channel=user_id,
                text=f"Your monitoring creation request for {resource_name} has been sent for approval"
            )
        except Exception as e:
            traceback.print_exc()
            web_client.chat_postMessage(
                channel='C078BQGN1BP',
                text=f"*Exception Occurred!*\n{user_name} Happened while sending a private message to the user who requested the monitoring creation : ```{e}```"
            )


def input_validation(alerts_details):
    error_messages = []

    for alert in alerts_details:
        for metric, parameters in alert.items():
            # Check if the parameters are integers
            for parameter, value in parameters.items():
                if parameter not in ['Missing data treatment', 'alarm condition']:
                    is_valid = True  # Initialize the flag as True
                    try:
                        parameters[parameter] = int(value)
                    except ValueError:
                        error_messages.append(
                            f"Invalid input for {parameter} in metric {metric}. It must be an integer.")
                        is_valid = False  # Set the flag as False if a ValueError is raised

                    # Skip the other validations if the input is not valid
                    if not is_valid:
                        continue

                    # validation for 'threshold' when 'alarm condition' is 'less'
                    if parameter == 'threshold' and parameters.get('alarm condition') == 'less' and parameters[
                        'threshold'] <= 0:
                        error_messages.append(
                            f"Invalid 'threshold' for metric {metric}.When 'alarm condition' is 'less', it has to be an integer bigger than 0")

                    # Validate 'threshold'
                    if parameter == 'threshold' and parameters['threshold'] < 0:
                        error_messages.append(f"Invalid 'threshold' for metric {metric}, can't be a negative number")

                    # Validate 'period'
                    if parameter == 'period' and parameters['period'] < 0:
                        error_messages.append(f"Invalid 'period' for metric {metric}, it has to be a positive integer")

                    if parameter == 'period' and parameters['period'] not in [1, 5, 10, 30] and parameters['period'] % 60 != 0:
                        error_messages.append(f"Invalid 'period' for metric {metric}, valid values are 1, 5, 10, 30, or any multiple of 60")

                    # Validate 'evaluation period'
                    if parameter == 'evaluation period' and parameters['evaluation period'] < 0:
                        error_messages.append(
                            f"Invalid 'evaluation period' for metric {metric}, it has to be a positive integer")

                    # Validate that 'datapoints to alarm' isn't bigger than the 'evaluation period'
                    if parameter == 'datapoints to alarm from the evaluation period' and 'evaluation period' in parameters and \
                            parameters['datapoints to alarm from the evaluation period'] > parameters[
                        'evaluation period']:
                        error_messages.append(
                            f"'datapoints to alarm from the evaluation period' cannot be bigger than the 'evaluation period' for metric {metric}")

                    # Validate 'datapoints to alarm from the evaluation period'
                    if parameter == 'datapoints to alarm from the evaluation period' and parameters[
                        'datapoints to alarm from the evaluation period'] < 0:
                        error_messages.append(
                            f"Invalid 'datapoints to alarm from the evaluation period' for metric {metric}")

    if error_messages:
        # print the error messages with a row between each message
        print("\n".join(error_messages))
        return error_messages
    else:
        return True


def button_hide(client: SocketModeClient, req: SocketModeRequest, approved: bool):
    # extract the approver details
    user_id = req.payload['user']['id']

    # Update the message to indicate the request has been approved
    try:
        # Extract the timestamp and channel ID of the original message
        message_ts = req.payload['message']['ts']
        channel_id = req.payload['channel']['id']

        # Update the blocks to change the appearance of the "Approve" button
        blocks = req.payload["message"]["blocks"]
        for block in blocks:
            if block["block_id"] == "approve-reject":
                # Change the type to "context" to remove the button
                block["type"] = "context"
                # deleting the buttons
                block["elements"] = []
                # Add a text to indicate the request has been approved
                if approved:
                    block["elements"].append({
                        "type": "mrkdwn",
                        "text": f"*Request approved* by <@{user_id}>"
                    })
                else:
                    # Add an text input to explain the rejection
                    block["elements"].append({
                        "type": "mrkdwn",
                        "text": f"*Request rejected* by <@{user_id}>"
                    })
        if approved:
            # Update the message
            web_client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text="Request approved",  # Add this line
                blocks=blocks
            )
            send_private_message(client, req, approved)
            web_client.chat_postMessage(
                channel='C078BQGN1BP',
                text=f"{user_name}'s Monitoring Creation request has been approved"
            )
        else:
            # Update the message
            web_client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text="Request rejected",  # Add this line
                blocks=blocks
            )
            # Create a block to ask the user to provide the reason for the rejection
            blocks = []
            # add the resource name and the requester id
            # Extract the resource details
            resource_details_text = req.payload['message']['blocks'][2]['text']['text']

            # Split the text by newline to get the resource name and id/arn
            resource_name, resource_id_arn = resource_details_text.split('\n')[1:]

            # Remove the prefix from the resource name and id/arn
            resource_name = resource_name.replace('Resource name: ', '')
            resource_id_arn = resource_id_arn.replace('Resource id/arn: ', '')

            # extract the user id in the message
            user_id = req.payload['message']['blocks'][1]['text']['text']
            user_id = user_id.replace('Requested by <@', '')
            user_id = user_id.replace('>', '')

            # add the resource name and id/arn to the blocks
            blocks.append({
                "type": "section",
                "block_id": "resource-name",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Resource details:* \nResource name: `{resource_name}`\nResource id/arn: `{resource_id_arn}`"
                }
            })
            # add the requester id to the blocks
            blocks.append({
                "type": "section",
                "block_id": "requester-id",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Requested by <@{user_id}>"
                }
            })
            # ask the user to provide the reason for the rejection

            blocks.append({
                "type": "input",
                "block_id": "rejection-reason",
                "dispatch_action": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": "rejection_reason_action"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Please provide the reason for the rejection"
                }
            })

            web_client.views_open(
                trigger_id=req.payload["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "rejection_reason",
                    "title": {
                        "type": "plain_text",
                        "text": "Rejection Reason"
                    },
                    "submit": {
                        "type": "plain_text",
                        "text": "Submit"
                    },
                    "blocks": blocks
                }
            )
            send_private_message(client, req, approved)
    except Exception as e:
        traceback.print_exc()
        web_client.chat_postMessage(
            channel='C078BQGN1BP',
            text=f"*Exception Occurred!*\n{user_name} Happened during button hide function: ```{e}```"
        )


def send_private_message(client: SocketModeClient, req: SocketModeRequest, approved: bool):
    # Send a private message to the user who requested the monitoring creation
    # Extract the details of the resource
    try:
        # Extract the resource details
        resource_details_text = req.payload['message']['blocks'][2]['text']['text']

        # Split the text by newline to get the resource name and id/arn
        resource_name, resource_id_arn = resource_details_text.split('\n')[1:]

        # Remove the prefix from the resource name and id/arn
        resource_name = resource_name.replace('Resource name: ', '')
        resource_id_arn = resource_id_arn.replace('Resource id/arn: ', '')

        # extract the user id in the message
        user_id = req.payload['message']['blocks'][1]['text']['text']
        user_id = user_id.replace('Requested by <@', '')
        user_id = user_id.replace('>', '')

        # extract the approver id
        admin_id = req.payload['user']['id']
    except Exception as e:
        traceback.print_exc()
        web_client.chat_postMessage(
            channel='C078BQGN1BP',
            text=f"*Exception Occurred!*\n{user_name} Happened while extracting the approver id : ```{e}```"
        )
    if approved:
        try:
            # Send a private message to the user who requested the monitoring creation
            web_client.chat_postMessage(
                channel=user_id,
                text=f"Your monitoring creation request for {resource_name} has been approved by <@{admin_id}> and is "
                     f"now being created"
            )
        except Exception as e:
            traceback.print_exc()
            web_client.chat_postMessage(
                channel='C078BQGN1BP',
                text=f"*Exception Occurred!*\n{user_name} Happened during sending a pm to the user that request is approved : ```{e}```"
            )

    else:
        try:
            # Send a private message to the user who requested the monitoring creation
            web_client.chat_postMessage(
                channel=user_id,
                text=f"Your monitoring creation request for {resource_name} has been rejected by <@{admin_id}>"
            )
        except Exception as e:
            traceback.print_exc()
            web_client.chat_postMessage(
                channel='C078BQGN1BP',
                text=f"*Exception Occurred!*\n{user_name} Happened during process of sending a pm to the user that request is rejected : ```{e}```"
            )


def approve_request(client: SocketModeClient, req: SocketModeRequest):
    try:
        # extract the approver details
        user_id = req.payload['user']['id']
        # Extract the resource details
        resource_details_text = req.payload['message']['blocks'][2]['text']['text']

        # Split the text by newline to get the resource name and id/arn
        resource_name, resource_id_arn = resource_details_text.split('\n')[1:]

        # Remove the prefix from the resource name and id/arn
        resource_name = resource_name.replace('Resource name: ```', '').replace('```', '')
        resource_id_arn = resource_id_arn.replace('Resource id/arn:```', '').replace('```','' )
        #remove the '' from the resource_id_arn and name

        # Initialize the alerts dictionary
        alerts = {}

        # Iterate over the blocks in the message
        for block in req.payload['message']['blocks']:
            # Check if the block is an alert details block
            if block['type'] == 'section' and 'alert-details' in block['block_id']:
                print(block)
                print(block['fields'])
                # Extract the metric from the block_id
                metric = block['block_id'].split('-')[0]
                # Initialize the parameters dictionary
                parameters = {}
                # Iterate over the fields in the block
                for field in block['fields']:
                    # Check if the text contains a newline and a colon
                    if '\n' in field['text'] and ':' in field['text']:
                        # Split the text by newline and colon to get the parameter and its value
                        value = field['text'].split('\n')[1].split(': ')[0]
                        parameter = field['text'].split('\n')[0].replace(':','').replace('*','')

                        # Add the parameter and its value to the parameters dictionary
                        parameters[parameter] = value
                    else:
                        print(f"Unexpected format in field text: {field['text']}")
                # Add the parameters dictionary to the alerts dictionary with the metric as the key
                alerts[metric] = parameters
        print(f"Resource Name: {resource_name}")
        print(f"Resource ID/ARN: {resource_id_arn}")
        print(f"Alerts: {alerts}")
        if user_id in admins:
            # Hide the approve and reject buttons
            button_hide(client, req, True)
            send_put_metric_alarm_request(resource_id_arn, resource_name, alerts)
        else:
            # Reject the request
            button_hide(client, req, False)
    except Exception as e:
        traceback.print_exc()
        web_client.chat_postMessage(
            channel='C078BQGN1BP',
            text=f"*Exception Occurred!*\n{user_name} Happened during approve request function : ```{e}```"
        )
        # Check if the user is an admin


def send_put_metric_alarm_request(resource_id_arn, resource_name, alerts):
    if resource_type_global == 'AWS/EC2':
        dimensions = [
            {
                'Name': 'InstanceId',
                'Value': resource_id_arn
            }
        ]
    elif resource_type_global == 'AWS/ApplicationELB':
        dimensions = [
            {
                'Name': 'TargetGroup',
                'Value': resource_id_arn
            }
        ]
    elif resource_type_global == 'AWS/RDS':
        dimensions = [
            {
                'Name': 'DBInstanceIdentifier',
                'Value': resource_id_arn
            }
        ]
    else:
        raise ValueError("Invalid resource_type. Must be 'EC2', 'ApplicationELB', or 'RDS'.")

    for metric, parameters in alerts.items():
        try:
            aws_session.client('cloudwatch').put_metric_alarm(
                AlarmName=f"{resource_name}-{metric}",
                AlarmDescription=f"Alarm for {metric} on {resource_name}",
                ActionsEnabled=True,
                AlarmActions=[
                    os.environ['SNS_TOPIC_ARN']
                ],
                MetricName=metric,
                Namespace=resource_type_global,
                Statistic='Average',
                Period=int(parameters['period (in seconds)']),
                EvaluationPeriods=int(parameters['evaluation period']),
                Threshold=int(parameters['threshold']),
                ComparisonOperator=parameters['alarm condition'],
                TreatMissingData=parameters['Missing data treatment'],
                DatapointsToAlarm=int(parameters['datapoints to alarm from the evaluation period']),
                Dimensions=dimensions
            )
        except Exception as e:
            print(e)
            web_client.chat_postMessage(
                channel='C078BQGN1BP',
                text=f"*Exception Occurred!*\n{user_name} Received An Error while creating/updating a CW alarm ```{e}```"
            )
            return
    print("Monitoring created successfully")
    web_client.chat_postMessage(
        channel='C078BQGN1BP',
        text=f"`{user_name}`'s Monitoring Creation request for {resource_name} has been created successfully"
    )

def reject_request(client: SocketModeClient, req: SocketModeRequest):
    # extract the approver details
    user_id = req.payload['user']['id']
    # Check if the user is an admin
    if user_id in admins:
        button_hide(client, req, False)
        """david its your part"""


def send_reason(client: SocketModeClient, req: SocketModeRequest):
    try:
        # Check if the rejection reason is provided
        rejection_reason = req.payload["view"]["state"]["values"]["rejection-reason"]["rejection_reason_action"][
            "value"]
        # get the resource name
        resource_name = req.payload["view"]["blocks"][0]["text"]["text"].split("\n")[1].replace("Resource name: ", "")
        # get the requester id
        requester_id = req.payload["view"]["blocks"][1]["text"]["text"].replace("Requested by <@", "").replace(">", "")
    except Exception:
        traceback.print_exc()
    try:
        # Send a private message to the user who requested the monitoring creation
        web_client.chat_postMessage(
            channel=requester_id,
            text=f"reason for the rejection of the monitoring creation request for {resource_name} is: {rejection_reason}"
        )
    except Exception:
        traceback.print_exc()


def create_form_with_error_messages(client: SocketModeClient, req: SocketModeRequest, error_messages=None):
    try:
        # Extract the submitted values from the request payload
        values = req.payload['view']['state']['values']

        # Create the blocks for the form
        blocks = req.payload['view']['blocks']

        # Concatenate all error messages into a single string
        error_text = "\n".join(f"*Error:* {error}" for error in error_messages)

        # check if the error messages block already exists
        for block in blocks:
            if block["type"] == "section" and block["block_id"] == "error-messages":
                block["text"]["text"] = error_text
                break
        else:
            # Create a single block with all the error messages
            blocks.insert(1, {
                "type": "section",
                "block_id": "error-messages",
                "text": {
                    "type": "mrkdwn",
                    "text": error_text
                }
            })
        # Iterate over the blocks
        for block in blocks:
            # Check if the block is an input block
            if block["type"] == "input":
                # Extract the action_id of the input element
                action_id = block["element"]["action_id"]
                if block["element"]["type"] == "plain_text_input":
                    # Replace '-action' with '-input' in the action_id
                    action_id = action_id.replace('-action', '-input')
                else:
                    action_id = action_id.replace('-action', '-dropdown')
                # Check if the user has submitted a value for this input field
                if action_id in values:
                    # Check the type of the element
                    if block["element"]["type"] == "plain_text_input":
                        # Set the initial value of the input field to the user's input
                        block["element"]["initial_value"] = values[action_id][action_id.replace('-input', '-action')][
                            'value']

                    elif block["element"]["type"] == "static_select":
                        # Set the initial option of the select field to the user's selection
                        block["element"]["initial_option"] = \
                        values[action_id][action_id.replace('-dropdown', '-action')]['selected_option']

    except Exception as e:
        traceback.print_exc()
        web_client.chat_postMessage(
            channel='C078BQGN1BP',
            text=f"*Exception Occurred!*\n{user_name} Happened while creating the form with the error messages : ```{e}```"
        )

    # Create the form with the blocks
    try:
        # Open the form with the error messages
        web_client.views_open(
            trigger_id=req.payload["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "alerts_details_third_page_error",
                "title": {
                    "type": "plain_text",
                    "text": "New Monitoring Creation",
                    "emoji": True
                },
                "submit": {
                    "type": "plain_text",
                    "text": "Submit for approval",
                    "emoji": True
                },
                "blocks": blocks
            }
        )
    except Exception as e:
        traceback.print_exc()
        web_client.chat_postMessage(
            channel='C078BQGN1BP',
            text=f"*Exception Occurred!*\n{user_name} Happened while opening the form with the error messages : ```{e}```"
        )


# Handle view_submission event
def view_submission_listener(client: SocketModeClient, req: SocketModeRequest):
    if req.payload.get("type") == "view_submission" and req.payload["view"]["callback_id"] == "resource_first_page":
        choose_resource_name_metrics(client, req)
    if req.payload.get("type") == "view_submission" and req.payload["view"][
        "callback_id"] == "resource_name_metrics_second_page":
        alerts_details(client, req)
    if req.payload.get("type") == "view_submission" and (req.payload["view"][
                                                             "callback_id"] == "alerts_details_third_page" or
                                                         req.payload["view"][
                                                             "callback_id"] == "alerts_details_third_page_error"):
        send_to_aprroval(client, req)
    # accept the request
    if req.payload.get("type") == "block_actions" and req.payload["actions"][0]["value"] == "approve":
        approve_request(client, req)
    # reject the request
    if req.payload.get("type") == "block_actions" and req.payload["actions"][0]["value"] == "reject":
        reject_request(client, req)
    # provide the reason for the rejection or close the modal
    if req.payload["view"]["callback_id"] == "rejection_reason" and req.payload.get("type") == "view_submission":
        send_reason(client, req)

    # response for slack
    response = SocketModeResponse(envelope_id=req.envelope_id)
    client.send_socket_mode_response(response)


# Add the listener for opening the modal
client.socket_mode_request_listeners.append(pathe_to_process)
# Add the listener for handling the form submission
client.socket_mode_request_listeners.append(view_submission_listener)

# Establish a WebSocket connection to the Socket Mode servers
client.connect()
# Keep the program running
Event().wait()
