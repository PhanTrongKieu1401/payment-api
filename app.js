const express = require("express");
const axios = require("axios");
const Stomp = require('stompjs');
const WebSocket = require('ws');
const cors = require("cors");

const app = express();
const port = 3000;
app.use(cors());
app.use(express.json());
app.use(express.urlencoded());

const MomoRequest = {
    partnerCode: String,
    orderId: String,
    amount: String,
    ids: String
}

const socket = new WebSocket('ws://localhost:8080/ws');
const stompClient = Stomp.over(socket);

let reconnectInterval = 10000; 
let maxReconnectAttempts = 10; 
let reconnectAttempts = 0;

stompClient.connect({}, (frame) => {
    console.log('Connected to WebSocket with STOMP');
    // setInterval(() => {
    //     if (stompClient.connected) {
    //         stompClient.send('/app/order', {}, 'ping');
    //         console.log('Sent keep-alive ping');
    //     }
    // }, 30000);
}, (error) => {
    console.error('WebSocket connection error:', error);
    if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        console.log(`Attempting to reconnect (#${reconnectAttempts})...`);
        setTimeout(stompConnect.connect, reconnectInterval); 
    } else {
        console.error('Max reconnect attempts reached. Could not reconnect to WebSocket.');
    }
});

app.post("/api/payment-with-momo", async (req, res) => {
    const { partnerCode, orderId, amount, ids } = req.body;

    var accessKey = 'F8BBA842ECF85';
    var secretKey = 'K951B6PE1waDMi640xX08PD3vg6EkVlz';
    var orderInfo = 'Thanh toán đơn hàng Kikimoon supermarket';
    // var partnerCode = 'MOMO';
    // var redirectUrl = `http://localhost:5173/order/${orderId}`;
    var redirectUrl = 'http://localhost:5173/order/' + orderId;
    var ipnUrl = 'https://adapted-ox-suitably.ngrok-free.app/callback';
    var requestType = 'payWithMethod';
    // var amount = '100000';
    // var orderId = partnerCode + new Date().getTime();
    var requestId = orderId;
    var extraData = '';
    var orderGroupId = '';
    var autoCapture = true;
    var lang = 'vi';
    var partnerName = 'MoMo Payment';
    var storeId = 'Momo Kikimoon supermarket';

    // HMAC SHA256 signature
    var rawSignature = "accessKey="+accessKey+"&amount=" + amount+"&extraData=" + extraData+"&ipnUrl=" + ipnUrl+"&orderId=" + orderId+"&orderInfo=" + orderInfo+"&partnerCode=" + partnerCode +"&redirectUrl=" + redirectUrl+"&requestId=" + requestId+"&requestType=" + requestType
    //puts raw signature
    console.log("--------------------RAW SIGNATURE----------------")
    console.log(rawSignature)

    // Create signature using secretKey
    const crypto = require('crypto');
    var signature = crypto.createHmac('sha256', secretKey)
        .update(rawSignature)
        .digest('hex');
    console.log("--------------------SIGNATURE----------------")
    console.log(signature)

    // JSON object to send to MoMo endpoint
    const requestBody = JSON.stringify({
        partnerCode: partnerCode,
        partnerName: partnerName,
        storeId: storeId,
        requestId: requestId,
        amount: amount,
        orderId: orderId,
        orderInfo: orderInfo,
        redirectUrl: redirectUrl,
        ipnUrl: ipnUrl,
        lang: lang,
        requestType: requestType,
        autoCapture: autoCapture,
        extraData: extraData,
        orderGroupId: orderGroupId,
        signature: signature
    });

    // const options = {
    //     method: "POST",
    //     url: "https://test-payment.momo.vn/v2/gateway/api/create",
    //     headers: {
    //         'Content-Type': 'application/json',
    //         'Content-Length': Buffer.byteLength(requestBody)
    //     },
    //     data: requestBody
    // }

    try {
        console.log("Sending....");

        const response = await axios.post('https://test-payment.momo.vn/v2/gateway/api/create', requestBody, {
            headers: {
                'Content-Type': 'application/json'
            }
        });

        console.log(`Status: ${response.status}`);
        console.log(`Headers: ${JSON.stringify(response.headers)}`);
        console.log('Body: ', response.data);
        
        return res.json({ shortLink: response.data.shortLink });
    } catch (error) {
        window.location.href = response.shortLink;
        console.error("Error in paymentWithMomo:", error.response ? error.response.data : error.message);
        return res.status(500).json({ error: 'Payment request failed.' });
    }
});

app.post("/callback", async (req, res) => {
    console.log("CALLBACK ::");
    console.log(req.body);

    if (stompClient.connected) {
        stompClient.send('/app/order', {}, JSON.stringify({
            partnerCode: req.body.partnerCode,
            orderId: req.body.orderId,
            resultCode: req.body.resultCode
        }));
        console.log('Order message sent:', JSON.stringify({
            partnerCode: req.body.partnerCode,
            orderId: req.body.orderId,
            resultCode: req.body.resultCode}));
    } else {
        console.error('WebSocket connection is not open');
    }
    return res.status(200).json(req.body);
})

app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});
