var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

function joinGame(gameId) {
    currentGameId = gameId;
    socket.emit('join', {game_id: gameId});
    document.getElementById('chat-box').innerHTML = '';  // 清空聊天记录
}

function sendMessage() {
    var messageInput = document.getElementById('message');
    var message = messageInput.value.trim();  // 去除两端空格
    if (message.length > 0) {  // 检查消息是否为空
        messageInput.value = '';
        socket.emit('send_message', {text: message, game_id: currentGameId});
    }
}

socket.on('receive_message', function(data) {
    if (data.game_id == currentGameId) {
        var chatBox = document.getElementById('chat-box');
        var msgElement = document.createElement('div');
        msgElement.className = "chat-message";  // 可以在CSS中定义样式
        msgElement.innerText = data.username + ': ' + data.text;
        chatBox.appendChild(msgElement);

        // 保持滚动到最新的消息
        chatBox.scrollTop = chatBox.scrollHeight;
    }
});
