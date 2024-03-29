from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_facebook import exceptions as facebook_exceptions, \
	settings as facebook_settings
from django_facebook.connect import CONNECT_ACTIONS, connect_user
from django_facebook.decorators import facebook_required_lazy, facebook_required
from django_facebook.utils import next_redirect, get_registration_backend, \
	to_bool, error_next_redirect, get_instance_for
from open_facebook import exceptions as open_facebook_exceptions
from open_facebook.utils import send_warning
from django.http import HttpResponse, HttpResponseRedirect
import logging
from open_facebook.api import OpenFacebook
from django_facebook.api import get_persistent_graph, require_persistent_graph
import json
from search.models import *
from urlparse import parse_qs, urlparse
from django.contrib.auth import logout as django_logout
from collections import defaultdict
import math
import nltk
import string, re
from nltk.stem.wordnet import WordNetLemmatizer
nltk.data.path.append('./nltk_data/')

logger = logging.getLogger(__name__)


'''
--------------------------------------------------------------
Facebook methods
--------------------------------------------------------------
'''

@csrf_exempt
@facebook_required(scope=['read_stream', 'email', 'user_about_me', 'user_birthday', 'user_website'])
def connect(request, graph):
	'''
	Exception and validation functionality around the _connect view
	Separated this out from _connect to preserve readability
	Don't bother reading this code, skip to _connect for the bit you're interested in :)
	'''
	backend = get_registration_backend()
	context = RequestContext(request)

	# validation to ensure the context processor is enabled
	if not context.get('FACEBOOK_APP_ID'):
		message = 'Please specify a Facebook app id and ensure the context processor is enabled'
		raise ValueError(message)

	try:
		response = _connect(request, graph)
	except open_facebook_exceptions.FacebookUnreachable, e:
		# often triggered when Facebook is slow
		warning_format = u'%s, often caused by Facebook slowdown, error %s'
		warn_message = warning_format % (type(e), e.message)
		send_warning(warn_message, e=e)
		additional_params = dict(fb_error_or_cancel=1)
		response = backend.post_error(request, additional_params)

	return response


def _connect(request, graph):
	'''
	Handles the view logic around connect user
	- (if authenticated) connect the user
	- login
	- register

	We are already covered by the facebook_required_lazy decorator
	So we know we either have a graph and permissions, or the user denied
	the oAuth dialog
	'''
	backend = get_registration_backend()
	context = RequestContext(request)
	connect_facebook = to_bool(request.REQUEST.get('connect_facebook'))

	logger.info('trying to connect using Facebook')
	if graph:
		logger.info('found a graph object')
		converter = get_instance_for('user_conversion', graph)
		authenticated = converter.is_authenticated()
		# Defensive programming :)
		if not authenticated:
			raise ValueError('didnt expect this flow')

		logger.info('Facebook is authenticated')
		facebook_data = converter.facebook_profile_data()
		# either, login register or connect the user
		try:
			action, user = connect_user(
				request, connect_facebook=connect_facebook)
			logger.info('Django facebook performed action: %s', action)
		except facebook_exceptions.IncompleteProfileError, e:
			# show them a registration form to add additional data
			warning_format = u'Incomplete profile data encountered with error %s'
			warn_message = warning_format % unicode(e)
			send_warning(warn_message, e=e,
						 facebook_data=facebook_data)

			context['facebook_mode'] = True
			context['form'] = e.form
			return render_to_response(
				backend.get_registration_template(),
				context_instance=context,
			)
		except facebook_exceptions.AlreadyConnectedError, e:
			user_ids = [u.get_user_id() for u in e.users]
			ids_string = ','.join(map(str, user_ids))
			additional_params = dict(already_connected=ids_string)
			return backend.post_error(request, additional_params)

		response = backend.post_connect(request, user, action)

		if action is CONNECT_ACTIONS.LOGIN:
			pass
		elif action is CONNECT_ACTIONS.CONNECT:
			# connect means an existing account was attached to facebook
			messages.info(request, _("You have connected your account "
									 "to %s's facebook profile") % facebook_data['name'])
		elif action is CONNECT_ACTIONS.REGISTER:
			invertedIndex = InvertedIndex(userID = user.id, invertedIndex = {}, lastPostTime = "", numberOfPosts = 0)
			invertedIndex.save()
			# hook for tying in specific post registration functionality
			response.set_cookie('fresh_registration', user.id)
	else:
		# the user denied the request
		additional_params = dict(fb_error_or_cancel='1')
		response = backend.post_error(request, additional_params)

	return response


