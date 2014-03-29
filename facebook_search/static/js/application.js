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

var queryForm = $('#query-form');
queryForm.submit(function () {
    $.ajax({
        type: queryForm.attr('method'),
        url: queryForm.attr('action'),
        data: queryForm.serialize(),
        success: function (data) {
            console.log(data);
        },
        error: function(data) {
            console.log ("error" + data);
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