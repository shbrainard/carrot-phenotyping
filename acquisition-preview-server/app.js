const fs = require("fs");
const path = require("path");
const express = require("express");
const http = require("http");
const EventEmitter = require("events");
const WebSocket = require("ws");
const cors = require("cors");

// require('dotenv').config()

const app = express();

app.use(cors());

const server = http.createServer(app);

const wss = new WebSocket.Server({ server });

const getSrc = () => {
  for (const arg of process.argv) {
    if (arg.includes("src")) {
      let src = arg.split("=")[1];
      return src;
    }
  }
};

const fileChange = new EventEmitter();

wss.on("listening", ws => {
  const src = getSrc();
  console.log("will look for files here:", src);

  const eventsOfInterest = ["change", "rename"];
  fs.watch(src, (eventType, filename) => {
    console.log(`event type is: ${eventType}`);
    console.log(`filename is: ${filename}`);

    if (filename && eventsOfInterest.includes(eventType)) {
      const absolutePath = path.join(src, filename);
      fileChange.emit("event", absolutePath);
    } else if (!filename) {
      console.log("filename not provided");
    }
  });
});

wss.on("connection", function connection(ws) {
  fileChange.on("event", src => {
    const responseData = {};

    if (src.includes("mask")) {
      responseData.type = "mask";
    } else if (src.includes("overlay")) {
      responseData.type = "overlay";
    }

    fs.readFile(src, (err, data) => {
      responseData.src = data.toString("base64");
      ws.send(JSON.stringify({ responseData }));
    });
  });

  console.log("new connection!");
});

server.listen(7777, function listening() {
  console.log("Listening on %d", server.address().port);
});

process.on("SIGINT", () => {
  console.info("SIGTERM signal received.");
  console.log("Closing http server.");
  process.exit(0);
});

module.exports = server;
