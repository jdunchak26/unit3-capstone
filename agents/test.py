from lambda_handler import handler
event = {"body": '{"question": "How many active projects do we have?"}'}
print(handler(event, None))