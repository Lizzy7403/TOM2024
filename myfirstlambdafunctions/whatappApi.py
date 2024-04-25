import base64
import datetime
from io import BytesIO
import json

import requests
from flask import url_for, current_app
from flask_pymongo import ObjectId
from PIL import Image

from . import mongo
from .collections import conversationsCollection, messagesCollection, chatsCollection

##################### POST Messages : send message #####################
def sendMessage(payload, business, chat, whatsapp_account):
    url = f"{current_app.config['WHATSAPP_API_URL']}/{business.get('whatsapp_api_version')}/{whatsapp_account.get('whatsapp_number_id')}/messages"

    headers = {
        "Authorization" : f"Bearer {business.get('whatsapp_api_token')}",
        'Content-Type': "application/json"
    }

    response        = requests.post(url, headers=headers, json=payload)
    response_status = response.status_code
    
    if response_status == 200:
        try:
            # Create new message
            new_message = {
                "message_id": response.json().get("messages")[0].get("id"),
                "chat" : chat.get("_id"),
                "whatsapp_account" : whatsapp_account.get("_id"),
                "business" : business.get("_id"),
                "payload": payload,
                "date": datetime.datetime.now(),
                "owner": True,
                "status": "",
                "status_history": [],
                "operatorName": "Bot",
                "failedDetail": "",
                "wa_id" : response.json().get("contacts")[0].get("wa_id"),
                "contacts": response.json().get("contacts")[0],
                "contact" : chat.get("contact"),
                "eventType": "message"
            }

            message = messagesCollection.insert_one(new_message)
            message = messagesCollection.find_one({"_id" : message.inserted_id})

            chat["last_message"] = message.get("_id")

            # Save changes to the database
            chatsCollection.replace_one({'_id' : chat.get('_id')}, chat)

            return response.json(), 200
        except:
            return None, 500
    else:
        return response.json(), response_status

###################### Template messages #####################
#https://developers.facebook.com/docs/whatsapp/business-management-api/message-templates#create-message-templates

def getTemplateMessages(business, whatsapp_account):
    url = f"{current_app.config['WHATSAPP_API_URL']}/{business.get('whatsapp_api_version')}/{whatsapp_account.get('whatsapp_account_id')}/message_templates?access_token={business.get('whatsapp_api_token')}"

    response = requests.get(url)
    
    return response

def createTemplateMessage(payload, business, whatsapp_account): 
    url = f"{current_app.config['WHATSAPP_API_URL']}/{business.get('whatsapp_api_version')}/{whatsapp_account.get('whatsapp_account_id')}/message_templates?name={payload.get('name')}&language={payload.get('language')}&category={payload.get('category')}&components={payload.get('components')}&access_token={business.get('whatsapp_api_token')}"

    response = requests.post(url)
    
    return response

def deleteTemplateMessage(template_name, business, whatsapp_account): 
    url = f"{current_app.config['WHATSAPP_API_URL']}/{business.get('whatsapp_api_version')}/{whatsapp_account.get('whatsapp_account_id')}/message_templates?name={template_name}&access_token={business.get('whatsapp_api_token')}"

    response = requests.delete(url)
    
    return response


# TODO create function to send Message Templates
def sendMessageTemplate():
    pass

##################### CONVERSATIONS #####################
def check_conversation_status(phone_number):
    conversation = conversationsCollection.find_one({
        'phone_number' : phone_number,
        'is_active' : True
    })

    if conversation:
        # Check if 24 hours have passed
        pass

    return conversation

##################### Get configs : webhook #####################
def get_webhook(app, business):
    # Get business's API Key
    api_key = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/configs/webhook"

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.get(url, headers=headers)
    response_status = response.status_code

    if response_status == 200:
        try:
            webhook = response.json().get("url")
        except:
            webhook = None
        return webhook
    else:
        return None

##################### Post configs : webhook #####################
def post_webhook(app, business):
    # Get business's API Key
    api_key = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/configs/webhook"

    payload = {
        "url": url_for('whatsapp.notifications', business_id=str(business.get("_id")), _external=True) if (current_app.config["ENV"] == 'production' or current_app.config["ENV"] == 'testing') else f"https://127.0.0.1:5000/v1/notifications/{str(business.get('_id'))}"
    }

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.post(url, json=payload, headers=headers)
    response_status = response.status_code

    if response_status == 200:
        try:
            webhook = response.json().get("url")
        except:
            webhook = None
        return webhook
    else:
        return None


