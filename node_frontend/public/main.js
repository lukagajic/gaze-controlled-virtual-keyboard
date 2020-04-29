const socket = io.connect('http://localhost:3000');

socket.on('gaze', (data) => {
    if(data === 'L') {
        console.log(`User looked left!`);
    }
    if(data === 'R') {
        console.log(`User looked right!`);
    }
});