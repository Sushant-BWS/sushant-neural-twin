"use strict";

/* =========================================================
   CONFIGURATION
========================================================= */

const API_BASE_URL =
  document.documentElement.dataset.apiBaseUrl ||
  (window.location.port === "8765"
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : window.location.origin);

const CHAT_API_URL =
  `${API_BASE_URL}/api/chat/chat`;

const VOICE_STATUS_URL =
  `${API_BASE_URL}/api/chat/voice-status`;

const AUDIO_URL =
  `${API_BASE_URL}/api/chat/audio`;

const HEALTH_URL =
  `${API_BASE_URL}/health`;

const VOICE_MAX_WAIT_MS = Math.max(
  60000,
  Number(
    document.documentElement.dataset.voiceMaxWaitMs ||
    900000
  )
);

const VOICE_POLL_INTERVAL_MS = 8000;

const VOICE_POLL_MAX_INTERVAL_MS = 30000;


/* =========================================================
   VIEW TITLES
========================================================= */

const titles = {
  chat: "Ask the twin",
  profile: "Profile",
  projects: "Projects",
  graph: "Knowledge graph",
  thoughts: "Thought profile",
  recruiter: "Recruiter mode",
};


/* =========================================================
   DOM ELEMENTS
========================================================= */

const navItems =
  document.querySelectorAll(".nav-item");

const views =
  document.querySelectorAll(".view");

const viewTitle =
  document.querySelector("#view-title");

const messageList =
  document.querySelector("#message-list");

const chatForm =
  document.querySelector("#chat-form");

const chatInput =
  document.querySelector("#chat-input");

const clearSession =
  document.querySelector("#clear-session");

const evidenceCount =
  document.querySelector(".count-badge");

const confidenceText =
  document.querySelector(
    ".confidence-meter strong"
  );

const confidenceBar =
  document.querySelector(
    ".meter-track span"
  );

const confidenceMessage =
  document.querySelector(
    ".confidence-panel .muted"
  );

const quietBadge =
  document.querySelector(
    ".chat-panel .quiet-badge"
  );

const systemStateText =
  document.querySelector(
    ".system-state span:last-child"
  );

const systemStateDot =
  document.querySelector(
    ".system-state .status-dot"
  );

const microphoneButton =
  document.querySelector(
    "#voice-button"
  );


/* =========================================================
   APPLICATION STATE
========================================================= */

let recognition = null;

let isListening = false;

let currentAudio = null;

let currentVoiceJobId = null;

let activeVoiceJobId = null;

let activeAudio = null;

let activeVoiceMessage = null;

let voiceEnabled = true;

const conversationHistory = [];


/* =========================================================
   BASIC ERROR HANDLER
========================================================= */

window.addEventListener(
  "error",
  function (event) {

    console.error(
      "Frontend error:",
      event.error || event.message
    );

  }
);


window.addEventListener(
  "unhandledrejection",
  function (event) {

    console.error(
      "Unhandled promise rejection:",
      event.reason
    );

  }
);


/* =========================================================
   VIEW NAVIGATION
========================================================= */

function selectView(viewName) {

  navItems.forEach(
    function (item) {

      item.classList.toggle(
        "active",
        item.dataset.view === viewName
      );

    }
  );


  views.forEach(
    function (view) {

      view.classList.toggle(
        "active",
        view.dataset.panel === viewName
      );

    }
  );


  if (viewTitle) {

    viewTitle.textContent =
      titles[viewName] ||
      "Ask the twin";

  }

}


navItems.forEach(
  function (item) {

    item.addEventListener(
      "click",
      function () {

        selectView(
          item.dataset.view
        );

      }
    );

  }
);


/* =========================================================
   ADD CHAT MESSAGE
========================================================= */

