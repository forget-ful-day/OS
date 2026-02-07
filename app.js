const audioInput = document.querySelector("#audio-file");
const audioName = document.querySelector("#audio-name");
const audioDuration = document.querySelector("#audio-duration");
const stepInput = document.querySelector("#step-ms");
const maxFreqInput = document.querySelector("#max-freq");
const pinInput = document.querySelector("#buzzer-pin");
const tempoInput = document.querySelector("#tempo");
const generateButton = document.querySelector("#btn-generate");
const downloadButton = document.querySelector("#btn-download");
const uploadButton = document.querySelector("#btn-upload");
const copyButton = document.querySelector("#btn-copy");
const clearButton = document.querySelector("#btn-clear");
const codeArea = document.querySelector("#arduino-code");
const statusEl = document.querySelector("#status");

let lastSketch = "";
let lastSequence = [];

const setStatus = (message) => {
  statusEl.textContent = message;
};

const secondsToLabel = (seconds) => {
  if (!Number.isFinite(seconds)) {
    return "—";
  }
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60)
    .toString()
    .padStart(2, "0");
  return `${minutes}:${rest}`;
};

const quantizeFrequency = (value, maxFreq) => {
  const freq = Math.min(Math.max(value, 120), maxFreq);
  return Math.round(freq);
};

const analyzeAudio = async (file, stepMs, maxFreq) => {
  const arrayBuffer = await file.arrayBuffer();
  const audioCtx = new AudioContext();
  const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
  const channelData = audioBuffer.getChannelData(0);
  const sampleRate = audioBuffer.sampleRate;
  const stepSize = Math.max(1, Math.round((stepMs / 1000) * sampleRate));

  const sequence = [];

  for (let i = 0; i < channelData.length; i += stepSize) {
    let sum = 0;
    for (let j = 0; j < stepSize && i + j < channelData.length; j += 1) {
      const sample = channelData[i + j];
      sum += Math.abs(sample);
    }
    const avg = sum / stepSize;
    const mapped = 220 + avg * (maxFreq - 220) * 2.5;
    sequence.push(quantizeFrequency(mapped, maxFreq));
  }

  audioCtx.close();
  return { sequence, duration: audioBuffer.duration };
};

const buildSketch = ({ sequence, stepMs, pin, tempo }) => {
  const delays = sequence.map(() => stepMs);
  const bpmFactor = 120 / tempo;
  const normalizedDelays = delays.map((delay) => Math.round(delay * bpmFactor));

  const sequenceString = sequence.join(", ");
  const delaysString = normalizedDelays.join(", ");

  return `// Автосгенерированный скетч
// Подключите пищалку к пину ${pin} и GND

const int buzzerPin = ${pin};
const int notes[] = { ${sequenceString} };
const int durations[] = { ${delaysString} };
const int totalNotes = sizeof(notes) / sizeof(notes[0]);

void setup() {
  pinMode(buzzerPin, OUTPUT);
}

void loop() {
  for (int i = 0; i < totalNotes; i++) {
    int freq = notes[i];
    int duration = durations[i];
    if (freq > 0) {
      tone(buzzerPin, freq, duration);
    }
    delay(duration * 1.1);
  }
  delay(2000);
}
`;
};

const createFile = (content) => {
  const blob = new Blob([content], { type: "text/plain" });
  return URL.createObjectURL(blob);
};

const handleDownload = () => {
  if (!lastSketch) return;
  const url = createFile(lastSketch);
  const link = document.createElement("a");
  link.href = url;
  link.download = "melody.ino";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};

const handleCopy = async () => {
  await navigator.clipboard.writeText(codeArea.value);
  setStatus("Код скопирован в буфер обмена.");
};

const handleClear = () => {
  codeArea.value = "";
  lastSketch = "";
  lastSequence = [];
  downloadButton.disabled = true;
  uploadButton.disabled = true;
  copyButton.disabled = true;
  setStatus("Поле очищено. Ожидаю аудио файл.");
};

const handleUpload = async () => {
  if (!("serial" in navigator)) {
    setStatus("Web Serial недоступен в этом браузере.");
    return;
  }
  if (!lastSketch) {
    setStatus("Сначала сгенерируйте скетч.");
    return;
  }

  try {
    const port = await navigator.serial.requestPort();
    await port.open({ baudRate: 115200 });
    const encoder = new TextEncoder();
    const writable = port.writable.getWriter();
    await writable.write(encoder.encode(lastSketch));
    writable.releaseLock();
    await port.close();
    setStatus(
      "Код отправлен в порт. Для прошивки используйте Arduino IDE/CLI, если требуется."
    );
  } catch (error) {
    setStatus(`Ошибка при отправке: ${error.message}`);
  }
};

const updateAudioInfo = (file, duration) => {
  audioName.textContent = file ? file.name : "Файл не выбран";
  audioDuration.textContent = `Длительность: ${secondsToLabel(duration)}`;
};

const generateFromFile = async () => {
  const file = audioInput.files[0];
  if (!file) {
    setStatus("Сначала выберите аудио файл.");
    return;
  }

  setStatus("Анализирую аудио…");
  generateButton.disabled = true;

  try {
    const stepMs = Number(stepInput.value) || 120;
    const maxFreq = Number(maxFreqInput.value) || 4000;
    const pin = Number(pinInput.value) || 9;
    const tempo = Number(tempoInput.value) || 120;

    const { sequence, duration } = await analyzeAudio(file, stepMs, maxFreq);
    lastSequence = sequence;
    updateAudioInfo(file, duration);

    lastSketch = buildSketch({ sequence, stepMs, pin, tempo });
    codeArea.value = lastSketch;
    downloadButton.disabled = false;
    uploadButton.disabled = false;
    copyButton.disabled = false;
    setStatus(`Готово! Сгенерировано ${sequence.length} нот.`);
  } catch (error) {
    setStatus(`Ошибка анализа: ${error.message}`);
  } finally {
    generateButton.disabled = false;
  }
};

audioInput.addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) {
    updateAudioInfo(null, null);
    return;
  }
  updateAudioInfo(file, null);
  setStatus("Файл выбран. Нажмите «Сгенерировать код»." );
});

generateButton.addEventListener("click", generateFromFile);

downloadButton.addEventListener("click", handleDownload);
copyButton.addEventListener("click", handleCopy);
clearButton.addEventListener("click", handleClear);
uploadButton.addEventListener("click", handleUpload);

codeArea.value = "";
setStatus("Ожидаю аудио файл.");