def disconnect(request):
	'''
	Removes Facebook from the users profile
	And redirects to the specified next page
	'''
	if request.method == 'POST':
		messages.info(
			request, _("You have disconnected your Facebook profile."))
		profile = request.user.get_profile()
		profile.disconnect_facebook()
		profile.save()
	response = next_redirect(request)
	return response

'''
Indexing method that is automatically called the first time a user logs in
'''
def index (request):
	if request.user.is_authenticated():
		return home(request)
	else:
		return login(request)

def login (request):
	context = RequestContext(request)
	return render_to_response('login.html', context)

def logout(request):
	django_logout(request)
	return HttpResponseRedirect("/")

@facebook_required(scope=['read_stream', 'email', 'user_about_me'])
def home(request):
	require_persistent_graph(request)
	context = RequestContext(request)
	print 'homepage yo'
	graph = request.facebook
	
	return render_to_response('home.html', context)
  
	
@facebook_required(scope=['read_stream', 'email', 'user_about_me'])
def reindex(request):

	require_persistent_graph(request)
	context = RequestContext(request)
	print 'reindexing yo'
	graph = request.facebook
	user = request.user
	buildIndex(graph, user)
	# saveUserPosts(graph, user)
	return HttpResponse("Done yo!")

@facebook_required_lazy
def getProfilePicture(request):
	require_persistent_graph(request)
	context = RequestContext(request)
	print 'getting profile picture yo'
	graph = request.facebook
	url = graph.get('me/picture', redirect = 0, height = 50, width = 50, type = 'normal')
	# print url
	return HttpResponse(json.dumps(url, ensure_ascii=False), mimetype="application/json")

@facebook_required(scope=['read_stream', 'email', 'user_about_me'])
def getGraphPost (request, postID):
	require_persistent_graph(request)
	context = RequestContext(request)
	graph = request.facebook
	postDict = graph.get(postID)
	return HttpResponse(json.dumps(postDict, ensure_ascii=False), mimetype="application/json")

'''
The first query method called when querying occurs. It checks whether there exists a valid search term,
whether the user is logged in etc, before calling _query that really starts the querying.
'''
def query(request):

	require_persistent_graph(request)
	context = RequestContext(request)
	print 'querying yo'
	
	# print response
	response = {}
	if request.POST:
		formDict = request.POST
		if formDict['query']:
			query = formDict['query']
			print 'getting more'
			response = _query(query, request.user)
		else:
			response = {'error' : "Enter a search term", "count":0}

	else:
		response = {'error' : "Invalid Request, please refresh the page.", "count":0}
	return HttpResponse(json.dumps(response, ensure_ascii=False), mimetype="application/json")

'''
_query method:
1. Preprocesses the query term.
2. Retrieves possibly relevant posts (any posts that contain any word from the query phrase).
3. calls further query methods.
'''
def _query(query, user):	
	invertedIndexObject = InvertedIndex.objects.get (userID = user.id)
	invertedIndex = invertedIndexObject.invertedIndex
	
	posts = []
	terms = preprocess(query)
	toRemove = []
	for term in terms:
		if term in invertedIndex:
			posts.extend(invertedIndex[term].keys())
		else:
			toRemove.append (term)

	for term in toRemove:
		terms.remove(term)

	posts = list(set(posts))
	posts = querySearch(terms, invertedIndex, posts)

	posts = postProcessSearchResults(terms, posts, invertedIndex)

	response = {}
	response ['data'] = posts
	response['count'] = len(posts)
	return response