function addMessage(
  role,
  text,
  response = null
) {

  const message =
    document.createElement("div");


  if (role === "user") {

    message.className =
      "chat-message user-message";

  } else {

    message.className =
      "chat-message assistant-message";

  }


  const content =
    document.createElement("div");


  content.className =
    "message-content";


  content.textContent =
    text;


  message.appendChild(
    content
  );


  const messageState = {
    role,
    content: text,
    safe: response?.safe ?? null,
    reasoningSummary: response?.reasoning_summary || "",
    evidenceCount: Number(response?.evidence_count || 0),
    verifications: Array.isArray(response?.verifications)
      ? response.verifications
      : [],
    voiceJobId: response?.voice_job_id || null,
    voiceStatus: response?.voice_status || "unavailable",
    audioFile: response?.audio_file || null,
    audio: null,
    element: message,
  };


  conversationHistory.push(messageState);


  if (role === "assistant") {

    if (response) {
      const metadata = document.createElement("div");
      metadata.className = "answer-metadata";

      const safety = document.createElement("span");
      safety.className = response.safe
        ? "answer-safety is-safe"
        : "answer-safety is-uncertain";
      safety.textContent = response.safe
        ? "Verified answer"
        : "Needs verification";

      const evidence = document.createElement("span");
      evidence.textContent =
        `${messageState.evidenceCount} evidence source${
          messageState.evidenceCount === 1 ? "" : "s"
        }`;

      metadata.append(safety, evidence);
      message.appendChild(metadata);

      if (messageState.reasoningSummary) {
        const summary = document.createElement("p");
        summary.className = "reasoning-summary";
        summary.textContent = messageState.reasoningSummary;
        message.appendChild(summary);
      }
    }

    const controls =
      document.createElement("div");

    controls.className =
      "voice-controls";

    const status =
      document.createElement("span");

    status.className =
      "voice-status";

    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.textContent = response?.voice_job_id
      ? "Voice queued"
      : "Voice unavailable";

    const playButton =
      document.createElement("button");

    playButton.type = "button";
    playButton.className = "voice-play-button";
    playButton.textContent = "Play Voice";
    playButton.hidden = true;

    playButton.addEventListener(
      "click",
      function () {
        playMessageVoice(messageState);
      }
    );

    const stopButton =
      document.createElement("button");

    stopButton.type = "button";
    stopButton.className = "voice-stop-button";
    stopButton.textContent = "Stop";
    stopButton.setAttribute("aria-label", "Stop voice playback");
    stopButton.hidden = true;
    stopButton.addEventListener("click", function () {
      stopMessageVoice(messageState);
    });

    const playbackMessage =
      document.createElement("span");

    playbackMessage.className =
      "voice-playback-message";

    playbackMessage.setAttribute("role", "status");
    playbackMessage.setAttribute("aria-live", "polite");

    controls.append(status, playButton, stopButton, playbackMessage);
    message.appendChild(controls);
    message.voiceMessage = messageState;
    messageState.statusElement = status;
    messageState.playButton = playButton;
    messageState.stopButton = stopButton;
    messageState.playbackMessage = playbackMessage;

  }


  messageList.appendChild(
    message
  );


  messageList.scrollTop =
    messageList.scrollHeight;


  return message;
}


/* =========================================================
   LOADING MESSAGE
========================================================= */

function addLoadingMessage() {

  const loading =
    document.createElement("div");


  loading.className =
    "chat-message assistant-message loading-message";


  loading.innerHTML = `
    <div class="loading-dots">
      <span></span>
      <span></span>
      <span></span>
    </div>

    <span>
      Neural Twin is thinking...
    </span>
  `;


  messageList.appendChild(
    loading
  );


  messageList.scrollTop =
    messageList.scrollHeight;


  return loading;
}


/* =========================================================
   UPDATE EVIDENCE PANEL
========================================================= */

function updateEvidence(
  result
) {

  const count =
    Number(
      result.evidence_count || 0
    );


  if (evidenceCount) {

    evidenceCount.textContent =
      String(count);

  }


  if (
    result.safe &&
    count > 0
  ) {

    if (quietBadge) {

      quietBadge.textContent =
        result.voice_job_id
          ? "Voice preparing..."
          : "Evidence retrieved";

    }

  } else if (!result.safe) {

    if (quietBadge) {

      quietBadge.textContent =
        "Needs verification";

    }

  } else {

    if (quietBadge) {

      quietBadge.textContent =
        "No evidence";

    }

  }


  if (
    result.safe &&
    count > 0
  ) {

    if (confidenceText) {

      confidenceText.textContent =
        "Grounded";

    }


    if (confidenceBar) {

      confidenceBar.style.width =
        "100%";

    }


    if (confidenceMessage) {

      confidenceMessage.textContent =
        `${count} evidence item${
          count === 1
            ? ""
            : "s"
        } retrieved.`;

    }

  } else {

    if (confidenceText) {

      confidenceText.textContent =
        "--";

    }


    if (confidenceBar) {

      confidenceBar.style.width =
        "0%";

    }


    if (confidenceMessage) {

      confidenceMessage.textContent =
        "No verified evidence available.";

    }

  }


  updateEvidenceDetails(
    result
  );
}


/* =========================================================
   EVIDENCE DETAILS
========================================================= */

