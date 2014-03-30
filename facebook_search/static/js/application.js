var reindexButton = $('#reindex-form');
reindexButton.submit(function () {
    $.ajax({
        type: reindexButton.attr('method'),
        url: reindexButton.attr('action'),
        data: reindexButton.serialize(),
        success: function (data) {
            console.log(data);
        },
        error: function(data) {
            console.log (data);
        }
    });
    return false;
});

$(document).ready(function(){
    
    $.ajax({
        type: 'get',
        url: '/profile-picture/',
        success: function (data) {
            var profilePicture = $("#profile-picture");
            console.log (data);
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
    $.ajax({
        type: queryForm.attr('method'),
        url: queryForm.attr('action'),
        data: queryForm.serialize(),
        success: function (data) {
            processSearchResults(data);
        },
        error: function(data) {
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
    else 
    {
        var html = '<div id = "results-container">';
        for (var i = 0; i < results.count; i++)
        {
            var postID = results.data[i];
            console.log(postID);
            html += generatePostPanel(postID);
            $.ajax({
                type: 'get',
                url: '/graph-post/'+postID+'/',
                success: function (postData) {
                    udpatePostPanel(postData);
                },
                error: function(data) {
                    console.log ("error");
                    console.log (data);
                }
            });
            udpatePostPanel(postID);

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
            if (postData.to)
            {
                heading = generatePanelHeading(postData.from.name+" posted on "+postData.to.name+"'s wall:");    
            }
            else
            {
                heading = generatePanelHeading(postData.from.name+" posted:");
            }
            body = generatePanelBody(postData.message);
            postDiv.append(heading + body);
        }
        else if (postData.story)
        {
            var storySplit = postData.story.split('"');
            console.log (storySplit);
            if (storySplit.length == 1)
            {
                postDiv.remove();
                return;
            }
            
            var comment = storySplit[1];
            if (postData.status_type && postData.status_type == "wall_post")
            {
                heading = generatePanelHeading(postData.from.name +" posted"+ storySplit[storySplit.length-1]);
            }
            else
            {
                heading = generatePanelHeading(postData.from.name +" commented"+ storySplit[storySplit.length-1]);
            }
            body = generatePanelBody(comment);
            postDiv.append(heading + body);
        }
    }
    else if (postData.type = "link") 
    {
        var heading, body;
        if (postData.description)
        {
            body = generatePanelBody(postData.description);   
        }
        if (postData.message)
        {
            body = generatePanelBody(postData.message);
        }
        if (postData.story)
        {
            heading = generatePanelHeading("Link: "+postData.story);
        }
        else if (postData.name)
        {
            heading = generatePanelHeading("Link: "+postData.name);
        }
        postDiv.append(heading + body);
    }
    else if (postData.type = "photo") 
    {
        var heading, body;
        if (postData.description)
        {
            body = generatePanelBody(postData.description);   
        }
        if (postData.message)
        {
            body = generatePanelBody(postData.message);
        }
        if (postData.story)
        {
            heading = generatePanelHeading("Photo: "+postData.story);
        }
        else if (postData.name)
        {
            heading = generatePanelHeading("Photo: "+postData.name);
        }
    }
    else if (postData.type = "video") 
    {
        var heading, body;
        if (postData.description)
        {
            body = generatePanelBody(postData.description);   
        }
        if (postData.message)
        {
            body = generatePanelBody(postData.message);
        }
        if (postData.story)
        {
            heading = generatePanelHeading("Video: "+postData.story);
        }
        else if (postData.name)
        {
            heading = generatePanelHeading("Video: "+postData.name);
        }
    }
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
function generatePanelHeading (message)
{
    return '<div class="panel-heading">'+message+'</div>';
}
function generatePanelBody (message)
{
    return '<div class="panel-body">'+message+'</div>';
}
