let chat_socket;
let audioQueue = [];
let isPlaying = false;
let refreshMsgText = false;

// Get agent configuration from global variable
const agentConfig = window.AGENT_CONFIG || {};
const language = agentConfig.language || "english";
const agentId = agentConfig.id || "default";

const chatContainer = document.getElementById('chat_container');
const userMsgDiv = document.getElementById('user-msg');
const llmResponseDiv = document.getElementById('llm-msg');
let audioContext = new (window.AudioContext || window.webkitAudioContext)();

console.log("Agent Configuration:", agentConfig);

async function getMicrophone() {
  const userMedia = await navigator.mediaDevices.getUserMedia({
    audio: true,
  });

  return new MediaRecorder(userMedia);
}

async function openMicrophone(microphone, socket) {
  await microphone.start(500);

  microphone.onstart = () => {
    console.log("client: microphone opened for agent:", agentId);
  };

  microphone.onstop = () => {
    console.log("client: microphone closed for agent:", agentId);
  };

  microphone.ondataavailable = (e) => {
    // sending data to server via streaming
    socket.send(e.data);
    console.log(`Data-Sent for agent ${agentId}:`, socket);
  };
}

async function closeMicrophone(microphone) {
  microphone.stop();
}

async function start(socket) {
  const listenButton = document.getElementById("record");
  let microphone;

  console.log("client: waiting to open microphone for agent:", agentId);

  listenButton.addEventListener("click", async () => {
    if (!microphone) {
      // open microphone
      microphone = await getMicrophone();
      await openMicrophone(microphone, socket);
    } else {
      // close microphone
      await closeMicrophone(microphone);
      // clearing chat boxes
      userMsgDiv.innerHTML = "";
      llmResponseDiv.innerHTML = "";

      stopAudio();
      microphone = undefined;
    }
  });
}

function stopAudio() {
  // Clear the audio queue and stop current playback
  audioQueue = [];
  isPlaying = false;
  console.log("Audio stopped and queue cleared for agent:", agentId);
}

function playNextAudio() {
  if (audioQueue.length > 0 && !isPlaying) {
    isPlaying = true;
    const data = audioQueue.shift();
    console.log(`Playing audio chunk for agent ${agentId}, ${audioQueue.length} remaining in queue`);
    playAudio(data);
  }
}

function playAudio(data) {
  const sampleRate = 16000;  // Your specified sample rate
  const numChannels = 1;  // Assuming mono audio

  console.log("client: decoding base64 data for agent:", agentId);
  // Decode base64 to Uint8Array
  const byteString = atob(data);
  const len = byteString.length;
  const uint8Array = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    uint8Array[i] = byteString.charCodeAt(i);
  }

  console.log("client: creating AudioBuffer for agent:", agentId);
  // Create an AudioBuffer
  const audioBuffer = audioContext.createBuffer(numChannels, uint8Array.length / 2, sampleRate);

  console.log("client: converting PCM to float values for agent:", agentId);
  // Convert PCM to float values
  for (let channel = 0; channel < numChannels; channel++) {
    const nowBuffering = audioBuffer.getChannelData(channel);
    for (let i = 0; i < nowBuffering.length; i++) {
      const sample = (uint8Array[i * 2 + 1] << 8) | (uint8Array[i * 2] & 0xff);
      nowBuffering[i] = (sample >= 0x8000 ? sample - 0x10000 : sample) / 32768.0;  // Normalize 16-bit PCM
    }
  }

  console.log("client: playing audio for agent:", agentId);
  // Play the buffer
  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  source.onended = () => {
    console.log("Audio chunk finished playing for agent:", agentId);
    isPlaying = false;
    playNextAudio(); // Try to play next chunk
  };
  source.start(0);
}

function getWebSocketURL(path = "") {
  var protocolPrefix =
    window.location.protocol === "https:" ? "wss:" : "ws:";
  var host = window.location.host; // Includes hostname and port

  return protocolPrefix + "//" + host + path;
}

function addUserMessage(message) {
  userMsgDiv.innerHTML = message;
}

function addLlmMessage(response) {
  if (refreshMsgText && response) {
    llmResponseDiv.innerHTML = response;
    refreshMsgText = false;
  } else {
    if (response) {
      llmResponseDiv.innerHTML = llmResponseDiv.innerHTML += response;
    }
  }
}

function sendMessage() {
  let user_msg = inputField.value;
  if (user_msg) {
    let data_sent = JSON.stringify({ "user_msg": user_msg });
    chat_socket.send(data_sent);
    inputField.value = "";
    addUserMessage(user_msg);
  }
}

window.addEventListener("load", () => {
  // URL for WebSocket connection with agent ID
  // const websocketUrl = getWebSocketURL(`/ws/phone?language=${language}`);
  const websocketUrl = getWebSocketURL(`/ws/phone/agent/${agentId}?language=${language}`);
  console.log("WebSocket URL for agent:", websocketUrl);

  socket = new WebSocket(websocketUrl);
  
  // Handle WebSocket events
  socket.onopen = async () => {
    console.log('WebSocket connection opened for agent:', agentId);
    setTimeout(() => { }, 1000);
    await start(socket);
  };

  socket.onmessage = (event) => {
    let event_parsed = JSON.parse(event.data);
    console.log(`Data-Rcvd for agent ${agentId}:`, JSON.stringify(event_parsed));

    if (event_parsed.is_text == true) {
      console.log("---> Text for agent", agentId, { event_parsed });
      let msg = event_parsed.msg;
      if (event_parsed.is_transcription == true) {
        addUserMessage(msg);
      } else {
        if (event_parsed.is_end) {
          refreshMsgText = true;
        }
        addLlmMessage(msg);
      }
    } else {
      console.log("[AUDIO_RECIEVED] for agent", agentId, event_parsed);
      if (event_parsed.is_clear_event == true) {
        console.log("[CLEAR_BUFFER_EVENT_RECIEVED] - Clearing audio queue for agent:", agentId);
        audioQueue = [];
        isPlaying = false; // Reset playing state
      } else {
        let audio_data = event_parsed.audio;
        if (audio_data) {
          console.log(`[AUDIO_QUEUED] Adding audio to queue for agent ${agentId}, current queue length: ${audioQueue.length}`);
          audioQueue.push(audio_data);
          // Always try to play next audio when new audio is received
          playNextAudio();
        } else {
          console.log("[AUDIO_ERROR] No audio data in message for agent:", agentId);
        }
      }
    }
  };

  socket.onclose = () => {
    console.log('WebSocket connection closed for agent:', agentId);
  };

  socket.onerror = (error) => {
    console.error('WebSocket error for agent:', agentId, error);
  };
});