##################### Get profile : about #####################
def get_profile_about(app, business):
    # Get business's API Key
    api_key = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/settings/profile/about"

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.get(url, headers=headers)
    response_status = response.status_code

    if response_status == 200:
        try:
            profile_about = response.json().get("settings")
        except:
            profile_about = None

        return profile_about

    else:
        return None

##################### Post profile : about #####################
def post_profile_about(app, business, payload):
    # Get business's API Key
    api_key = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/settings/profile/about"

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.patch(url, json=payload, headers=headers)
    response_status = response.status_code

    if response_status == 200:
        try:
            profile_about = response.json().get("settings")
        except:
            profile_about = response.json()
        return profile_about
    else:
        return None

##################### Get profile : photo #####################
def get_profile_photo(app, business):
    # Get business's API Key
    api_key = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/settings/profile/photo"

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.get(url, headers=headers, stream=True)
    response_status = response.status_code

    if response_status == 200:
        try:
            image = Image.open(response.raw)
            data  = BytesIO()
            image.save(data, "JPEG")
            encoded_img_data = base64.b64encode(data.getvalue())
            profile_photo    = encoded_img_data.decode('utf-8')
        except:
            profile_photo = None
        return profile_photo
    else:
        return None

##################### Delete profile : photo #####################
def delete_profile_photo(app, business):
    # Delete business's API Key
    api_key = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/settings/profile/photo"

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.delete(url, headers=headers)
    response_status = response.status_code

    if response_status == 200:
        try:
            return 200
        except:
            return 500
    else:
        return response_status

##################### Post profile : photo #####################
def post_profile_photo(app, business, profile_photo):
    # Get business's API Key
    api_key = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/settings/profile/photo"

    data = profile_photo

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "image/jpg",
    }

    response        = requests.post(url, data=data, headers=headers)
    response_status = response.status_code

    if response_status == 200:
        return 200
    else:
        return 500

##################### Get business : profile #####################
def get_business_profile(app, business):
    # Get business's API Key
    api_key = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/settings/business/profile"

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.get(url, headers=headers)
    response_status = response.status_code

    if response_status == 200:
        try:
            business_profile = response.json().get("settings")
        except:
            business_profile = None
        return business_profile

    else:
        return None

##################### Post business : profile #####################
def post_business_profile(app, business, payload):
    # Get business's API Key
    api_key = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/settings/business/profile"

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.post(url, json=payload, headers=headers)
    response_status = response.status_code

    if response_status == 200:
        try:
            business_profile = response.json()
        except:
            business_profile = None
        return business_profile

    else:
        return None

##################### Get template list #####################
def get_template_list(app, business):
    # Get business's API Key
    api_key = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/configs/templates"

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.get(url, headers=headers)
    response_status = response.status_code
    response_data   = response.json()

    if response_status == 200:
        try:
            count     = response_data.get("count")
            templates = response_data.get("waba_templates")
        except:
            count     = None
            templates = None
        return count, templates
    else:
        return None

##################### Get message #####################
def get_message(app, business, message_id):
    # Get business's API Key
    api_key = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/messages/{message_id}"

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.post(url, headers=headers)
    response_status = response.status_code

    if response_status == 200:
        try:
            message = response.json()
        except:
            message = None
        return message
    else:
        return None

##################### Get contact #####################
def get_contact(app, business, contact):
    # Get business's API Key
    api_key = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/contacts"

    payload = {
        "blocking": "wait",
        "contacts": [f"+{contact}"],
        "force_check": True
    }

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.post(url, json=payload, headers=headers)
    response_status = response.status_code

    if response_status == 200:
        try:
            contact_status = response.json().get("contacts")[0].get("status")
            contact_wa_id  = response.json().get("contacts")[0].get("wa_id")
        except:
            contact_status = None
            contact_wa_id  = None
        return contact_status, contact_wa_id
    else:
        return None, None

