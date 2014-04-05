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
from django_facebook.decorators import facebook_required_lazy
from django_facebook.utils import next_redirect, get_registration_backend, \
	to_bool, error_next_redirect, get_instance_for
from open_facebook import exceptions as open_facebook_exceptions
from open_facebook.utils import send_warning
from django.http import HttpResponse
import logging
from open_facebook.api import OpenFacebook
from django_facebook.api import get_persistent_graph, require_persistent_graph
import json
from search.models import *
from urlparse import parse_qs, urlparse

logger = logging.getLogger(__name__)


@csrf_exempt
@facebook_required_lazy
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

@facebook_required_lazy
def home(request):
	require_persistent_graph(request)
	context = RequestContext(request)
	print 'example yo'
	graph = request.facebook
	

	# token = request.facebook.user.oauth_token.token #user token
	# token_app=facepy.utils.get_application_access_token('APP_ID','APP_SECRET_ID') 
	


	return render_to_response('home.html', context)
  
	
@facebook_required_lazy
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

@facebook_required_lazy
def getGraphPost (request, postID):
	require_persistent_graph(request)
	context = RequestContext(request)
	graph = request.facebook
	postDict = graph.get(postID)
	return HttpResponse(json.dumps(postDict, ensure_ascii=False), mimetype="application/json")

@facebook_required_lazy
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
			response = _query(query, request.facebook)
		else:
			response = {'error' : "Enter a search term", "count":0}

	else:
		response = {'error' : "Invalid Request, please refresh the page.", "count":0}
	return HttpResponse(json.dumps(response, ensure_ascii=False), mimetype="application/json")


def _query(query, graph):	

	feed_dict = graph.get('me/feed', limit=25)
	print len(feed_dict['data'])
	idList = []
	for datum in feed_dict['data']:
		if datum['type'] in ['link', 'photo', 'video']:
			if 'story' in datum and 'went to an event' in datum['story']:
				continue
			idList.append(datum['id'])
		elif 'message' in datum or ('status_type' in datum and datum['status_type'] == "wall_post"):
			idList.append(datum['id'])
			
	response = {}
	response ['data'] = idList
	response['count'] = len(idList)
	return response

def buildIndex(graph, user):

	feedDict = graph.get('me/feed', limit=200)
	newLastPostTime = feedDict['data'][0]['created_time']
	invertedIndexObject = InvertedIndex.objects.get(userID = user.id)
	lastPostTime = invertedIndexObject.lastPostTime
	if lastPostTime == "":
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
		print 'reindex code is not there yet'
		while indexFeedTill(feedDict, user, lastPostTime) == False:
			feedDict = graph.get('me/feed', limit=200, until = int(queries['until'][0]))
	
	invertedIndexObject = InvertedIndex.objects.get(userID = user.id)
	invertedIndexObject.lastPostTime = newLastPostTime
	invertedIndexObject.save()

def indexFeed(feedDict, user):
	
	invertedIndexObject = InvertedIndex.objects.get(userID = user.id)
	invertedIndex = invertedIndexObject.invertedIndex
	count = 0
	for datum in feedDict['data']:
		index = {}
		if datum['type'] in ['photo', 'link', 'video']:
			if 'message' in datum:
				addToIndex(invertedIndex, datum['message'], datum['id'])
				count = count + 1
			elif 'description' in datum and datum['type'] != 'link':
				addToIndex(invertedIndex, datum['description'], datum['id'])
				count = count + 1
		elif datum['type'] == 'status':
			if 'message' in datum:
				addToIndex(invertedIndex, datum['message'], datum['id'])
				count = count + 1
			elif 'story' in datum and 'status_type' in datum and datum['status_type'] == 'wall_post':
				storySplit = datum['story'].split('"')
				if len(storySplit) == 1:
					continue
				addToIndex(invertedIndex, "".join(storySplit[1:len(storySplit)-1]), datum['id'])
				count = count + 1
	
	invertedIndexObject.numberOfPosts = invertedIndexObject.numberOfPosts + count
	invertedIndexObject.save()
	print 'indexed some posts'

def indexFeedTill (feedDict, user, time):
	if feedDict['data'][len(feedDict['data']) - 1]['created_time'] > time:
		indexFeed (feedDict, user)
		print 'added all posts'
		return False 
	else:
		prunedDict = {'data' : []}
		for datum in feedDict['data']:
			if datum['created_time'] > time:
				prunedDict['data'].append(datum)
			else:
				break
		indexFeed (prunedDict, user)
		print 'added some posts'
		return True

def addToIndex(index, postText, postID):
	words = preprocess(postText).split(' ')
	for i in range(0, len(words)):
		word = words[i]
		if word in index:
			if(postID in index[word]):
				index[word][postID].append(i)
			else:
				index[word][postID] = [i]
		else:
			index[word] = {postID : [i]}

def preprocess (postText):
	return postText

def saveUserPosts (graph, user):
	feedDict = graph.get('me/feed', limit=200)
	for datum in feedDict['data']:
		if datum['type'] in ['photo', 'link', 'video']:
			if 'message' in datum:
				addPostForUser(datum['message'], user.id, datum['id'])
			elif 'description' in datum and datum['type'] != 'link':
				addPostForUser(datum['description'], user.id, datum['id'])
		elif datum['type'] == 'status':
			if 'message' in datum:
				addPostForUser(datum['message'], user.id, datum['id'])
			elif 'story' in datum and 'status_type' in datum and datum['status_type'] == 'wall_post':
				storySplit = datum['story'].split('"')
				if len(storySplit) == 1:
					continue
				addPostForUser("".join(storySplit[1:len(storySplit)-1]), user.id, datum['id'])

def addPostForUser (postText, userID, postID):
	posts = Post.objects.filter(postID = postID).filter(userID = userID)
	if len(posts) > 0:
		return
	post = Post(userID = userID, text = postText, postID = postID)
	post.save()

def getInvertedIndex (request, userID):
	invertedIndex = InvertedIndex.objects.get(userID = userID)
	return HttpResponse(json.dumps(invertedIndex.invertedIndex, ensure_ascii=False), mimetype="application/json")	