function updateEvidenceDetails(
  result
) {

  const evidencePanel =
    document.querySelector(
      ".evidence-panel"
    );


  if (!evidencePanel) {

    return;

  }


  const oldItems =
    evidencePanel.querySelector(
      ".evidence-items"
    );


  if (oldItems) {

    oldItems.remove();

  }


  const emptyState =
    evidencePanel.querySelector(
      ".empty-state"
    );

  const verifications =
    Array.isArray(
      result.verifications
    )
      ? result.verifications
      : [];

  const evidenceBySource = new Map();

  verifications.forEach(function (verification) {
    const status = String(verification.status || "UNKNOWN").toUpperCase();
    const evidence = Array.isArray(verification.evidence)
      ? verification.evidence
      : [];

    evidence.forEach(function (item) {
      const source = String(item.source || "").replace(/\\/g, "/");
      if (!source) {
        return;
      }

      const sourceKey = source.toLowerCase();
      let sourceEvidence = evidenceBySource.get(sourceKey);

      if (!sourceEvidence) {
        sourceEvidence = {
          source,
          statuses: new Set(),
          title: String(item.title || ""),
          summary: String(item.summary || ""),
        };
        evidenceBySource.set(sourceKey, sourceEvidence);
      }

      sourceEvidence.statuses.add(status);
    });
  });

  if (emptyState) {
    emptyState.hidden = evidenceBySource.size > 0;
  }

  if (evidenceBySource.size === 0) {
    return;
  }

  const container =
    document.createElement(
      "div"
    );


  container.className =
    "evidence-items";

  const intentMatch = String(result.reasoning_summary || "").match(
    /for\s+([a-z]+)\s+intent/i
  );
  const intent = intentMatch ? intentMatch[1].toLowerCase() : "profile";

  evidenceBySource.forEach(function (evidence) {
    const filename = evidence.source.split("/").pop();
    const fallback = summarizeEvidenceSource(filename, intent);
    const details = {
      title: evidence.title || fallback.title,
      summary: evidence.summary || fallback.summary,
    };
    const item = document.createElement("article");
    item.className = "evidence-item";

    const title = document.createElement("strong");
    title.textContent = details.title;

    const status = document.createElement("span");
    status.className = "evidence-status";
    status.textContent = evidence.statuses.has("VERIFIED")
      ? "Verified"
      : evidence.statuses.has("SUPPORTED")
        ? "Supported"
        : "Documented";

    const summary = document.createElement("span");
    summary.className = "evidence-summary";
    summary.textContent = details.summary;

    const source = document.createElement("small");
    source.textContent = `Source: ${filename}`;

    item.append(title, status, summary, source);
    container.appendChild(item);
  });


  evidencePanel.appendChild(
    container
  );
}


function summarizeEvidenceSource(
  filename,
  intent
) {

  if (filename.toLowerCase() === "education.json") {
    return {
      title: "Education record",
      summary: "Degree, institution, and study period",
    };
  }

  if (filename.toLowerCase() === "sushant_resume.pdf") {
    const summaries = {
      education: "Education and academic achievements",
      project: "Documented project details",
      skill: "Documented technical skills",
      experience: "Documented work experience",
      certification: "Documented certifications",
      profile: "Documented profile details",
    };

    return {
      title: "Resume",
      summary: summaries[intent] || "Supporting resume details",
    };
  }

  const titleByIntent = {
    project: "Project record",
    skill: "Skills record",
    experience: "Experience record",
    certification: "Certification record",
    education: "Education record",
    thought: "Thought record",
    profile: "Profile record",
  };

  return {
    title: titleByIntent[intent] || "Documented record",
    summary: "Source-backed supporting details",
  };
}


/* =========================================================
   CHECK BACKEND
========================================================= */

async function checkBackend() {

  try {

    const response =
      await fetch(
        HEALTH_URL,
        {
          method: "GET",
          cache: "no-store"
        }
      );

    setBackendState(response.ok);
    return response.ok;

  } catch (error) {

    console.warn(
      "Backend health check failed:",
      error
    );

    setBackendState(false);
    return false;
  }
}


function setBackendState(online) {

  if (systemStateText) {
    systemStateText.textContent = online
      ? "Neural Twin online"
      : "Neural Twin offline";
  }

  if (systemStateDot) {
    systemStateDot.classList.toggle("offline", !online);
  }
}


/* =========================================================
   CHAT API
========================================================= */

