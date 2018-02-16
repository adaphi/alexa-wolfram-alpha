"""alexa-wolfram-alpha.py
This sample demonstrates a simple skill built with the Amazon Alexa Skills Kit.
The Intent Schema, Custom Slots, and Sample Utterances for this skill, as well
as testing instructions are located at http://amzn.to/1LzFrj6

For additional samples, visit the Alexa Skills Kit Getting Started guide at
http://amzn.to/1LGWsLG
"""

import os
import logging
import xml.etree.ElementTree as etree
try:
    from urllib.request import urlopen
    from urllib.parse import urlencode
except ImportError:
    # Python2
    from urllib2 import urlopen
    from urllib import urlencode

__version__ = 'v0.1.2'

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    logger.debug("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID
    to prevent someone else from configuring a skill that sends requests to
    this function.
    """
    if (event['session']['application']['applicationId'] !=
            os.environ["SKILL_ID"]):
        raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])


def on_session_started(session_started_request, session):
    """ Called when the session starts """

    logger.debug("on_session_started requestId=" +
          session_started_request['requestId'] +
          ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    logger.debug("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    logger.debug("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "wa_query":
        return ask_wolfram_alpha(intent, session)
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.
    Is not called when the skill returns should_end_session=true
    """
    logger.debug("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here

# --------------- Functions that control the skill's behavior -----------------


def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Ask a question to Wolfram Alpha."
    # If the user either does not reply to the welcome message or says
    # something that is not understood, they will be prompted again with this
    # text.
    reprompt_text = ("I didn't catch that. Ask a question for Wolfram Alpha.")
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def ask_wolfram_alpha(intent, session):
    session_attributes = {}
    should_end_session = False
    reprompt_text = "I didn't catch that. Care to try again?"
    speech_output = "Try asking me a question you'd ask Wolfram Alpha."

    api_root = "http://api.wolframalpha.com/v2/"

    appid = os.environ["WOLFRAM_ID"]

    query = intent['slots']['response'].get('value')

    # Alexa will always interpret "pi" as "pie"
    # Wolfram is likely to want the opposite, so let's fix that
    query = query.replace("pie", "pi")

    if query:

        logger.info("ask_wolfram_alpha query: " + query)

        payload = {
            'input': query,
            'appid': appid,
            'async': 'true',
            'reinterpret': 'true'
        }

        resp = urlopen(api_root + "query?" + urlencode(payload))
        raw = resp.read()
        logger.debug(raw)
        tree = etree.fromstring(raw)

        try:
            # Return first subpod's plaintext
            answer = next(pod for pod in tree if pod.attrib.get('title') in ["Result", "Decimal approximation", "Limit"])

            if answer.attrib.get('title') == "Result":
                result = answer.find("subpod").find("plaintext").text

            elif answer.attrib.get('title') == "Decimal approximation":
                _s = answer.find("subpod").find("plaintext").text.replace('...', '')
                if 'i' not in _s:
                    _n = round(float(_s), 4)
                else:
                    _n_1, _, _n_2 = _s.split()[:3]
                    _n = "{} + {} i".format(round(float(_n_1), 2), round(float(_n_2), 2))
                result = "Approximately {}".format(_n)

            elif answer.attrib.get('title') == "Limit":
                _s = answer.find("subpod").find("plaintext").text
                result = _s[_s.index('=')+2:]

            should_end_session = True
        except StopIteration:
            result = "No results for {}".format(query)

        logger.info("ask_wolfram_alpha result: " + result)

        speech_output = result

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

# --------------- Helpers that build all of the responses ---------------------


def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': 'SessionSpeechlet - ' + title,
            'content': 'SessionSpeechlet - ' + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }
