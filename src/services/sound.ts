/**
 * Arena Goal Horn & Cannon Blast Sound Synthesizer (Web Audio API).
 *
 * Faithfully reproduces the Nationwide Arena goal horn (~138 Hz fundamental with
 * measured harmonic spectral distribution) followed by the thunderous boom of the
 * replica Civil War cannon with low-frequency reverb.
 */

let audioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    audioCtx = new AudioContextClass();
  }
  if (audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx;
}

const HORN_F0 = 138.0;
const HORN_HARMONICS = [
  1.0, 0.46, 0.45, 0.22, 0.06, 0.05, 0.54, 0.38, 0.14, 0.08,
  0.26, 0.01, 0.17, 0.37, 0.1, 0.13, 0.17, 0.12, 0.0, 0.07,
];

export function playGoalHorn(volumePercent: number = 80): void {
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;
    const masterGain = ctx.createGain();
    const vol = Math.max(0, Math.min(1, volumePercent / 100));
    masterGain.gain.setValueAtTime(vol * 0.85, now);
    masterGain.connect(ctx.destination);

    // 1. Synthesize the Horn Blast (~3.0 seconds)
    const hornGain = ctx.createGain();
    hornGain.gain.setValueAtTime(0.001, now);
    hornGain.gain.exponentialRampToValueAtTime(0.6, now + 0.08); // punchy attack
    hornGain.gain.setValueAtTime(0.6, now + 2.8);
    hornGain.gain.exponentialRampToValueAtTime(0.001, now + 3.2); // smooth release
    hornGain.connect(masterGain);

    HORN_HARMONICS.forEach((amp, idx) => {
      if (amp <= 0.005) return;
      const osc = ctx.createOscillator();
      const harmGain = ctx.createGain();
      const freq = HORN_F0 * (idx + 1);

      // Slight natural chorus/detuning
      const detune = (idx % 2 === 0 ? 1 : -1) * (idx * 0.8);
      osc.type = idx % 3 === 0 ? "sawtooth" : "triangle";
      osc.frequency.setValueAtTime(freq + detune, now);

      harmGain.gain.setValueAtTime(amp * 0.15, now);
      osc.connect(harmGain);
      harmGain.connect(hornGain);

      osc.start(now);
      osc.stop(now + 3.3);
    });

    // 2. Synthesize The Cannon Blast (fires at t = 3.1s)
    const cannonTime = now + 3.0;

    // Sub-bass thump (sine drop 90Hz -> 30Hz)
    const thumpOsc = ctx.createOscillator();
    const thumpGain = ctx.createGain();
    thumpOsc.type = "sine";
    thumpOsc.frequency.setValueAtTime(95, cannonTime);
    thumpOsc.frequency.exponentialRampToValueAtTime(25, cannonTime + 0.6);
    thumpGain.gain.setValueAtTime(0.001, cannonTime);
    thumpGain.gain.exponentialRampToValueAtTime(0.9, cannonTime + 0.02);
    thumpGain.gain.exponentialRampToValueAtTime(0.001, cannonTime + 1.2);
    thumpOsc.connect(thumpGain);
    thumpGain.connect(masterGain);
    thumpOsc.start(cannonTime);
    thumpOsc.stop(cannonTime + 1.3);

    // Explosive noise burst with resonant lowpass filter & reverb decay
    const bufferSize = ctx.sampleRate * 2.5; // 2.5s noise
    const noiseBuffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const output = noiseBuffer.getChannelData(0);
    let lastOut = 0.0;
    for (let i = 0; i < bufferSize; i++) {
      const white = Math.random() * 2 - 1;
      // Pink-ish noise filter
      output[i] = (lastOut + 0.03 * white) / 1.03;
      lastOut = output[i];
      output[i] *= 3.5;
    }

    const noiseSource = ctx.createBufferSource();
    noiseSource.buffer = noiseBuffer;

    const noiseFilter = ctx.createBiquadFilter();
    noiseFilter.type = "lowpass";
    noiseFilter.frequency.setValueAtTime(320, cannonTime);
    noiseFilter.frequency.exponentialRampToValueAtTime(55, cannonTime + 1.8);
    noiseFilter.Q.setValueAtTime(3.5, cannonTime);

    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(0.001, cannonTime);
    noiseGain.gain.exponentialRampToValueAtTime(1.0, cannonTime + 0.015);
    noiseGain.gain.exponentialRampToValueAtTime(0.001, cannonTime + 2.2);

    noiseSource.connect(noiseFilter);
    noiseFilter.connect(noiseGain);
    noiseGain.connect(masterGain);

    noiseSource.start(cannonTime);
    noiseSource.stop(cannonTime + 2.5);
  } catch (err) {
    console.error("Failed to play goal horn:", err);
  }
}

export function playOpponentChime(volumePercent: number = 80): void {
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;
    const vol = Math.max(0, Math.min(1, volumePercent / 100));

    const masterGain = ctx.createGain();
    masterGain.gain.setValueAtTime(vol * 0.45, now);
    masterGain.connect(ctx.destination);

    // Soft two-tone chime (520Hz, 390Hz)
    [
      { freq: 520, start: 0, dur: 0.8 },
      { freq: 390, start: 0.15, dur: 1.0 },
    ].forEach(({ freq, start, dur }) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, now + start);

      gain.gain.setValueAtTime(0.001, now + start);
      gain.gain.exponentialRampToValueAtTime(0.5, now + start + 0.04);
      gain.gain.exponentialRampToValueAtTime(0.001, now + start + dur);

      osc.connect(gain);
      gain.connect(masterGain);
      osc.start(now + start);
      osc.stop(now + start + dur + 0.1);
    });
  } catch (err) {
    console.error("Failed to play chime:", err);
  }
}