async function askNeuralTwin(
  question
) {

  const response =
    await fetch(
      CHAT_API_URL,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",

          "Accept":
            "application/json"
        },

        body: JSON.stringify({
          message: question
        })
      }
    );


  let data = null;


  try {

    data =
      await response.json();

  } catch (error) {

    throw new Error(
      `Backend returned invalid JSON. HTTP ${response.status}`
    );

  }


  if (!response.ok) {

    const detail =
      data &&
      data.detail
        ? data.detail
        : "Neural Twin backend returned an error.";


    const error = new Error(
      typeof detail === "string"
        ? detail
        : JSON.stringify(detail)
    );

    error.status = response.status;
    const retryAfterSeconds = Number(
      response.headers.get("Retry-After")
    );
    if (Number.isFinite(retryAfterSeconds) && retryAfterSeconds > 0) {
      error.retryAfterMs = retryAfterSeconds * 1000;
    }

    throw error;

  }


  return data;
}


/* =========================================================
   GET VOICE STATUS
========================================================= */

async function getVoiceStatus(
  jobId
) {

  const response =
    await fetch(
      `${VOICE_STATUS_URL}/${encodeURIComponent(
        jobId
      )}`,
      {
        method: "GET",

        headers: {
          "Accept":
            "application/json"
        },

        cache: "no-store"
      }
    );


  let data = null;


  try {

    data =
      await response.json();

  } catch (error) {

    throw new Error(
      "Invalid voice status response."
    );

  }


  if (!response.ok) {

    const detail =
      data &&
      data.detail
        ? data.detail
        : "Voice status request failed.";


    throw new Error(
      typeof detail === "string"
        ? detail
        : JSON.stringify(detail)
    );

  }


  return data;
}


/* =========================================================
   STOP CURRENT AUDIO
========================================================= */

function stopCurrentAudio() {

  if (!currentAudio) {

    return;

  }


  try {

    currentAudio.pause();

    currentAudio.currentTime =
      0;

    currentAudio.src = "";

  } catch (error) {

    console.warn(
      "Could not stop current audio:",
      error
    );

  }


  currentAudio =
    null;
}


/* =========================================================
   PLAY GENERATED VOICE
========================================================= */

async function playGeneratedVoice(
  audioFile
) {

  if (!audioFile) {

    return false;

  }


  const audioUrl =
    `${AUDIO_URL}/${encodeURIComponent(
      audioFile
    )}`;


  console.log(
    "Audio URL:",
    audioUrl
  );


  stopCurrentAudio();


  currentAudio =
    new Audio();


  currentAudio.preload =
    "auto";


  currentAudio.src =
    audioUrl;


  currentAudio.addEventListener(
    "loadeddata",
    function () {

      console.log(
        "Voice audio loaded."
      );

    }
  );


  currentAudio.addEventListener(
    "play",
    function () {

      if (quietBadge) {

        quietBadge.textContent =
          "Speaking...";

      }

    }
  );


  currentAudio.addEventListener(
    "ended",
    function () {

      if (quietBadge) {

        quietBadge.textContent =
          "Voice finished";

      }

    }
  );


  currentAudio.addEventListener(
    "error",
    function (event) {

      console.error(
        "Audio element error:",
        event
      );


      if (quietBadge) {

        quietBadge.textContent =
          "Voice playback error";

      }

    }
  );


  try {

    await currentAudio.play();


    console.log(
      "Sushant cloned voice started."
    );


    return true;

  } catch (error) {

    console.warn(
      "Automatic playback blocked:",
      error
    );


    showManualVoiceButton(
      audioUrl
    );


    return false;
  }
}


/* =========================================================
   MANUAL VOICE BUTTON
========================================================= */

function showManualVoiceButton(
  audioUrl
) {

  const oldButton =
    document.querySelector(
      "#manual-voice-button"
    );


  if (oldButton) {

    oldButton.remove();

  }


  const button =
    document.createElement(
      "button"
    );


  button.id =
    "manual-voice-button";


  button.type =
    "button";


  button.className =
    "voice-play-button";


  button.textContent =
    "🔊 Play Voice";


  button.addEventListener(
    "click",
    async function () {

      try {

        stopCurrentAudio();


        currentAudio =
          new Audio(
            audioUrl
          );


        currentAudio.preload =
          "auto";


        await currentAudio.play();


        button.remove();


        if (quietBadge) {

          quietBadge.textContent =
            "Speaking...";

        }


        currentAudio.addEventListener(
          "ended",
          function () {

            if (quietBadge) {

              quietBadge.textContent =
                "Voice finished";

            }

          }
        );


      } catch (error) {

        console.error(
          "Manual voice playback failed:",
          error
        );


        if (quietBadge) {

          quietBadge.textContent =
            "Voice playback error";

        }

      }

    }
  );


  const composer =
    document.querySelector(
      ".chat-composer"
    );


  if (composer) {

    composer.appendChild(
      button
    );

  }
}


