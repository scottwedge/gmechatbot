#~~~~~~~~~~~~~~~ Package imports.
import os
import sys
import json
from flask import Flask, request
import requests
from random import randint
import linecache
import datetime
import wget
import time
import spacy
from spacy.matcher import Matcher
import en_core_web_sm

app = Flask(__name__)
nlp = en_core_web_sm.load()
matcher = Matcher(nlp.vocab)


#----------------------------The Talker----------------------------#

#~~~~~~~~~~~~~~~ Endpoint for GroupMe messages.
@app.route('/', methods=['POST'])
def webhook():
	data = request.get_json()
	if data['sender_type'] == 'user': #did the user send the message?
		log('The Talker Log: Received Message: "{}" from "{}".'.format(data['text'], data['name']))
		scan_message(data['text'])
	return "ok", 200

#~~~~~~~~~~~~~~~ Methods.
def read_quote(): #Reading a quote.
	x = randint(1, 81)
	quote = linecache.getline('quotes.txt', x) #reading a random line in the file
	log('The Talker Log: Quote has been read.')
	post_message('The Talker', quote, '')

def read_joke(): #Telling a joke.
	x = randint(1, 61)
	joke = linecache.getline('jokes.txt', x) #reading a random line in the file
	log('The Talker Log: Joke has been read.')
	post_message('The Talker', joke, '')

def scan_message(msg): #Using NLP to process the user's message.
	doc = nlp(msg)
	is_punct_msgsent = False 

	for token in doc: #iterate over each token (a word or punctuation)
		if token.is_punct:  
			if is_punct_msgsent == False: 
				post_message('The Talker', 'Thank you for using punctuation!', '')
				log('The Talker Log: Punctuation was detected in the message.')
				is_punct_msgsent == True
		#Keywords.
		if token.text.lower()[0:4] == 'joke':
			read_joke()
		if token.text.lower()[0:5] == 'quote':
			read_quote()
		if token.text.lower()[0:4] == 'news':
			read_news(doc[token.i - 1].text.lower())


#----------------------------The Digital Journalist----------------------------#

#~~~~~~~~~~~~~~~ Endpoints for cron-scheduled pings. 
@app.route('/weather', endpoint = 'weather', methods=['POST'])
def webhook():
	read_weather()
	return "ok", 200
@app.route('/news', endpoint = 'news', methods=['POST'])
def webhook():
	read_news('')
	return "ok", 200
@app.route('/history', endpoint = 'history', methods=['POST'])
def webhook():
	read_history()
	return "ok", 200
@app.route('/votd', endpoint = 'votd', methods=['POST'])
def webhook():
	read_votd()
	return "ok", 200

#~~~~~~~~~~~~~~~ Methods.
def read_weather(): #Explaining the weather forecast.
	data = requests.get( #get the weather at Oakdale, Minnesota, in Imperial units
		url = 'https://api.weatherbit.io/v2.0/forecast/daily?city=Oakdale,MN&units=I&days=1&key={}'.format(os.getenv('WEATHERBIT_API_KEY'))
	)
	log('The Digital Journalist Log: Received Weather. {}'.format(data))
	post_message('The Digital Journalist', "Today's high temp is {}°F, the low temp {}°F, and there is {}% predicted chance of precipitation. Clouds will cover the sky around {}% of sky today.".format(data.json()['data'][0]['high_temp'], data.json()['data'][0]['low_temp'], data.json()['data'][0]['pop'], data.json()['data'][0]['clouds']),'')	

def read_news(query): #Detailing top headlines.
	if query != '':
		log('The Digital Journalist Log: Asking for news about "{}."'.format(query))
		url_query = 'q=' + query + '&' #add the url format to custom news request

	data = requests.get(#get the top thirty US headlines, with an optional custom query
		url = 'https://newsapi.org/v2/top-headlines?country=us&{}pageSize=30&apiKey={}'.format(url_query, os.getenv('NEWS_API_KEY'))
	)
	log("The Digital Journalist Log: Received The News. {}".format(data))
	
	limit = data.json()['totalResults']
	story1 = randint(0, limit)
	story2 = randint(0, limit)
	story3 = randint(0, limit)

	#Check once to try to fix a duplicate event in the list.
	if(story2 == story1): 
		story2 = randint(0, limit)
	if(story3 == story1 or story3 == story2):
		story3 = randint(0, limit)

	story1_description = data.json()['articles'][story1]['description']
	story2_description = data.json()['articles'][story2]['description']
	story3_description = data.json()['articles'][story3]['description']
	story1_url = data.json()['articles'][story1]['url']
	story2_url = data.json()['articles'][story2]['url']
	story3_url = data.json()['articles'][story3]['url']

	post_message('The Digital Journalist', "Today's Top News: \n\n{}\n{}, \n\n{}\n{}, \n\n{}\n{}".format(story1_description, story1_url, story2_description, dstory2_url, story3_description, story3_url),'')

