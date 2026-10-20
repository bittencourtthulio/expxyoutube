// Timeline "para e anda" (regra 11) e respiro (regra 7), portados do template CANAL.
import { Easing, interpolate } from "remotion";
import { theme } from "../theme";

export type Stop = { value: number; dwell: number };

export const buildStops = (stops: Stop[], travel: number) => {
  const inputs: number[] = [];
  const outputs: number[] = [];
  let t = 0;
  stops.forEach((stop, i) => {
    inputs.push(t);
    outputs.push(stop.value);
    t += stop.dwell;
    inputs.push(t);
    outputs.push(stop.value);
    if (i < stops.length - 1) t += travel;
  });
  return { inputs, outputs, totalFrames: t };
};

export const stopsDuration = (stops: Stop[], travel: number) => buildStops(stops, travel).totalFrames;

export const stopAndGo = (frame: number, stops: Stop[], travel: number, easing: (t: number) => number = theme.ease.inOut) => {
  const { inputs, outputs } = buildStops(stops, travel);
  return interpolate(frame, inputs, outputs, { easing, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
};

/** Micro-movimento de respiro: elemento parado por mais de 2 s nunca fica imóvel. */
export const breathe = (frame: number, fps: number, amplitude = 4, seconds = 4) =>
  Math.sin((frame / (fps * seconds)) * Math.PI * 2) * amplitude;

export { Easing };