/* =========================================================
   WAIT FOR VOICE JOB
========================================================= */

async function waitForVoice(
  jobId
) {

  if (!jobId) {

    console.warn(
      "No voice job ID."
    );

    return;

  }


  currentVoiceJobId =
    jobId;


  console.log(
    "Voice job started:",
    jobId
  );


  if (quietBadge) {

    quietBadge.textContent =
      "Preparing voice...";

  }


  /*
   * Chatterbox CPU generation can take several minutes.
   *
   * 600 attempts x 1 second =
   * maximum 10 minutes.
   */

  const maxAttempts =
    600;


  for (
    let attempt = 0;
    attempt < maxAttempts;
    attempt++
  ) {

    /*
     * Stop polling when another
     * question has started.
     */

    if (
      currentVoiceJobId !== jobId
    ) {

      console.log(
        "Old voice job cancelled."
      );

      return;

    }


    try {

      const status =
        await getVoiceStatus(
          jobId
        );


      console.log(
        "Voice status:",
        status
      );


      /* ---------------------------------------------
         READY
      --------------------------------------------- */

      if (
        status.status === "ready" &&
        status.audio_file
      ) {

        if (quietBadge) {

          quietBadge.textContent =
            "Voice ready";

        }


        await playGeneratedVoice(
          status.audio_file
        );


        return;
      }


      /* ---------------------------------------------
         ERROR
      --------------------------------------------- */

      if (
        status.status === "error"
      ) {

        console.error(
          "Voice generation failed:",
          status.voice_error
        );


        if (quietBadge) {

          quietBadge.textContent =
            "Voice unavailable";

        }


        /*
         * Do not hide the text answer.
         * Voice failure should never break chat.
         */

        return;
      }


      /* ---------------------------------------------
         QUEUED
      --------------------------------------------- */

      if (
        status.status === "queued"
      ) {

        if (quietBadge) {

          quietBadge.textContent =
            "Voice queued...";

        }

      }


      /* ---------------------------------------------
         PROCESSING
      --------------------------------------------- */

      if (
        status.status === "processing"
      ) {

        if (quietBadge) {

          const elapsed =
            Math.floor(
              attempt / 60
            );

          if (elapsed > 0) {

            quietBadge.textContent =
              `Generating voice... ${elapsed}m`;

          } else {

            quietBadge.textContent =
              "Generating voice...";

          }

        }

      }


    } catch (error) {

      console.error(
        "Voice polling error:",
        error
      );


      /*
       * A temporary polling error should not
       * immediately kill the voice job.
       *
       * Continue polling unless this is
       * the final attempt.
       */

      if (
        attempt >= maxAttempts - 1
      ) {

        if (quietBadge) {

          quietBadge.textContent =
            "Voice status error";

        }

        return;
      }

    }


    /*
     * Poll every second.
     */

    await new Promise(
      function (resolve) {

        setTimeout(
          resolve,
          1000
        );

      }
    );

  }


  console.warn(
    "Voice generation timed out after 10 minutes."
  );


  if (quietBadge) {

    quietBadge.textContent =
      "Voice timeout";

  }
}


function setVoiceMessageStatus(
  message,
  status,
  detail = ""
) {

  message.voiceStatus = status;

  if (!message.element.isConnected) {
    return;
  }

  const labels = {
    queued: "Voice queued",
    preparing: "Preparing voice...",
    processing: "Generating voice...",
    ready: "Voice ready",
    unavailable: "Voice unavailable",
    error: "Voice generation failed",
  };

  message.statusElement.textContent =
    labels[status] || labels.preparing;

  message.statusElement.dataset.status = status;
  message.playButton.hidden = status !== "ready";
  message.playButton.disabled = status !== "ready";
  message.playbackMessage.textContent = detail;

  if (
    status === "error" &&
    /unavailable|not running|connection refused/i.test(detail)
  ) {
    message.statusElement.textContent =
      "Voice unavailable";
  }

  if (
    message.voiceJobId &&
    message.voiceJobId === activeVoiceJobId &&
    quietBadge
  ) {
    quietBadge.textContent =
      message.statusElement.textContent;
  }
}


