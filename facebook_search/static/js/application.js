
var reindex = function () {
	var pleaseWaitDiv = $('#reindexingDialog');
	pleaseWaitDiv.modal('show');
	$.ajax({
		type: reindexButton.attr('method'),
		url: reindexButton.attr('action'),
		data: reindexButton.serialize(),
		success: function (data) {
			console.log(data);
			pleaseWaitDiv.modal('hide');
		},
		error: function(data) {
			console.log (data);
			pleaseWaitDiv.modal('hide');
		}
	});
	return false;
};

var reindexButton = $('#reindex-form');
reindexButton.submit(reindex);

var query = "";

$(document).ready(function(){	
	reindex();
	$.ajax({
		type: 'get',
		url: '/profile-picture/',
		success: function (data) {
			var profilePicture = $("#profile-picture");
			profilePicture.attr('src', data.data.url);
		},
		error: function(data) {
			console.log ("error");
			console.log (data);
		}
	});
	$.ajax({
		type: 'get',
		url: '/profile-picture/',
		success: function (data) {
			var profilePicture = $("#profile-picture");
			profilePicture.attr('src', data.data.url);
		},
		error: function(data) {
			console.log ("error");
			console.log (data);
		}
	});    
});
var queryForm = $('#query-form');
queryForm.submit(function () {
	var pleaseWaitDiv = $('#searchingDialog');
	query = $("#search-bar").val();
	pleaseWaitDiv.modal('show');
	$.ajax({
		type: queryForm.attr('method'),
		url: queryForm.attr('action'),
		data: queryForm.serialize(),
		success: function (data) {

			pleaseWaitDiv.modal('hide');
			processSearchResults(data);
			console.log (data);
		},
		error: function(data) {
			pleaseWaitDiv.modal('hide');
			console.log ("error");
			console.log (data);
		}
	});
	return false;
});



function postData(url, obj, callback)
{
	$.post(
			url, 
			{msg: JSON.stringify(obj)},
			function(data) {
				callback(data);
	});
}

function processSearchResults (results)
{
	// console.log(results);
	$("#results-container").remove();
	if (results.error) 
	{
		// console.log (generateWarningPanel(results.error));
		var html = '<div id = "results-container">';
		html += generateWarningPanel(results.error);
		html += '</div>';
		$(html).appendTo('#results-container-parent');
	}
	else if (results.count == 0) {
		var html = '<div id = "results-container">';
		html += generateWarningPanel("The search query was not found in your recent activity.");
		html += '</div>';
		$(html).appendTo('#results-container-parent');
	}
	else 
	{
		var html = '<div id = "results-container">';
		for (var i = 0; i < results.count; i++)
		{
			var postID = results.data[i];
			// console.log(postID);
			html += generatePostPanel(postID);
			$.ajax({
				type: 'get',
				url: '/graph-post/'+postID+'/',
				success: function (postData) {
					udpatePostPanel(postData);
					jQuery("abbr.timeago").timeago();
				},
				error: function(data) {
					console.log ("error retrieving object");
					console.log (postID);
				}
			});
			// udpatePostPanel(postID);

		}
		html += '</div>';
		$(html).appendTo('#results-container-parent');
	}
}
function udpatePostPanel (postData)
{
	// console.log(postData);
	var postDiv = $("#" + postData.id + 'parent');
	postDiv.empty();
	if (postData.type == "status")
	{
		var heading, body;
		if (postData.message)
		{

			if (postData.to && (postData.to.name||postData.to.data.length > 0))
			{
				
				heading = generatePanelHeading(postData.from.name+" posted on "+(postData.to.name||postData.to.data[postData.to.data.length - 1].name)+"'s timeline.", postData.id);    
			}
			else
			{
				heading = generatePanelHeading(postData.from.name+" posted.", postData.id);
			}
			body = generatePanelBody(postData.message, postData.created_time);
			postDiv.append(heading + body);
		}
		else if (postData.story)
		{
			var storySplit = postData.story.split('"');
			if (storySplit.length == 1)
			{
				postDiv.remove();
				console.log ('removing');
				return;
			}
			
			if (postData.status_type && postData.status_type == "wall_post")
			{
				var comment = storySplit.slice(1, storySplit.length-1).join('"');
				heading = generatePanelHeading(postData.from.name +" posted"+ storySplit[storySplit.length-1], postData.id);
				body = generatePanelBody(comment, postData.created_time);
				postDiv.append(heading + body);
			}

			else // No comment related posts.
			{
				postDiv.remove();
				console.log ('removing');
				return;
				// heading = generatePanelHeading(postData.from.name +" commented"+ storySplit[storySplit.length-1]);
			}
		}
	}
	else if (postData.type == "link") 
	{
		var heading, body;
		if (postData.message)
			body = generateLinkAndVideoPanelBody(postData.message, postData.link, postData.picture, (postData.description||"No description found."), postData.created_time);   
		else
		{
			postDiv.remove();
			return;
		}
		if (postData.story || postData.name)
			heading = generatePanelHeading(postData.from.name + " posted a link: " + (postData.story || postData.name), postData.id);
		else
		{
			heading = generatePanelHeading(postData.from.name + " posted a link: ", postData.id);
			console.log (postData);
		}    

		postDiv.append(heading + body);
	}
	else if (postData.type == "photo") 
	{
		var heading, body;
		if (postData.message || postData.description)
			body = generatePhotoPanelBody((postData.message || postData.description), postData.link, postData.picture, postData.created_time);  
		else
		{
			postDiv.remove();
			return;
		}
		if (postData.status_type === "tagged_in_photo")
			heading = generatePanelHeading(postData.story, postData.id);
		else if (postData.to) 
			heading = generatePanelHeading(postData.from.name + " posted a photo to " + (postData.to.name || postData.to.data[postData.to.data.length - 1].name) + "'s timeline", postData.id);
		else
			heading = generatePanelHeading(postData.from.name + " posted a photo", postData.id);
		// console.log (heading);
		postDiv.append(heading + body);
	}
	else if (postData.type == "video") 
	{
		var heading, body;
		if (postData.message || postData.description)
			// body = generatePanelBody(postData.message || postData.description);  
			body = generateLinkAndVideoPanelBody((postData.message || postData.description), postData.link, postData.picture, (postData.description || "No description found."), postData.created_time);   
		else
		{
			postDiv.remove();
			return;
		}
		if (postData.to)
		{

			heading = generatePanelHeading(postData.from.name + " posted a video to " + (postData.to.name || postData.to.data[postData.to.data.length - 1].name) + "'s timeline", postData.id);
		}
		else
			heading = generatePanelHeading(postData.from.name + " posted a video", postData.id);
		// console.log (heading);
		postDiv.append(heading + body);
	}
}

