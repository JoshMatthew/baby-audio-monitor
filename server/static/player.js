// Plays the baby Mac's audio: 16 kHz mono, one mu-law byte per sample.
const SAMPLE_RATE = 16000;
const START_DELAY_SECONDS = 0.3;
const MAX_DELAY_SECONDS = 1.5;
const MULAW_TABLE = buildMulawTable();

function buildMulawTable() {
  const mu = 255;

  return Float32Array.from({ length: 256 }, (_, byte) => {
    const compressed = byte / 127.5 - 1;
    return (
      (Math.sign(compressed) * (Math.pow(1 + mu, Math.abs(compressed)) - 1)) /
      mu
    );
  });
}

function peakOf(samples) {
  return samples.reduce((peak, sample) => Math.max(peak, Math.abs(sample)), 0);
}

export class Player {
  constructor() {
    this.context = new AudioContext({ sampleRate: SAMPLE_RATE });
    this.volume = this.context.createGain();
    this.volume.connect(this.context.destination);
    this.nextStartTime = 0;
  }

  setVolume(value) {
    this.volume.gain.value = value;
  }

  // Returns the chunk's loudest sample, from 0 to 1, for the level meter.
  play(bytes) {
    const samples = Float32Array.from(bytes, (byte) => MULAW_TABLE[byte]);

    if (this.context.state === "running") {
      this.schedule(samples);
    } else {
      this.context.resume();
    }

    return peakOf(samples);
  }

  // Queues chunks back to back; jumps ahead if playback fell behind or drifted too far from live.
  schedule(samples) {
    const buffer = this.context.createBuffer(1, samples.length, SAMPLE_RATE);
    buffer.copyToChannel(samples, 0);

    const now = this.context.currentTime;
    const fellBehind = this.nextStartTime < now;
    const tooFarBehindLive = this.nextStartTime > now + MAX_DELAY_SECONDS;
    if (fellBehind || tooFarBehindLive)
      this.nextStartTime = now + START_DELAY_SECONDS;

    const source = this.context.createBufferSource();
    source.buffer = buffer;
    source.connect(this.volume);
    source.start(this.nextStartTime);
    this.nextStartTime += buffer.duration;
  }

  close() {
    this.context.close();
  }
}