function stopActiveAudio() {

  if (activeAudio) {
    try {
      activeAudio.pause();
      activeAudio.currentTime = 0;
      activeAudio.removeAttribute("src");
      activeAudio.load();
    } catch (error) {
      console.warn("Could not release active audio:", error);
    }
  }

  if (activeVoiceMessage) {
    activeVoiceMessage.audio = null;
    activeVoiceMessage.playButton.textContent = "Play Voice";
    activeVoiceMessage.playButton.setAttribute("aria-pressed", "false");
    activeVoiceMessage.stopButton.hidden = true;
  }

  activeAudio = null;
  activeVoiceMessage = null;
}


function stopMessageVoice(message) {

  if (activeVoiceMessage === message) {
    stopActiveAudio();
  } else if (message.audio) {
    message.audio.pause();
    message.audio.currentTime = 0;
    message.audio.removeAttribute("src");
    message.audio.load();
    message.audio = null;
  }

  message.playButton.textContent = "Play Voice";
  message.playButton.setAttribute("aria-pressed", "false");
  message.stopButton.hidden = true;
  message.playbackMessage.textContent = "";
}


async function playMessageVoice(message) {

  if (!message.audioFile) {
    return;
  }

  if (
    message.audio &&
    activeAudio === message.audio
  ) {
    if (activeAudio.paused) {
      try {
        await activeAudio.play();
        message.playButton.textContent = "Pause Voice";
        message.playButton.setAttribute("aria-pressed", "true");
        message.playbackMessage.textContent = "";
      } catch (error) {
        message.playbackMessage.textContent =
          "Playback was blocked. Press Play Voice to try again.";
      }
    } else {
      activeAudio.pause();
      message.playButton.textContent = "Play Voice";
      message.playButton.setAttribute("aria-pressed", "false");
    }
    return;
  }

  stopActiveAudio();

  const audioUrl =
    `${AUDIO_URL}/${encodeURIComponent(message.audioFile)}`;

  const audio = new Audio(audioUrl);
  audio.preload = "auto";
  message.audio = audio;
  activeAudio = audio;
  activeVoiceMessage = message;
  activeVoiceJobId = message.voiceJobId;

  audio.addEventListener("ended", function () {
    if (activeAudio !== audio) {
      return;
    }
    message.playButton.textContent = "Play Voice";
    message.playButton.setAttribute("aria-pressed", "false");
    message.stopButton.hidden = true;
    activeAudio = null;
    activeVoiceMessage = null;
  });

  audio.addEventListener("error", function () {
    if (message.audio !== audio) {
      return;
    }
    message.playbackMessage.textContent =
      "This audio could not be played. Try again.";
    message.playButton.textContent = "Play Voice";
    message.playButton.setAttribute("aria-pressed", "false");
    message.stopButton.hidden = true;
    activeAudio = null;
    activeVoiceMessage = null;
  });

  try {
    await audio.play();
    message.playButton.textContent = "Pause Voice";
    message.playButton.setAttribute("aria-pressed", "true");
    message.stopButton.hidden = false;
    message.playbackMessage.textContent = "";
  } catch (error) {
    message.playbackMessage.textContent =
      "Voice ready. Click Play Voice to listen.";
    activeAudio = null;
    activeVoiceMessage = null;
    message.stopButton.hidden = true;
  }
}


async function startVoicePolling(
  jobId,
  message
) {

  if (!jobId || !message) {
    return;
  }

  message.voiceJobId = jobId;
  activeVoiceJobId = jobId;
  const startedAt = Date.now();
  let consecutiveFailures = 0;
  let nextPollIntervalMs = VOICE_POLL_INTERVAL_MS;
  setVoiceMessageStatus(message, "queued");

  while (
    Date.now() - startedAt < VOICE_MAX_WAIT_MS &&
    message.element.isConnected
  ) {
    try {
      const status = await getVoiceStatus(jobId);
      consecutiveFailures = 0;
      nextPollIntervalMs = VOICE_POLL_INTERVAL_MS;
      const returnedJobId = status.voice_job_id || status.job_id;

      if (returnedJobId && returnedJobId !== jobId) {
        throw new Error("Voice status returned a different job ID.");
      }

      if (status.status === "ready" && status.audio_file) {
        message.audioFile = status.audio_file;
        setVoiceMessageStatus(message, "ready");
        console.debug("Voice job timings", {
          jobId,
          elapsedMs: Date.now() - startedAt,
        });

        if (message.voiceJobId === activeVoiceJobId) {
          await playMessageVoice(message);
        }

        return;
      }

      if (status.status === "error") {
        setVoiceMessageStatus(
          message,
          "error",
          status.voice_error || "Voice generation failed."
        );
        return;
      }

      setVoiceMessageStatus(
        message,
        status.status === "queued" ? "queued" :
          status.status === "processing" ? "processing" : "preparing"
      );

    } catch (error) {
      consecutiveFailures += 1;
      nextPollIntervalMs = error.retryAfterMs || Math.min(
        VOICE_POLL_MAX_INTERVAL_MS,
        VOICE_POLL_INTERVAL_MS * 2 ** Math.min(consecutiveFailures, 3)
      );

      if (error.status === 429) {
        console.debug("Voice status rate limited; backing off.");
      } else {
        console.warn("Voice status polling failed; will retry:", error);
      }
      setVoiceMessageStatus(message, "preparing");
    }

    await new Promise(function (resolve) {
      setTimeout(resolve, nextPollIntervalMs);
    });
  }

  if (message.element.isConnected) {
    setVoiceMessageStatus(
      message,
      "error",
      `Voice generation timed out after ${Math.round(VOICE_MAX_WAIT_MS / 60000)} minutes.`
    );
  }
}


