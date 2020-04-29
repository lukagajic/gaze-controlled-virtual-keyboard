const express = require('express');
const socket = require('socket.io');

const amqp = require('amqplib/callback_api');

amqp.connect('amqp://localhost', (error0, connection) => {
    if(error0) {
        throw error0;
    }
    connection.createChannel((error1, channel) => {
        if(error1) {
            throw error1
        }

        let queue = 'gaze';

        channel.assertQueue(queue, {
            durable: false
        });

        console.log(` [*] Waiting for messages in ${queue}. To exit press CTRL + C`)

        channel.consume(queue, (msg) => {
            console.log(` [x] Received ${msg.content.toString()}`);
            io.sockets.emit('gaze', msg.content.toString());
        }, {
            noAck: true
        });

    })
})

const app = express();

const server = app.listen(3000, () => {
    console.log(`Server started on port 3000`);
})

app.use(express.static('public'));

const io = socket(server);

io.on('connection', (socket) => {
    console.log(`made socket connection`);
});