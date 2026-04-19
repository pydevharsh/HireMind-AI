window.addEventListener("DOMContentLoaded", () => {
    /* =========================================================
       🌐 GLOBAL STATE
       ========================================================= */

    let emotion = "neutral";



    /* =========================================================
       📷 CAMERA INITIALIZATION
       ========================================================= */

    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            const videoEl = document.getElementById("video");
            if (videoEl) videoEl.srcObject = stream;
        })
        .catch(() => {
            const emotionEl = document.getElementById("emotionText");
            if (emotionEl) emotionEl.innerText = "Camera permission denied";
        });



    /* =========================================================
       🙂 FAKE EMOTION DETECTOR (Placeholder)
       ========================================================= */

    setInterval(() => {
        let emotions = ["confident", "confused", "neutral"];
        emotion = emotions[Math.floor(Math.random() * 3)];
        const emotionEl = document.getElementById("emotionText");
        if (emotionEl) emotionEl.innerText = "Emotion: " + emotion;
    }, 3000);



    /* =========================================================
       🔊 FALLBACK BROWSER SPEECH (Used only if server audio fails)
       ========================================================= */

    function speak(text) {
        let voices = speechSynthesis.getVoices();
        let hindiVoice = voices.find(v => v.lang === "hi-IN") || voices[0];
        let s = new SpeechSynthesisUtterance(text);
        s.voice = hindiVoice;
        s.lang = "hi-IN";
        s.rate = 0.9;
        speechSynthesis.cancel();
        speechSynthesis.speak(s);
    }



    /* =========================================================
       💬 CHAT UI HANDLERS
       ========================================================= */

    function add(msg, isAI = false) {
        let c = document.getElementById("chat");
        c.innerHTML += "<p>" + msg.replace(/\n/g, "<br>") + "</p>";
        c.scrollTop = c.scrollHeight;
        if (isAI) speak(msg); // fallback voice
    }

    function typing() {
        document.getElementById("chat").innerHTML += "<p id='typing'>🤖 typing...</p>";
    }

    function removeTyping() {
        let t = document.getElementById("typing");
        if (t) t.remove();
    }



    /* =========================================================
       ⌨️ SEND MESSAGE TO BACKEND  ⭐ AUDIO SUPPORT ADDED
       ========================================================= */

    function send() {
        let input = document.getElementById("userInput");
        let msg = input.value.trim();

        if (msg === "") {
            document.getElementById("error").innerText = "⚠️ खाली संदेश नहीं भेज सकते";
            return;
        }

        document.getElementById("error").innerText = "";
        add("👤 " + msg);
        typing();

        fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: msg, emotion: emotion })
        })
            .then(r => r.json())
            .then(d => {
                removeTyping();
                add("🤖 " + d.reply);

                // ⭐ SERVER VOICE PLAY (NEW)
                if (d.audio) {
                    const audio = new Audio(d.audio);
                    audio.play();
                } else {
                    speak(d.reply); // fallback
                }
            })
            .catch(() => {
                removeTyping();
                add("🤖 सर्वर समस्या, फिर कोशिश करें");
            });

        input.value = "";
    }



    /* =========================================================
       ⏎ ENTER KEY SUPPORT
       ========================================================= */

    document.getElementById("userInput").addEventListener("keydown", e => {
        if (e.key === "Enter") { e.preventDefault(); send(); }
    });



    /* =========================================================
       📤 OLD UPLOAD FUNCTIONS (LEGACY) — COMMENTED
       ========================================================= */

    /*
    function uploadResume() { ...old version... }
    function uploadResume() { ...old version v2... }
    */



    /* =========================================================
       📄 FINAL RESUME UPLOAD FUNCTION (SYNCED WITH BACKEND)
       ========================================================= */

    async function uploadResume() {
        const fileInput = document.getElementById("fileInput");
        const fileNameText = document.getElementById("fileName");
        const uploadText = document.getElementById("uploadText");
        const uploadBox = document.getElementById("uploadBox");

        const file = fileInput.files[0];
        if (!file) return;

        fileNameText.innerText = file.name;
        uploadText.innerText = "Uploading...";

        const formData = new FormData();
        formData.append("resume", file);

        const response = await fetch("/upload-resume", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        uploadText.innerText = data.message || "Resume Uploaded ✅";
        uploadBox.style.border = "2px solid #00ff88";
    }



    /* =========================================================
       🧠 RESUME ANALYSIS ⭐ RESPONSE KEY FIXED
       Backend sends: {analysis, audio}
       ========================================================= */

    async function analyzeResume() {
        add("📄 Resume analyze कर रहा हूँ...");
        typing();

        try {
            const response = await fetch("/analyze-resume", { method: "POST" });
            const data = await response.json();
            removeTyping();

            if (data.error) {
                add("❌ " + data.error, true);
                return;
            }

            // ❌ OLD: data.reply
            // ✅ NEW: data.analysis
            add("🤖 " + data.analysis);

            if (data.audio) {
                const audio = new Audio(data.audio);
                audio.play();
            }

        } catch (err) {
            removeTyping();
            add("⚠️ Server error, please try again", true);
        }
    }



    /* =========================================================
       🔊 MANUAL VOICE PLAYER
       ========================================================= */

    function playVoice() {
        const audio = new Audio("/static/voice.mp3");
        audio.play();
    }



    /* =========================================================
       🎤 START INTERVIEW FLOW ⭐ FULL CHAT INTEGRATION
       ========================================================= */

    async function startInterviewWithResume() {
        add("🎤 Interview शुरू कर रहा हूँ...");
        typing();

        const response = await fetch("/start_interview_resume", {
            method: "POST"
        });

        const data = await response.json();
        removeTyping();

        if (data.error) {
            add("❌ " + data.error, true);
            return;
        }

        add("🤖 " + data.question);

        if (data.audio) {
            const audio = new Audio(data.audio);
            audio.play();
        }
    }



    /* =========================================================
       🎤 VOICE INPUT (Speech → Text)
       ========================================================= */

    let recognition;

    function startSpeech() {

        if (!('webkitSpeechRecognition' in window)) {
            alert("Chrome browser use करें");
            return;
        }

        recognition = new webkitSpeechRecognition();
        recognition.lang = "hi-IN";
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.start();

        recognition.onresult = function (event) {
            const speechText = event.results[0][0].transcript;
            document.getElementById("userInput").value = speechText;
            send();
        };

        recognition.onerror = function (event) {
            console.error(event);
            alert("Mic error आया");
        };
    }



    /* =========================================================
       ⚠️ UNUSED DIRECT CALLS — COMMENTED
       ========================================================= */

    /*
    onclick = "analyzeResume()"
    playVoice();
    */



    /* =========================================================
       🌍 GLOBAL EXPORTS
       ========================================================= */

    window.uploadResume = uploadResume;
    window.analyzeResume = analyzeResume;
    window.startInterviewWithResume = startInterviewWithResume;
    window.send = send;
    window.startSpeech = startSpeech;

});