# resources = {resource type : [{name of the metric in aws side: description of the metric that will be shown in the form}]}
resources = {
    'AWS/ApplicationELB': [{'HTTPCode_Target_4XX_Count': "HTTP 4XX backend error"},
            {"HTTPCode_Target_5XX_Count": "HTTP 5XX backend error"}, {'RequestCount': "Request Count"},
            {'UnHealthyHostCount': "UnHealthy Host Count"}, {'HealthyHostCount': "Healthy Host Count"}],
    'AWS/EC2': [{'CPUUtilization': "CPU Utilization"}, {'NetworkIn': "Network In"}, {'NetworkOut': "Network Out"},
                {'StatusCheckFailed_Instance': "Status Check Failed Instance"},
                {'StatusCheckFailed_System': "Status Check Failed System"}],
    'AWS/RDS': [{'CPUUtilization': "CPU Utilization"}, {'DatabaseConnections': "Database Connections"},
                {'FreeStorageSpace': "Free Storage Space"}, {'ReadIOPS': "Read IOPS"}, {'WriteIOPS': "Write IOPS"}]
}

# alet variables = {variable name: value, variable name: value, variable name: value}
alert_vairables = {'alarm condition': ['GreaterThanThreshold', 'GreaterThanOrEqualToThreshold', 'LessThanThreshold', 'LessThanOrEqualToThreshold'],
                   'threshold': 0,
                   'period (in seconds)': 0,
                   'evaluation period': 0,
                   'datapoints to alarm from the evaluation period': 0,
                   'Missing data treatment': ['breaching: Treat missing data as alarm',
                                              'notBreaching: Treat missing data as ok',
                                              'ignore: keep alarm state unchanged',
                                              'missing: Treat missing data missing data'],
                   }

admins = ['U033L0LJQ3V', 'U02FNG26P6V', 'U03F71FQYBU']