'''
returns the words in a post
'''
def getPostWordsForPostID(postID, invertedIndex):
	postWords = {}
	for word in invertedIndex:
		if postID in invertedIndex[word]:
			positions = invertedIndex[word][postID]
			for position in positions:
				postWords[position] = word
	
	orderedWords = []
	for position in sorted(postWords.keys()):
		orderedWords.append(postWords[position])
	
	# print orderedWords
	return orderedWords

'''
Builds the index for a user.
Retrieves 200 posts at a time and builds the index till it has at least 1000 posts.
This is limited due to facebook API restrictions of 600 calls per 600s for a user/app pair.
'''
def buildIndex(graph, user):

	feedDict = graph.get('me/feed', limit=200)
	newLastPostTime = feedDict['data'][0]['created_time']
	invertedIndexObject = InvertedIndex.objects.get(userID = user.id)
	lastPostTime = invertedIndexObject.lastPostTime
	invertedIndexObject.lastPostTime = newLastPostTime
	invertedIndexObject.save()
	if lastPostTime == "" or invertedIndexObject.numberOfPosts < 400:
		while len(feedDict['data']) > 0 and invertedIndexObject.numberOfPosts < 1000:
			# index them
			print 'indexing some posts'
			indexFeed (feedDict, user)
			# get next 200 posts
			url = feedDict["paging"]["next"]
			queries = parse_qs(urlparse(url).query, keep_blank_values=True)
			if 'until' not in queries:
				break
			feedDict = graph.get('me/feed', limit=200, until = int(queries['until'][0]))
			invertedIndexObject = InvertedIndex.objects.get(userID = user.id)
	else:
		while indexFeedTill(feedDict, user, lastPostTime) == False:
			feedDict = graph.get('me/feed', limit=200, until = int(queries['until'][0]))
	
	# invertedIndexObject = InvertedIndex.objects.get(userID = user.id)
	

'''
adds all the posts in feedDict to the index.
'''
def indexFeed(feedDict, user):
	
	invertedIndexObject = InvertedIndex.objects.get(userID = user.id)
	invertedIndex = invertedIndexObject.invertedIndex
	count = 0
	for datum in feedDict['data']:
		index = {}
		if datum['type'] in ['photo', 'link', 'video']:
			if 'message' in datum:
				if addToIndex(invertedIndex, datum['message'], datum['id']) == True:
					count = count + 1
			elif 'description' in datum and datum['type'] != 'link':
				if addToIndex(invertedIndex, datum['description'], datum['id']) == True:
					count = count + 1
		elif datum['type'] == 'status':
			if 'message' in datum:
				if addToIndex(invertedIndex, datum['message'], datum['id']) == True:
					count = count + 1
			elif 'story' in datum and 'status_type' in datum and datum['status_type'] == 'wall_post':
				storySplit = datum['story'].split('"')
				if len(storySplit) == 1:
					continue
				if addToIndex(invertedIndex, "".join(storySplit[1:len(storySplit)-1]), datum['id']) == True:
					count = count + 1
	print str(count) + ' posts added'
	invertedIndexObject.numberOfPosts = invertedIndexObject.numberOfPosts + count
	invertedIndexObject.save()

'''
adds all the posts in feedDict to the index till a specified time.
'''
def indexFeedTill (feedDict, user, time):
	if feedDict['data'][len(feedDict['data']) - 1]['created_time'] > time:
		indexFeed (feedDict, user)
		
		return False 
	else:
		prunedDict = {'data' : []}
		for datum in feedDict['data']:
			if datum['created_time'] > time:
				prunedDict['data'].append(datum)
			else:
				break
		indexFeed (prunedDict, user)
		
		return True

'''
adds a specific post to the index.
'''
def addToIndex(index, postText, postID):
	words = preprocess(postText)
	for i in range(0, len(words)):
		word = words[i]
		if word in index:
			if postID in index[word] and i in index[word][postID]:
				return False
			elif postID in index[word]:
				index[word][postID].append(i)
			else:
				index[word][postID] = [i]
		else:
			index[word] = {postID : [i]}
	return True
