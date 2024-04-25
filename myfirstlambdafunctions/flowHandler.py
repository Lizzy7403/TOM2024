import datetime
import time

from flask import current_app
from flask_pymongo import ObjectId

from . import flowBuilders
from .flowBuilders import flow_builders
from .collections import nodesCollection, nodeTypeCollection, logsCollection, flowsCollection
from .collections import whatsappAccountsCollection, conversationCategoriesCollection, chatsCollection
from .whatsappAPI import sendMessage
from .notificationHandlers import handleNotification
from .conversationHandlers import findContactByPhoneNumber, findChatByContact, chargeConversationByCategory

def handleMessage(notification, business):
    try:
        # Get notification type
        notification_type = notification.get('entry', [])[0].get('changes', [])[0].get('value', {}).get('messages', [])[0].get('type', None)

        # Get notification's whatsapp account
        phone_number_id  = notification.get('entry', [])[0].get('changes', [])[0].get('value', {}).get('metadata', {}).get('phone_number_id')
        whatsapp_account = whatsappAccountsCollection.find_one({"business" : business.get("_id"), "whatsapp_number_id" : phone_number_id})

        # Get phone number and name
        phone_number  = notification.get('entry', [])[0].get('changes', [])[0].get('value', {}).get('contacts', [])[0].get('wa_id', None)
        name          = notification.get('entry', [])[0].get('changes', [])[0].get('value', {}).get('contacts', [])[0].get('profile', {}).get("name", "")

        # Find contact by wa_id and create contact if contact does not exist
        contact = findContactByPhoneNumber(phone_number=phone_number, business=business, name=name, whatsapp_account=whatsapp_account)
        
        # Find chat by contact or create chat if chat does not exist
        chat = findChatByContact(contact=contact, business=business, whatsapp_account=whatsapp_account)

        # TODO mark chat as unread

        # Calculate the conversation's charge based on category
        # TODO implement new WhatsApp API logic
        conversation_category = conversationCategoriesCollection.find_one({"category" : "Service"})
        chargeConversationByCategory(chat=chat, business=business, category=conversation_category, whatsapp_account=whatsapp_account)
        
        # TODO handle all received message types. See https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
        user_answer  = handleNotification(
            notification=notification,
            notification_type=notification_type,
            chat=chat,
            whatsapp_account=whatsapp_account
        )

        # TODO modify messageHandler to handle only next nodes
        # TODO check that chat does not have a current_node or flow attribute
        # Check if chat is assigned to bot
        if chat.get('automation'):
            # Get businesse's keywords
            keywords = whatsapp_account.get("keywords")

            # If automation has not been triggered yet and keyword is detected, send the corresponding flow
            if not chat.get("automation_triggered") and keywords.get(user_answer, False) != False:
                # Find flow by keyword
                flow = flowsCollection.find_one({'_id' : ObjectId(keywords.get(user_answer)) })

                # Find starting node from flow
                chat['flow']                 = flow.get('_id')
                chat['current_node']         = nodesCollection.find_one({'flow' : flow.get('_id'), 'starting_node' : True }).get('_id')
                chat['automation_triggered'] = True
                chat['automation_started']   = False

                chatsCollection.replace_one({'_id' : chat.get('_id')}, chat)

                # Get current node
                current_node = chat.get("current_node")
                current_node = nodesCollection.find_one({'_id' : current_node})

            # If automation has not been triggered but keyword is not detected
            elif not chat.get("automation_triggered") and keywords.get(user_answer, False) == False:
                flow = flowsCollection.find_one({'_id' : ObjectId(whatsapp_account.get("default_flow")) })

                chat['flow']                 = flow.get('_id')
                chat['current_node']         = nodesCollection.find_one({'flow' : flow.get('_id'), 'starting_node' : True }).get('_id')
                chat['automation_triggered'] = True
                chat['automation_started']   = False

                chatsCollection.replace_one({'_id' : chat.get('_id')}, chat)

                # Get chat's current node
                current_node = chat.get("current_node")
                current_node = nodesCollection.find_one({'_id' : current_node})

            # If automation has been triggered and business has selected to stop automation on keywords and keyword is detected
            elif chat.get("automation_triggered") and whatsapp_account.get("stop_automation_on_keywords") and (keywords.get(user_answer, False) != False):
                # Find flow by keyword
                flow = flowsCollection.find_one({'_id' : ObjectId(keywords.get(user_answer)) })

                if flow:
                    # Find starting node from flow 
                    chat['flow']                 = flow.get('_id')
                    chat['current_node']         = nodesCollection.find_one({'flow' : flow.get('_id'), 'starting_node' : True }).get('_id')
                    chat['automation_triggered'] = True
                    chat['automation_started']   = False

                    chatsCollection.replace_one({'_id' : chat.get('_id')}, chat)

                    # Get current node
                    current_node = chat.get("current_node")
                    current_node = nodesCollection.find_one({'_id' : current_node})
                
                else: 
                    flow = flowsCollection.find_one({'_id' : ObjectId(whatsapp_account.get("default_flow")) })

                    chat['flow']                 = flow.get('_id')
                    chat['current_node']         = nodesCollection.find_one({'flow' : flow.get('_id'), 'starting_node' : True }).get('_id')
                    chat['automation_triggered'] = True
                    chat['automation_started']   = False

                    chatsCollection.replace_one({'_id' : chat.get('_id')}, chat)

                    # Get chat's current node
                    current_node = chat.get("current_node")
                    current_node = nodesCollection.find_one({'_id' : current_node})

            # If automation has been triggered
            else:
                # If automation has been triggered already, get the chat's current node
                current_node = chat.get("current_node")
                current_node = nodesCollection.find_one({'_id' : current_node})
            
            if current_node.get('expected_types') and notification_type in current_node.get('expected_types'):
                # Evaluate if node takes variables
                if current_node.get("variable"):
                    chat["variables"][current_node.get("variable")] = user_answer
                    chatsCollection.replace_one({"_id" : chat.get("_id")}, chat)
                
                current_node, user_answer = messageHandler(
                    current_node=current_node,
                    user_answer=user_answer,
                    chat=chat,
                    contact=contact,
                    business=business,
                    whatsapp_account=whatsapp_account,
                    resend_current_node=False
                )

                # Handle nodes that do not need user answer
                # TODO Include inside loop? Maybe for API call nodes?
                while current_node and not current_node.get("wait_answer"):
                    if current_node.get("variable"):
                        chat["variables"][current_node.get("variable")] = user_answer
                        chatsCollection.replace_one({"_id" : chat.get("_id")}, chat)

                    current_node, user_answer = messageHandler(
                        current_node=current_node,
                        user_answer=user_answer,
                        chat=chat,
                        contact=contact,
                        business=business,
                        whatsapp_account=whatsapp_account,
                        resend_current_node=False
                    )
            
            else:
                logsCollection.insert_one({
                    "user" : "",
                    "date" : datetime.datetime.now(),
                    "description" : "Didn't find expected_types",
                    "ip" : ""
                })
                
                # TODO use default answer from current node
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": contact.get("wa_id"),
                    "type": "text",
                    "text": {
                        "preview_url": False,
                        "body": whatsapp_account.get("wrong_answer_message")
                    }
                }

                sendMessage(
                    payload=payload,
                    business=business,
                    chat=chat,
                    whatsapp_account=whatsapp_account
                )

                # TODO resend current node
                current_node, user_answer = messageHandler(
                    current_node=current_node,
                    user_answer=user_answer,
                    chat=chat,
                    contact=contact,
                    business=business,
                    whatsapp_account=whatsapp_account,
                    resend_current_node=True
                )

        else:
            # TODO send messages to agent
            pass
    except Exception as e:
        logsCollection.insert_one({
            "user" : "",
            "date" : datetime.datetime.now(),
            "description" : f"Error while executing the handleMessage function: {e}",
            "ip" : ""
        })

