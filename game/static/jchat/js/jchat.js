var chat_room_id = undefined;
var last_received = 0;
var jchat_username = '';

/**
 * Initialize chat:
 * - Set the room id
 * - Generate the html elements (chat box, forms & inputs, etc)
 * - Sync with server
 * @param chat_room_id the id of the chatroom
 * @param html_el_id the id of the html element where the chat html should be placed
 * @return
 */

//CACHE PREVENTION LOGIC
var jchat_timestamp = 1;
function gen_jchat_timestamp() {
  jchat_timestamp = jchat_timestamp + 1;
}

setInterval("gen_jchat_timestamp()", 500);
function init_chat(chat_id, html_el_id, input_username) {
	chat_room_id = chat_id;
        jchat_username = input_username;
	layout_and_bind(html_el_id);
	sync_messages();
}

var img_dir = "/static/img/";

/**
 * Asks the server which was the last message sent to the room, and stores it's id.
 * This is used so that when joining the user does not request the full list of
 * messages, just the ones sent after he logged in. 
 * @return
 */
function sync_messages() {
    $.ajax({
        //type: 'POST',
        type: 'GET',
        data: {id:window.chat_room_id, username:window.jchat_username, ts:window.jchat_timestamp},
        url:'/chat/sync/',
		dataType: 'json',
                cache:false,
		success: function (json) {
        	last_received = json.last_message_id;
		}        
    });
	
	setTimeout("get_messages()", 2000);
}

/**
 * Generate the Chat box's HTML and bind the ajax events
 * @param target_div_id the id of the html element where the chat will be placed 
 */
function layout_and_bind(html_el_id) {
		// layout stuff
		var html = '<br><div id="chat-messages-container">'+
		'<div id="chat-messages"> </div>'+
		'<div id="chat-last"> </div>'+
		'</div>'+
                '<div id="chat-form-div">'+
		'<form id="chat-form">'+
		'<input name="message" type="text" class="message" />';
                if(platform != 'mobile') {
                  html += '<input type="submit" class="button" style="width: 20%;" value="Say!!!"/>';
                }
                else {
                  html += '<br><input type="submit" class="button" style="width: 100%;" value="Say!!!"/>';
                }
                html +=  
		'</form>'+
                '</div>';
		
		$("#"+html_el_id).append(html);
		
		// event stuff
    	$("#chat-form").submit( function () {
            var $inputs = $(this).children('input');
            var values = {};
            
            $inputs.each(function(i,el) { 
            	values[el.name] = $(el).val();
            });
			values['chat_room_id'] = window.chat_room_id;
        	
        	$.ajax({
                data: values,
                dataType: 'json',
                //JG: try GET, I've had trouble with  ajax and POST before
                //type: 'post',
                type: 'get',
                url: '/chat/send/'
            });
            $('#chat-form .message').val('');
            return false;
	});
};

/**
 * Gets the list of messages from the server and appends the messages to the chatbox
 */
function get_messages() {
    $.ajax({
        //JG: try GET, I've had trouble with  ajax and POST before
        //type: 'POST',
        type: 'GET',
        data: {id:window.chat_room_id, offset: window.last_received,username:window.jchat_username,ts:window.jchat_timestamp},
        url:'/chat/receive/',
		dataType: 'json',
                cache:false,
		success: function (json) {
			var scroll = false;
		
			// first check if we are at the bottom of the div, if we are, we shall scroll once the content is added
			var $containter = $("#chat-messages-container");
			if ($containter.scrollTop() == $containter.attr("scrollHeight") - $containter.height())
				scroll = true;

			// add messages
			$.each(json, function(i,m){
				if (m.type == 's')
					$('#chat-messages').append('<div class="system">' + replace_emoticons(m.message) + '</div>');
				else if (m.type == 'm') 	
					$('#chat-messages').append('<div class="message"><div class="author">'+m.author+'</div>'+replace_emoticons(m.message) + '</div>');
				else if (m.type == 'j') 	
					$('#chat-messages').append('<div class="join">'+m.author+' has joined</div>');
				else if (m.type == 'l') 	
					$('#chat-messages').append('<div class="leave">'+m.author+' has left</div>');
					
				last_received = m.id;
			})
			
			// scroll to bottom
			if (scroll)
				$("#chat-messages-container").animate({ scrollTop: $("#chat-messages-container").attr("scrollHeight") }, 500);
		}        
    });
    
    // wait for next
    setTimeout("get_messages()", 1000);
}

/**
 * Tells the chat app that we are joining
 */
function chat_join() {
	$.ajax({
		async: false,
        //type: 'POST',
        type: 'GET',
        cache:false,
        data: {chat_room_id:window.chat_room_id},
        url:'/chat/join/'
    });
}

/**
 * Tells the chat app that we are leaving
 */
function chat_leave() {
	$.ajax({
		async: false,
        type: 'GET',
        cache:false,
        data: {chat_room_id:window.chat_room_id},
        url:'/chat/leave/'
    });
}

// attach join and leave events
$(window).load(function(){chat_join()});
$(window).unload(function(){chat_leave()});

// emoticons
var emoticons = {                 
	'>:D' : 'emoticon_evilgrin.png',
	':D' : 'emoticon_grin.png',
	'=D' : 'emoticon_happy.png',
	':\\)' : 'emoticon_smile.png',
	':O' : 'emoticon_surprised.png',
	':P' : 'emoticon_tongue.png',
	':\\(' : 'emoticon_unhappy.png',
	':3' : 'emoticon_waii.png',
	';\\)' : 'emoticon_wink.png',
	'\\(ball\\)' : 'sport_soccer.png'
}

/**
 * Regular expression maddness!!!
 * Replace the above strings for their img counterpart
 */
function replace_emoticons(text) {
	$.each(emoticons, function(char, img) {
		re = new RegExp(char,'g');
		// replace the following at will
		text = text.replace(re, '<img src="'+img_dir+img+'" />');
	});
	return text;
}