'''
Preprocessing using the WordNetLemmatizer, imported from nltk.
'''
def preprocess(text):
	lemmatizer = WordNetLemmatizer()
	words = []

	# Removing Punctuation and Special Characters
	exclude = set(string.punctuation)
	text = ''.join(char for char in text if char not in exclude)
	# text.translate(string.maketrans("\n\t\r", "   "))
	re.sub('\n\t\n', ' ', text)
	# Case Folding
	text = text.lower()
   
	# Stemming and Removal of Stopwords
	terms = text.split()
	for term in terms:
		lemmatizedTerm = lemmatizer.lemmatize(term.lower())
		words.append(lemmatizedTerm.lower())

	return words

def getInvertedIndex (request, userID):
	invertedIndex = InvertedIndex.objects.get(userID = userID)
	return HttpResponse(json.dumps(invertedIndex.invertedIndex, ensure_ascii=False), mimetype="application/json")	



"""
------------------------------------------------------
Querying methods
------------------------------------------------------
"""
def querySearch(query, index, documents):
	print 'starting search'
	queryDictionary = set(query)
	# print len(queryDictionary)
	document_frequency = defaultdict(int)
	length = defaultdict(float)
	characters = " .,!#$%^&*();:\n\t\\\"?!{}[]<>"
	initialize_document_frequencies(queryDictionary, index, document_frequency)
	# print 'got df'
	initialize_lengths(queryDictionary, length, index, documents, document_frequency)
	documents = search(queryDictionary, documents, document_frequency, index, length)
	print 'search complete'
	
	return documents

def initialize_document_frequencies(queryDictionary, index, document_frequency):
	for term in queryDictionary:
		document_frequency[term] = len(index[term].keys())

def initialize_lengths(queryDictionary, length, index, documents, document_frequency):
	# print 'get lengths'
	for id in documents:
		# print id
		l = 0
		for term in queryDictionary:
			l += imp(term,id, index, queryDictionary, document_frequency)**2
		length[id] = math.sqrt(l)


'''
Calculates the importance of a term, with respect to a document (post).
imp = tf(term,doc)*idf(term)
'''
def imp(term,id, index, queryDictionary, document_frequency):
	if id in index[term].keys():
		return len(index[term][id])*inverse_document_frequency(term, queryDictionary, document_frequency)
	else:
		return 0.0

def inverse_document_frequency(term, queryDictionary, document_frequency):
	if term in queryDictionary and document_frequency[term] != 0:
		return math.log(1000/document_frequency[term],2)
	else:
		return 0.0

def search(queryDictionary, documents, document_frequency, index, length):
	# sorts all relevant documents in order of similarity, or relevance
	scores = sorted([(id,similarity(queryDictionary,id, document_frequency, index, length))
					 for id in documents],
					key=lambda x: x[1],
					reverse=True)
	sortedPosts = []
	for score in scores:
		if score[1] > 6:
			sortedPosts.append(score[0])
	# print len(sortedPosts)
	return sortedPosts

def intersection(sets):
	return reduce(set.intersection, [s for s in sets])

'''
calculates the similarity of a doc with respect to the query term.
similarity = sum(idf(term)*imp(term, doc)) for every term in the query.
'''
def similarity(queryDictionary,id, document_frequency, index, length):
	similarity = 0.0
	for term in queryDictionary:
		similarity += inverse_document_frequency(term, queryDictionary, document_frequency)*imp(term,id, index, queryDictionary, document_frequency)
	
	if length[id] != 0:
		similarity = similarity / length[id]

	return similarity


'''
Phrase Search method
'''
def postProcessSearchResults (query, posts, index):
	phraseMatches = []
	nonMatches = []
	queryAsString = " ".join(query)
	for post in posts:
		postText = getPostWordsForPostID(post, index)
		postTextAsString = " ".join(postText)
		if queryAsString in postTextAsString:
			phraseMatches.append (post)
		else:
			nonMatches.append (post)
	results = []
	results.extend (phraseMatches)
	results.extend (nonMatches)
	return results