##################### Send session message #####################
def send_session_message(app, business, message_to, message):
    # Get business's API Key and Namespace
    api_key   = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/messages"

    payload = {
        "recipient_type": "individual",
        "to": f"{message_to}",
        "type": "text",
        "text": {
            "body": f"{message}"
        }
    }

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.post(url, json=payload, headers=headers)
    response_status = response.status_code
    return response.json()
    # if response_status == 200:
    #     try:
    #         contact = response.json()
    #     except:
    #         contact = None
    #     return contact
    # else:
    #     return None

##################### Send template message #####################
def send_template_message(app, business, template_name, message_to, header_parameters, body_parameters):
    # Get business's API Key and Namespace
    api_key   = business.get("whatsapp_api_key")
    namespace = business.get("business_whatsapp_namespace")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/messages"

    payload = {
        "to": f"{message_to}",
        "type": "template",
        "template": {
            "namespace": f"{namespace}",
            "language": {
                "policy": "deterministic",
                "code": "es"
            },
            "name": f"{template_name}",
            "components": [
                {
                    "type": "header",
                    "parameters": header_parameters
                },
                {
                    "type": "body",
                    "parameters": body_parameters
                }
            ]

        }

    }

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.post(url, json=payload, headers=headers)
    response_status = response.status_code

    if response_status == 200:
        try:
            contact = response.json()
        except:
            contact = None
        return contact
    else:
        return None

##################### Send buttons message #####################
def send_buttons_message(app, business, message_to, header_text, body_text, footer_text, buttons):
    # Get business's API Key and Namespace
    api_key    = business.get("whatsapp_api_key")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/messages"

    payload = {
        "recipient_type": "individual",
        "to" : f"{message_to}",
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {
                "type": "text",
                "text": f"{header_text}"
            },
            "body": {
                "text": f"{body_text}"
            },
            "footer": {
                "text": f"{footer_text}"
                },
            "action": {
                "buttons": buttons
            }
        }
    }

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.post(url, json=payload, headers=headers)
    response_status = response.status_code

    if response_status == 200 or response_status==201:
        try:
            return response.json()
        except:
            return None
    else:
        return None

##################### Send one product message #####################
def send_one_product_message(app, business, message_to, body_text, footer_text, product_id):
    # Get business's API Key and Namespace
    api_key    = business.get("whatsapp_api_key")
    catalog_id = business.get("business_facebook_catalog_id")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/messages"

    payload = {
        "recipient_type": "individual",
        "to": f"{message_to}",
        "type": "interactive",
        "interactive": {
            "type": "product",
            "body": {
                "text": f"{body_text}"
            },
            "footer": {
                "text": f"{footer_text}"
            },
            "action": {
                "catalog_id": f"{catalog_id}",
                "product_retailer_id": f"{product_id}"
            }
        }
    }

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.post(url, json=payload, headers=headers)
    response_status = response.status_code

    if response_status == 200 or response_status==201:
        try:
            return response.json()
        except:
            return None
    else:
        return None

##################### Send multiple products message #####################
def send_multiple_products_message(app, business, message_to, header_text, body_text, section_title, products):
    # Get business's API Key and Namespace
    api_key    = business.get("whatsapp_api_key")
    catalog_id = business.get("business_facebook_catalog_id")

    url = f"{app.config['WHATSAPP_API_URL']}/v1/messages"

    payload = {
        "recipient_type": "individual",
        "to": f"{message_to}",
        "type": "interactive",
        "interactive": {
            "type": "product_list",
            "header": {
                "type": "text",
                "text": f"{header_text}"
            },
            "body": {
                "text": f"{body_text}"
            },
            "action": {
                "catalog_id": f"{catalog_id}",
                "sections": [
                    {
                        "title": f"{section_title}",
                        "product_items": products
                    }
                ]
            }
        }
    }

    headers = {
        'D360-Api-Key': f"{api_key}",
        'Content-Type': "application/json",
    }

    response        = requests.post(url, json=payload, headers=headers)
    response_status = response.status_code

    if response_status == 200 or response_status==201:
        try:
            return response.json()
        except:
            return None
    else:
        return None