def messageHandler(current_node, user_answer, chat, contact, business, whatsapp_account, resend_current_node):
    try:
        # Check if current node is the starting_node if so, send current node data
        if current_node.get("starting_node") and not chat.get("automation_started"):
            next_node = current_node
        
            # Update chat's automation status
            chat["automation_started"] = True
            chatsCollection.replace_one({'_id' : chat.get('_id')}, chat)
            
        elif resend_current_node:
            next_node = current_node

        else:
            # Get next node
            next_node = current_node.get("possible_answers").get(user_answer, None) if "Any" not in current_node.get("possible_answers").keys() else current_node.get("possible_answers").get("Any", None)
            next_node = nodesCollection.find_one({"_id" : next_node})

        if next_node:
            # Get necessary data from next node
            next_node_type       = nodeTypeCollection.find_one({'_id' : next_node.get('type')})
            next_node_parameters = next_node.get("parameters")

            # Update chat's current node
            chat["current_node"] = next_node.get('_id')
            chatsCollection.replace_one({'_id' : chat.get('_id')}, chat)

            # Get next node builder
            next_node_builder = next_node_type.get('builder')

            # TODO check if next node is in chat flow
            payload, user_answer = flow_builders.get(next_node_builder)(
                parameters=next_node_parameters,
                to=contact.get("wa_id"),
                chat=chat,
                user_answer=user_answer,
                current_node=next_node
            )

            if payload:
                sendMessage(
                    payload=payload,
                    business=business,
                    chat=chat,
                    whatsapp_account=whatsapp_account
                )

                # Handle nodes that take longer to send before sending the next nodes
                if next_node.get("wait_to_be_sent", False):
                    time.sleep(5)

            # Handle final nodes (has no possible answers) by making automation = true, automation_triggered = False and automation_started = False
            if len(next_node.get("possible_answers", [])) == 0 and chat.get("automation") != False:
                chat["automation"]           = True
                chat["automation_triggered"] = False
                chat["automation_started"]   = False
                chatsCollection.replace_one({'_id' : chat.get('_id')}, chat)

            # Add if user_answer:
            
            return next_node, user_answer

        else:
            logsCollection.insert_one({
                "user" : "",
                "date" : datetime.datetime.now(),
                "description" : f"Didn't find next_node with answer: {user_answer}",
                "ip" : ""
            })

            # TODO use current node's default answer
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": contact.get("wa_id"),
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": whatsapp_account.get("wrong_answer_message")
                }
            }

            sendMessage(
                payload=payload,
                business=business,
                chat=chat,
                whatsapp_account=whatsapp_account
            )

            # TODO Send current node's default message
            # Resend current node
            current_node, user_answer = messageHandler(
                current_node=current_node,
                user_answer=user_answer,
                chat=chat,
                contact=contact,
                business=business,
                whatsapp_account=whatsapp_account,
                resend_current_node=True
            )
            
            return None, user_answer
    except Exception as e:
        logsCollection.insert_one({
            "user" : "",
            "date" : datetime.datetime.now(),
            "description" : f"Error while executing the messageHandler function: {e} \n {current_node} \n {user_answer} \n {resend_current_node}",
            "ip" : ""
        })

def handlePostback():
    pass

def callSendAPI(next_node, business):
    url = f"{current_app.config['WHATSAPP_API_URL']}/{business.get('whatsapp_api_version')}/{current_app.config.get('WHATSAPP_PHONE_ID')}/messages"