/* =========================================================
   CHAT FORM SUBMIT
========================================================= */

if (chatForm) {

  chatForm.addEventListener(
    "submit",
    async function (event) {

      /*
       * Prevent page refresh.
       */

      event.preventDefault();

      event.stopPropagation();


      console.log(
        "Chat form submitted without page refresh."
      );


      const message =
        chatInput.value.trim();


      if (!message) {

        return;

      }


      /*
       * Stop currently playing audio.
       */

      stopActiveAudio();
      activeVoiceJobId = null;
      currentVoiceJobId = null;


      /*
       * Show user message.
       */

      addMessage(
        "user",
        message
      );


      /*
       * Clear input.
       */

      chatInput.value =
        "";


      /*
       * Disable input.
       */

      chatInput.disabled =
        true;


      const sendButton =
        chatForm.querySelector(
          ".primary-button"
        );


      if (sendButton) {

        sendButton.disabled =
          true;


        sendButton.dataset.originalText =
          sendButton.innerHTML;


        sendButton.innerHTML =
          "Thinking...";

      }


      /*
       * Loading message.
       */

      const loadingMessage =
        addLoadingMessage();


      try {

        /*
         * Ask Neural Twin.
         */

        const result =
          await askNeuralTwin(
            message
          );


        /*
         * Remove loading.
         */

        loadingMessage.remove();


        /*
         * Show answer immediately.
         */

        const assistantElement = addMessage(
          "assistant",
          result.answer,
          result
        );


        /*
         * Update evidence.
         */

        updateEvidence(
          result
        );


        /*
         * Start voice generation.
         *
         * IMPORTANT:
         * We DO NOT await this.
         *
         * The text answer remains instant.
         */

        if (
          voiceEnabled &&
          result.voice_job_id
        ) {

          startVoicePolling(
            result.voice_job_id,
            assistantElement.voiceMessage
          );

        } else {

          console.warn(
            "No voice_job_id returned by backend.",
            result
          );


          setVoiceMessageStatus(
            assistantElement.voiceMessage,
            "unavailable",
            result.voice_error ||
              "No voice job was created for this answer."
          );

        }


      } catch (error) {

        /*
         * Remove loading.
         */

        loadingMessage.remove();


        console.error(
          "Neural Twin request failed:",
          error
        );


        addMessage(
          "assistant",
          error instanceof TypeError
            ? "Neural Twin backend is unavailable. Please check whether the backend is running."
            : "Neural Twin could not complete this request. Please try again."
        );

        setBackendState(error instanceof TypeError ? false : true);


        if (quietBadge) {

          quietBadge.textContent =
            "Backend unavailable";

        }

      } finally {

        /*
         * Re-enable input.
         */

        chatInput.disabled =
          false;


        if (sendButton) {

          sendButton.disabled =
            false;


          sendButton.innerHTML =
            sendButton.dataset.originalText ||
            'Send <span aria-hidden="true">&#8594;</span>';

        }


        chatInput.focus();

      }

    }
  );

}


/* =========================================================
   KEYBOARD SUPPORT
========================================================= */

if (chatInput) {

  chatInput.addEventListener(
    "keydown",
    function (event) {

      /*
       * Enter = send
       * Shift + Enter = new line
       */

      if (
        event.key === "Enter" &&
        !event.shiftKey
      ) {

        event.preventDefault();

        event.stopPropagation();

        chatForm.requestSubmit();

      }

    }
  );

}


/* =========================================================
   CLEAR SESSION
========================================================= */