def read_history(): #Recalling the events of the past.
	data = requests.get(
		url = 'http://history.muffinlabs.com/date'
		)
	log("The Digital Journalist Log: Received Today's History. {}".format(data))

	#Determine three random events to display.
	limit = len(data.json()['data']['Events']) 
	story1 = randint(0, limit + 1)
	story2 = randint(0, limit + 1)
	story3 = randint(0, limit + 1)

	#Check once to see if there is a duplicate event in the list.
	if(story2 == story1):	
		story2 = randint(0, limit + 1)
	if(story3 == story1 or story3 == story1):
		story3 = randint(0, limit + 1)

	#Scan the events twice to make sure the dates are in order.
	for i in range(2): 
		if(data.json()['data']['Events'][story1]['year'] > data.json()['data']['Events'][story2]['year']):
			x = story1
			story1 = story2
			story2 = x
		if(data.json()['data']['Events'][story2]['year'] > data.json()['data']['Events'][story3]['year']):
			x = story3
			story3 = story2
			story2 = x
	date = data.json()['date']
	post_message('The Digital Journalist', 'Today in History, {}: \n\n{}, {}\n\n{}, {}\n\n{}, {}'.format(date, data.json()['data']['Events'][story1]['year'], data.json()['data']['Events'][story1]['text'], data.json()['data']['Events'][story2]['year'], data.json()['data']['Events'][story2]['text'], data.json()['data']['Events'][story3]['year'], data.json()['data']['Events'][story3]['text']), '')

def read_votd(): #Downloading and uploading verse of tbe day picture.
	dayNumber = (datetime.date.today() - datetime.date(2020, 1, 1)).days
	data = requests.get( #Request verse and picture url from YouVersion. 
		url ='https://developers.youversionapi.com/1.0/verse_of_the_day/{}?version_id=1'.format(dayNumber), 
		headers = {
			'accept' : 'application/json',
			'x-youversion-developer-token' : '{}'.format(os.getenv('YOUVERSION_DEVELOPER_TOKEN')),
			'accept-language' : 'en'
		}
	)
	log('The Digital Journalist Log: Received VOTD. {}'.format(data))
	
	verse = data.json()['verse']['text'] + '\n- ' + data.json()['verse']['human_reference'] 
	data = wget.download(data.json()['image']['url'][56:]) #Download the picture from Youversion.
	log('The Digital Journalist Log: Image Download from YouVersion Complete.')
  

	data = requests.post( #Upload the picture to GroupMe's image service.
		url = 'https://image.groupme.com/pictures', 
		data = open('./1280x1280.jpg', 'rb').read(), 
		headers = {'Content-Type': 'image/jpeg','X-Access-Token':'{}'.format(os.getenv('GROUPME_DEVELOPER_TOKEN'))}
	)
	log('The Digital Journalist Log: Image Upload to GroupMe Complete. {}'.format(data))

	#Post the image to the chat.
	image_url = (data.json()['payload']['url'])
	post_message('The Digital Journalist', '', image_url)
	post_message('The Digital Journalist', verse, '')


#----------------------------General Methods
def post_message(bot_name, msg, image_url): #Sending a message to the group chat.
	if image_url == '': #Post message without photo.
		if bot_name == 'The Talker': #Post message from Talker.
			data = requests.post(
				url = 'https://api.groupme.com/v3/bots/post', 
				data = {
					'bot_id'  : os.getenv('TALKER_BOT_ID'),
					'text' : msg,
				}
			)
			log('The Talker Log: Message: "{}" was posted. {}'.format(msg, data))
		elif bot_name == 'The Digital Journalist': #Post message from The Digital Journalist.
			data = requests.post(
				url = 'https://api.groupme.com/v3/bots/post', 
				data = {
					'bot_id'  : os.getenv('JOURNALIST_BOT_ID'),
					'text' : msg,
				}
			)
			log('The Digital Journalist Log: Message: "{}" was posted. {}'.format(msg, data))
	else: #Post message with photo.
		if bot_name == 'The Talker': #Post message from The Talker.
			data = requests.post(
				url = 'https://api.groupme.com/v3/bots/post', 
				params = {
					'bot_id'  : os.getenv('Talker_BOT_ID'),
					'text' : msg,
					'attachments' : [
   						{
							'type' : 'image',
							'url'  : image_url
						}
					]
				},
				data = {
					'text' : 'Image',
					'picture_url' : image_url
				}
			)
			log('The Talker Log: Message: "{}" was posted along with the image at this link: {}. {}'.format(msg, image_url, data))
		elif bot_name == 'The Digital Journalist': #Post message from The Digital Journalist.
			data = requests.post(
				url = 'https://api.groupme.com/v3/bots/post', 
				params = {
					'bot_id'  : os.getenv('JOURNALIST_BOT_ID'),
					'text' : msg,
					'attachments' : [
   						{
							'type' : 'image',
							'url'  : image_url
						}
					]
				},
				data = {
					'text' : 'Image',
					'picture_url' : image_url
				}
			)
			log('The Digital Journalist Log: Message: "{}" was posted along with the image at this link: {}. {}'.format(msg, image_url, data))

def log(msg): #Printing log information.
	print(str(msg))
	sys.stdout.flush()
