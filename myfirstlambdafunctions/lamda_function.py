import json

def lambda_handler(event, context):
    # Check the HTTP method

    if event.get('httpMethod') == 'GET':
        # Access query parameters
        #params = event.get('queryStringParameters', {})
        # hub_mode = params.get('hub.mode')
        # hub_token = params.get('hub.verify_token')
        #hub_challenge = params.get('hub.challenge')
        hub_challenge = 'trial'
     
        eventhttp = str(event)
        return {
                "statusCode": 200,
                "body": eventhttp
           
                
            }
        
        # Validate the subscription request
        if hub_mode == 'subscribe' and hub_token == 'fdcDX1s@dc0c70e27e':
            return {
                "statusCode": 200,
                "body": hub_challenge
            }
        
        # Respond with 404 if tokens do not match
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Invalid token"})
        }
    
    
    if event.get('httpMethod') == "POST":
        try:
            notification = event
            print(notification)
            
           
           

            # Get notification type
            if notification.get('entry', [])[0].get('changes', [])[0].get('value', {}).get('messages'):
                print(notification)
                # TODO get response status from handleMessage
                # handleMessage only handles Received Messages notifications
                #handleMessage(
                #    notification=notification,
                #    business=business
                #)

            if notification.get('entry', [])[0].get('changes', [])[0].get('value', {}).get('statuses'):
                # TODO handleConversation only handles Message Status notifications
                pass

        except Exception as e:
           return {
                "statusCode": 200,
                "body": json.dumps({"error": "Wrong Payload"})
            }


        # TODO change endpoint response
        return {"Hola" : "Hola"}, 200
        
    # Default response for non-GET methods or other errors
    return {
        "statusCode": 500,
        "body": json.dumps({"error": "Server error"})
    }