if (clearSession) {

  clearSession.addEventListener(
    "click",
    function (event) {

      event.preventDefault();


      /*
       * Stop audio.
       */

      stopActiveAudio();
      activeVoiceJobId = null;
      currentVoiceJobId = null;


      /*
       * Reset messages.
       */

      messageList.innerHTML = `
        <div class="welcome-message">

          <div class="welcome-mark">
            SN
          </div>

          <div>

            <h3>
              Ready when the evidence is.
            </h3>

            <p>
              Ask the assistant about Sushant's
              documented profile, skills, projects,
              experience, education, or thoughts.
            </p>

          </div>

        </div>
      `;

      conversationHistory.length = 0;


      /*
       * Reset evidence.
       */

      if (evidenceCount) {

        evidenceCount.textContent =
          "0";

      }


      if (confidenceText) {

        confidenceText.textContent =
          "--";

      }


      if (confidenceBar) {

        confidenceBar.style.width =
          "0%";

      }


      if (confidenceMessage) {

        confidenceMessage.textContent =
          "No estimate until evidence is retrieved.";

      }


      if (quietBadge) {

        quietBadge.textContent =
          "Ready";

      }


      /*
       * Remove evidence details.
       */

      const evidenceItems =
        document.querySelector(
          ".evidence-items"
        );


      if (evidenceItems) {

        evidenceItems.remove();

      }

      const evidenceEmptyState =
        document.querySelector(
          ".evidence-panel .empty-state"
        );

      if (evidenceEmptyState) {
        evidenceEmptyState.hidden = false;
      }


      /*
       * Stop microphone.
       */

      stopListening();


      if (chatInput) {

        chatInput.focus();

      }

    }
  );

}


/* =========================================================
   VOICE INPUT
========================================================= */

const SpeechRecognition =
  window.SpeechRecognition ||
  window.webkitSpeechRecognition;


function setupVoiceRecognition() {

  if (!microphoneButton) {

    console.warn(
      "Microphone button not found."
    );

    return;

  }


  if (!SpeechRecognition) {

    microphoneButton.disabled =
      true;


    microphoneButton.title =
      "Speech recognition is not supported in this browser.";


    return;

  }


  recognition =
    new SpeechRecognition();


  recognition.lang =
    "en-IN";


  recognition.continuous =
    false;


  recognition.interimResults =
    true;


  recognition.maxAlternatives =
    1;


  /*
   * START
   */

  recognition.onstart =
    function () {

      isListening =
        true;


      microphoneButton.classList.add(
        "listening"
      );


      microphoneButton.textContent =
        "●";


      microphoneButton.title =
        "Listening...";

    };


  /*
   * RESULT
   */

  recognition.onresult =
    function (event) {

      let transcript =
        "";


      for (
        let i = event.resultIndex;
        i < event.results.length;
        i++
      ) {

        transcript +=
          event.results[i][0]
            .transcript;

      }


      chatInput.value =
        transcript.trim();

    };


  /*
   * ERROR
   */

  recognition.onerror =
    function (event) {

      console.error(
        "Speech recognition error:",
        event.error
      );


      stopListening();

    };


  /*
   * END
   */

  recognition.onend =
    function () {

      stopListening();

    };


  /*
   * BUTTON
   */

  microphoneButton.addEventListener(
    "click",
    function (event) {

      event.preventDefault();


      if (isListening) {

        recognition.stop();

        return;

      }


      try {

        recognition.start();

      } catch (error) {

        console.error(
          "Could not start speech recognition:",
          error
        );

      }

    }
  );

}


/* =========================================================
   STOP LISTENING
========================================================= */

function stopListening() {

  isListening =
    false;


  if (!microphoneButton) {

    return;

  }


  microphoneButton.classList.remove(
    "listening"
  );


  microphoneButton.textContent =
    "🎤";


  microphoneButton.title =
    "Speak your question";
}


/* =========================================================
   INITIALIZE
========================================================= */

console.log(
  "Sushant Neural Twin frontend loaded."
);


console.log(
  "Backend:",
  API_BASE_URL
);


console.log(
  "Voice enabled:",
  voiceEnabled
);


console.log(
  "Voice status endpoint:",
  VOICE_STATUS_URL
);


console.log(
  "Audio endpoint:",
  AUDIO_URL
);


setupVoiceRecognition();


if (chatInput) {

  chatInput.focus();

}


/*
 * Check backend once when frontend starts.
 */

checkBackend()
  .then(
    function (online) {

      if (online) {

        console.log(
          "Neural Twin backend: ONLINE"
        );

      } else {

        console.warn(
          "Neural Twin backend: OFFLINE"
        );

      }

    }
  );