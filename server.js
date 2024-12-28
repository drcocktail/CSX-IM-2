const express = require('express');
const crypto = require('crypto');
const bodyParser = require('body-parser');
const axios = require('axios');
const dotenv = require('dotenv');
dotenv.config();

const app = express();
app.use(bodyParser.json());

const VERIFY_TOKEN = process.env.VERIFY_TOKEN;
const APP_SECRET = process.env.APP_SECRET;
const ACCESS_TOKEN = process.env.ACCESS_TOKEN;  
const IG_ID = process.env.IG_ID;
console.log (VERIFY_TOKEN);
console.log (APP_SECRET);
console.log (ACCESS_TOKEN);
console.log(IG_ID);


const FLASK_SERVER = 'http://localhost:3000';

app.get('/webhooks', (req, res) => {
    // Parse the query params
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];

    console.log('Received webhook verification:');
    console.log('Mode:', mode);
    console.log('Token:', token);
    console.log('Challenge:', challenge);

    // For Instagram, we need to be more explicit about the checks
    if (!mode || !token || !challenge) {
        console.error('Missing required parameters');
        return res.sendStatus(403);
    }

    if (mode === 'subscribe' && token === process.env.VERIFY_TOKEN) {
        console.log('WEBHOOK_VERIFIED');
        // Instagram specifically needs the challenge returned as a string
        return res.status(200).send(challenge);
    }

    console.error('Verification failed');
    return res.sendStatus(403);
});

// Webhook endpoint for receiving updates
app.post('/webhooks', (req, res) => {
    const signature = req.headers['x-hub-signature-256'];
    
    // Verify Instagram signature first
    if (!verifySignature(req.body, signature)) {
        console.error('Invalid signature');
        return res.sendStatus(403);
    }

    const body = req.body;

    console.log('Received webhook:', JSON.stringify(body, null, 2));

    // Instagram specific object check
    if (body.object === 'instagram') {
        // Send the OK response immediately as required by Instagram
        res.status(200).send('EVENT_RECEIVED');

        // Process the Instagram updates
        if (body.entry && body.entry.length > 0) {
            body.entry.forEach((entry) => {
                // Handle Instagram messaging specific events
                if (entry.messaging) {
                    entry.messaging.forEach((messagingEvent) => {
                        console.log('Processing message:', messagingEvent);
                        // Your message handling logic here
                        // This is where you'd send to your Flask server
                    });
                }
            });
        }
    } else {
        // Not from Instagram
        res.sendStatus(404);
    }
});

function verifySignature(payload, signature) {
    if (!signature) return false;
    const sig = signature.split('sha256=')[1];
    const expectedSignature = crypto
        .createHmac('sha256', APP_SECRET)
        .update(JSON.stringify(payload))
        .digest('hex');
    return crypto.timingSafeEqual(
        Buffer.from(sig),
        Buffer.from(expectedSignature)
    );
}

// Updated handle message function to process messages through Flask
async function handleMessage(event) {
    if (event.message && event.message.text) {
        const senderId = event.sender.id;
        const message = event.message.text;

        console.log('Processing message:', {
            from: senderId,
            message: message
        });

        try {
            // Forward to Flask server
            const flaskResponse = await axios.post(`${FLASK_SERVER}/query`, {
                username: senderId,  // Using sender ID as username
                query: message
            });

            // Send response back to Instagram
            await sendInstagramMessage(senderId, flaskResponse.data.response);

        } catch (error) {
            console.error('Error processing message:', error);
            // Send error message back to user
            await sendInstagramMessage(
                senderId, 
                "I apologize, but I'm having trouble processing your message right now. Please try again later."
            );
        }
    }
}

// Function to send messages back to Instagram
async function sendInstagramMessage(recipientId, message) {
    try {
        const response = await axios.post(
            `https://graph.instagram.com/v21.0/me/messages`,
            {
                recipient: { id: recipientId },
                message: { text: message }
            },
            {
                headers: {
                    'Authorization': `Bearer ${ACCESS_TOKEN}`,
                    'Content-Type': 'application/json'
                }
            }
        );
        console.log('Message sent successfully:', response.data);
        return response.data;
    } catch (error) {
        console.error('Error sending message to Instagram:', error);
        throw error;
    }
}

const PORT = process.env.PORT || 6969; 
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});