function escapeRegExp(string) {
	return string.replace(/([.*+?^=!:${}()|\[\]\/\\])/g, "\\$1");
}

function replaceAll(find, replace, str) {
	return str.replace(new RegExp(escapeRegExp(find), 'i'), replace);
}

function highlight(find, str) {
	var reg = new RegExp(find, 'gi');
	return str.replace (reg, function(str) {return "<span class = 'highlight'>" + str + "</span>";});
}

function processMessage (message)
{
	// message = message.replace(/'/g,"\\\'");
	strippedQuery = query.replace(/[\.,-\/#!$%\^&\*;:{}=\-_`~()]/," ");
	querySplit = query.split(' ');
	for (termIndex in querySplit)
	{
		message = highlight(querySplit[termIndex], message);
	}
	message = message.replace(/\n/g, "<br />");
	return message;
}

function generatePostPanel (postID)
{
	return '<div id="'+postID+'parent" class="panel panel-primary"><div class="panel-heading">'+'Loading...'+'</div></div>';
}
function generateWarningPanel (message)
{
	return '<div class="panel panel-warning"><div class="panel-heading">'+message+'</div></div>';
}    

function generateDangerPanel (message)
{
	return '<div class="panel panel-danger"><div class="panel-heading">'+message+'</div></div>';
}
function generatePanelHeading (message, id)
{
	idSplit = id.split('_');
	link = "https:facebook.com/" + idSplit[0] + '/posts/'+ idSplit[1];
	return '<div class="panel-heading"><a target="_blank" href = "'+ link +'">'+message+'</a></div>';
}

function generatePanelBody (message, timestamp)
{
	return '<div class="panel-body word-wrap"><p>'+processMessage(message)+'</p><hr><small>Posted <abbr class="timeago" title="'+timestamp+'"></abbr></small></div>';
}

function generateLinkAndVideoPanelBody (message, link, pictureSource, description, timestamp)
{
	// console.log (message);
	processMessage(message);
	// console.log ("yo");
	return '<div class="panel-body"><p>'+processMessage(message)+'</p><hr><a target="_blank" href="'+ link + '"><div class="row"><div class="col-md-2"><img class="img-rounded img-responsive" src="'+pictureSource+'"></div><div class="col-md-10"><div class="well link-description">'+processMessage(description)+'</div></div></div></a><hr><small>Posted <abbr class="timeago" title="'+timestamp+'"></abbr></small></div>';
}

function generatePhotoPanelBody (message, link, pictureSource, timestamp)
{
	return '<div class="panel-body"><p>'+processMessage(message)+'</p><hr><a target="_blank" href="'+link+'"><div class="row"><div class="col-md-8 col-md-offset-2"><img class="post-img img-rounded img-responsive" src="'+pictureSource+'"></div></div></a><hr><small>Posted <abbr class="timeago" title="'+timestamp+'"></abbr></small></div>';
}


function adjustModalMaxHeightAndPosition(){
	$('.modal').each(function(){
		if($(this).hasClass('in') == false){
			$(this).show();
		}
		var contentHeight = $(window).height() - 60;
		var headerHeight = $(this).find('.modal-header').outerHeight() || 2;
		var footerHeight = $(this).find('.modal-footer').outerHeight() || 2;

		$(this).find('.modal-content').css({
			'max-height': function () {
				return contentHeight;
			}
		});

		$(this).find('.modal-body').css({
			'max-height': function () {
				return contentHeight - (headerHeight + footerHeight);
			}
		});

		$(this).find('.modal-dialog').addClass('modal-dialog-center').css({
			'margin-top': function () {
				return -($(this).outerHeight() / 2);
			},
			'margin-left': function () {
				return -($(this).outerWidth() / 2);
			}
		});
		if($(this).hasClass('in') == false){
			$(this).hide();
		}
	});
}
if ($(window).height() >= 320){
	$(window).resize(adjustModalMaxHeightAndPosition).trigger("resize");
}



